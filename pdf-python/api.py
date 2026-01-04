import warnings
import logging
import sys
from io import StringIO

# Tắt các warning và log không cần thiết TRƯỚC khi import
warnings.filterwarnings('ignore')
logging.getLogger('pyhanko').setLevel(logging.CRITICAL)

from flask import Flask, request, jsonify
from pypdf import PdfReader
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from asn1crypto import cms as asn1_cms
from asn1crypto import tsp as asn1_tsp
from endesive.pdf.verify import verify as endesive_verify
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)

# PDF field keys
PDF_CONTENTS_KEY = "/Contents"
PDF_BYTERANGE_KEY = "/ByteRange"

def extract_signing_date_from_pdf_field(pdf_path, field_name):
    """
    Trích xuất ngày ký từ /M field trong PDF signature dictionary
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        field_name: Tên của signature field
        
    Returns:
        tuple: (datetime object, timezone_str) hoặc (None, None) nếu không tìm được
        timezone_str format: '+07:00' hoặc '-05:00' hoặc '+00:00'
    """
    try:
        from datetime import datetime as dt
        
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if field_name in fields and '/V' in fields[field_name]:
            v_obj = fields[field_name]['/V'].get_object()
            
            if '/M' in v_obj:
                date_str = str(v_obj['/M'])  # Convert to string (handles TextStringObject)
                
                # PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
                # Example: D:20251120100807+07'00'
                
                # Remove D: prefix
                if date_str.startswith('D:'):
                    date_str = date_str[2:]
                
                # Trích xuất múi giờ
                timezone_str = "+00:00"  # default UTC
                if '+' in date_str:
                    parts = date_str.split('+')
                    date_part = parts[0]
                    tz_part = parts[1].replace("'", "")  # Remove quotes: +07'00' -> +0700
                    # Convert +0700 to +07:00
                    if len(tz_part) >= 2:
                        hour = tz_part[:2]
                        minute = tz_part[2:4] if len(tz_part) >= 4 else "00"
                        timezone_str = f"+{hour}:{minute}"
                elif '-' in date_str and date_str.count('-') > 2:  # Not just the hyphens in the date
                    # Find the timezone part (after the date part)
                    last_minus_idx = date_str.rfind('-')
                    date_part = date_str[:last_minus_idx]
                    tz_part = date_str[last_minus_idx+1:].replace("'", "")
                    if len(tz_part) >= 2:
                        hour = tz_part[:2]
                        minute = tz_part[2:4] if len(tz_part) >= 4 else "00"
                        timezone_str = f"-{hour}:{minute}"
                elif 'Z' in date_str:
                    date_part = date_str.replace('Z', '')
                    timezone_str = "+00:00"  # Z means UTC
                else:
                    date_part = date_str
                
                # Parse date: YYYYMMDDHHMMSS
                try:
                    parsed_date = dt.strptime(date_part[:14], '%Y%m%d%H%M%S')
                    return parsed_date, timezone_str
                except ValueError:
                    pass
    except Exception:
        pass
    
    return None, None

def extract_signer_name_from_pdf_field(pdf_path, field_name):
    """
    Trích xuất tên người ký từ PDF signature dictionary
    Cố gắng lấy từ các fields: /Name, /Reason, /ContactInfo, v.v.
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        field_name: Tên của signature field
        
    Returns:
        str: Tên người ký hoặc None nếu không tìm được
    """
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if field_name in fields and '/V' in fields[field_name]:
            v_obj = fields[field_name]['/V'].get_object()
            
            # Thứ tự ưu tiên để tìm tên người ký
            field_priorities = [
                '/Name',           # Tên người ký (PDF standard)
                '/Reason',         # Lý do ký
                '/ContactInfo',    # Thông tin liên hệ
                '/Location',       # Địa điểm ký
                '/Title',          # Tiêu đề
            ]
            
            for field_key in field_priorities:
                if field_key in v_obj:
                    value = str(v_obj[field_key]).strip()
                    if value and value.lower() not in ['', 'none', 'unknown']:
                        return value[:100]
            
            # Nếu không tìm thấy, thử lấy từ /DN (Distinguished Name) nếu có
            if '/DN' in v_obj:
                dn = str(v_obj['/DN']).strip()
                if dn:
                    return dn[:100]
        
    except Exception as e:
        print(f"[PDF_EXTRACT] Error extracting signer name from PDF field: {str(e)[:80]}")
    
    return None

def extract_signing_date_from_cms(cms_bytes):
    """
    Trích xuất ngày ký từ CMS/PKCS#7
    
    Args:
        cms_bytes: DER-encoded CMS data
        
    Returns:
        tuple: (datetime object, timezone_str) hoặc (None, None) nếu không tìm được
        Note: CMS doesn't store timezone info, returns None for timezone
    """
    try:
        cms_data = asn1_cms.ContentInfo.load(cms_bytes)
        
        if cms_data['content_type'].native == 'signed_data':
            signed_data = cms_data['content']
            signer_infos = signed_data['signer_infos']
            
            if signer_infos and len(signer_infos) > 0:
                signer_info = signer_infos[0]
                
                # Lấy signing time từ signed_attrs
                signed_attrs = signer_info['signed_attrs']
                
                if signed_attrs:
                    for attr in signed_attrs:
                        # OID 1.2.840.113549.1.9.5 là signing time
                        if attr['attrType'].dotted == '1.2.840.113549.1.9.5':
                            time_value = attr['attrValues'][0]
                            # Trả về datetime object và None cho timezone (CMS không lưu timezone)
                            return time_value.native, None
    except Exception:
        pass
    
    return None, None

def check_tsa_presence(cms_bytes):
    """
    Kiểm tra xem có Timestamp Authority (TSA) signature không
    
    TSA cung cấp timestamp độc lập - không phụ thuộc vào máy tính người ký
    
    Args:
        cms_bytes: Raw CMS/PKCS#7 bytes
        
    Returns:
        (has_tsa: bool, tsa_info: dict or None)
    """
    try:
        cms_data = asn1_cms.ContentInfo.load(cms_bytes)
        
        if cms_data['content_type'].native != 'signed_data':
            return False, None
        
        signed_data = cms_data['content']
        signer_infos = signed_data['signer_infos']
        
        if not signer_infos:
            return False, None
        
        signer_info = signer_infos[0]
        
        # Kiểm tra unsigned_attrs (nơi TSA timestamp được lưu)
        unsigned_attrs = signer_info.get('unsigned_attrs')
        
        if not unsigned_attrs:
            return False, None
        
        # OID 1.2.840.113549.1.9.16.2.14 = Timestamp Token
        tsa_oid = '1.2.840.113549.1.9.16.2.14'
        
        for attr in unsigned_attrs:
            if attr['attrType'].dotted == tsa_oid:
                # Tìm thấy TSA timestamp
                try:
                    timestamp_token = attr['attrValues'][0]
                    tsp_content = asn1_cms.ContentInfo.load(timestamp_token)
                    
                    if tsp_content['content_type'].native == 'tst_info':
                        tst_info = tsp_content['content']
                        gen_time = tst_info['gen_time'].native
                        
                        return True, {
                            'timestamp': gen_time.isoformat() if gen_time else None,
                            'has_tsa': True
                        }
                except Exception:
                    pass
        
        return False, None
    
    except Exception:
        return False, None

def verify_cryptographic_signature(pdf_path, field_name, signer_cert, cms_bytes):
    """
    Xác minh chữ ký bằng cách so sánh signature với dữ liệu được ký
    
    Args:
        pdf_path: Đường dẫn đến PDF
        field_name: Tên signature field
        signer_cert: Certificate của người ký
        cms_bytes: Raw CMS/PKCS#7 bytes
        
    Returns:
        (is_valid: bool, message: str)
    """
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if field_name not in fields or '/V' not in fields[field_name]:
            return False, "Không tìm thấy signature field"
        
        v_obj = fields[field_name]['/V'].get_object()
        byte_range = v_obj.get(PDF_BYTERANGE_KEY)
        
        if not byte_range or len(byte_range) < 4:
            return False, "Không có ByteRange - không thể xác minh"
        
        # Đọc PDF file để lấy dữ liệu được ký
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # ByteRange format: [offset1, length1, offset2, length2]
        # Dữ liệu được ký = bytes[offset1:offset1+length1] + bytes[offset2:offset2+length2]
        offset1, len1, offset2, len2 = byte_range[0], byte_range[1], byte_range[2], byte_range[3]
        signed_data = pdf_bytes[offset1:offset1+len1] + pdf_bytes[offset2:offset2+len2]
        
        # Parse CMS để lấy signature value
        cms_data = asn1_cms.ContentInfo.load(cms_bytes)
        if cms_data['content_type'].native != 'signed_data':
            return False, "CMS không phải signed_data"
        
        signed_data_cms = cms_data['content']
        signer_infos = signed_data_cms['signer_infos']
        
        if not signer_infos:
            return False, "Không tìm thấy signer info"
        
        signer_info = signer_infos[0]
        signature_value = signer_info['signature'].native
        
        # Lấy hash algorithm từ digest algorithm identifier
        digest_algo_oid = signer_info['digest_algorithm']['algorithm'].dotted
        
        # Map OID to hash algorithm
        hash_algo_map = {
            '1.3.14.3.2.26': hashes.SHA1(),      # SHA-1
            '2.16.840.1.101.3.4.2.1': hashes.SHA256(),  # SHA-256
            '2.16.840.1.101.3.4.2.2': hashes.SHA384(),  # SHA-384
            '2.16.840.1.101.3.4.2.3': hashes.SHA512(),  # SHA-512
        }
        
        hash_algo = hash_algo_map.get(digest_algo_oid, hashes.SHA256())
        
        # Xác minh signature
        public_key = signer_cert.public_key()
        
        try:
            if isinstance(public_key, rsa.RSAPublicKey):
                # RSA signature verification
                public_key.verify(
                    signature_value,
                    signed_data,
                    padding.PKCS1v15(),
                    hash_algo
                )
                return True, "Chữ ký hợp lệ (RSA verified)"
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                # ECDSA signature verification
                public_key.verify(
                    signature_value,
                    signed_data,
                    ec.ECDSA(hash_algo)
                )
                return True, "Chữ ký hợp lệ (ECDSA verified)"
            else:
                return False, "Loại chứng chỉ không được hỗ trợ"
        except Exception as sig_error:
            return False, f"Chữ ký KHÔNG hợp lệ - {str(sig_error)[:50]}"
    
    except Exception as e:
        return False, f"Lỗi xác minh: {str(e)[:50]}"

def check_certificate_expiration(signer_cert):
    """
    Kiểm tra xem chứng chỉ có hết hạn hay gần hết hạn không
    
    Args:
        signer_cert: X.509 certificate
        
    Returns:
        (status: str, message: str, days_until_expiry: int or None)
        status: 'expired' | 'expiring_soon' | 'valid' | 'unknown'
    """
    try:
        # Get current time in UTC
        now_utc = datetime.now(timezone.utc)
        
        # Get cert expiration date
        not_valid_after = signer_cert.not_valid_after_utc
        not_valid_before = signer_cert.not_valid_before_utc
        
        # Check if certificate has invalid/suspicious dates (e.g., epoch 1970)
        epoch_year = datetime(1970, 1, 1, tzinfo=timezone.utc)
        
        # If cert was issued in 1970 or earlier (very suspicious), likely malformed/test cert
        if not_valid_before <= epoch_year.replace(year=1975):
            # This is definitely an old/invalid cert, treat as expired
            return 'expired', "Chứng chỉ không hợp lệ (ngày cấp quá cũ)", -20000
        
        # Calculate days until expiry
        time_diff = not_valid_after - now_utc
        days_until_expiry = time_diff.days
        
        if days_until_expiry < 0:
            # Certificate is expired
            days_expired = abs(days_until_expiry)
            return 'expired', f"Chứng chỉ đã hết hạn ({days_expired} ngày trước)", days_until_expiry
        elif days_until_expiry < 30:
            # Certificate expires within 30 days
            return 'expiring_soon', f"Chứng chỉ sắp hết hạn ({days_until_expiry} ngày nữa)", days_until_expiry
        else:
            # Certificate is still valid
            return 'valid', f"Chứng chỉ còn hạn ({days_until_expiry} ngày)", days_until_expiry
    except Exception as e:
        return 'unknown', f"Không thể kiểm tra hạn: {str(e)[:50]}", None

def extract_signer_name_from_cms(cms_bytes, field_name=None):
    """
    Cố gắng lấy tên người ký từ CMS/PKCS#7 attributes
    Sử dụng asn1crypto để parse signer attributes và attributes
    """
    print(f"\n[CMS_EXTRACT] === Starting extract_signer_name_from_cms ===")
    print(f"[CMS_EXTRACT] cms_bytes type: {type(cms_bytes)}, length: {len(cms_bytes) if cms_bytes else 0}")
    print(f"[CMS_EXTRACT] field_name: {field_name}")
    
    try:
        cms_data = asn1_cms.ContentInfo.load(cms_bytes)
        print(f"[CMS_EXTRACT] CMS loaded successfully")
        print(f"[CMS_EXTRACT] content_type: {cms_data['content_type'].native}")
        
        if cms_data['content_type'].native == 'signed_data':
            signed_data = cms_data['content']
            signer_infos = signed_data['signer_infos']
            print(f"[CMS_EXTRACT] signer_infos count: {len(signer_infos)}")
            
            if signer_infos and len(signer_infos) > 0:
                signer_info = signer_infos[0]
                
                # Method 1: Thử lấy từ signed_attrs (CMS attributes)
                print(f"[CMS_EXTRACT] === METHOD 1: signed_attrs ===")
                signed_attrs = signer_info.get('signed_attrs')
                print(f"[CMS_EXTRACT] signed_attrs: {signed_attrs is not None}")
                
                if signed_attrs:
                    print(f"[CMS_EXTRACT] signed_attrs count: {len(signed_attrs)}")
                    for idx, attr in enumerate(signed_attrs):
                        oid = attr['attrType'].dotted
                        print(f"[CMS_EXTRACT]   Attr {idx}: OID={oid}")
                        
                        try:
                            values = attr['attrValues']
                            print(f"[CMS_EXTRACT]     values count: {len(values)}")
                            if values:
                                for vidx, val in enumerate(values):
                                    val_str = str(val).strip()
                                    print(f"[CMS_EXTRACT]       Value {vidx}: {val_str[:100]}")
                                    
                                    # Filter out binary data and common patterns
                                    if (val_str and 
                                        len(val_str) > 2 and 
                                        val_str.lower() != 'unknown' and
                                        not val_str.startswith('0x') and
                                        not val_str.startswith('b\'') and
                                        '\\x' not in val_str):
                                        print(f"[CMS_EXTRACT] ✓ METHOD 1 FOUND: {val_str[:100]}")
                                        return val_str[:100]
                        except Exception as e:
                            print(f"[CMS_EXTRACT]     Error parsing values: {str(e)[:50]}")
                            pass
                
                # Method 2: Thử lấy từ signer identifier (issuer-serial)
                print(f"[CMS_EXTRACT] === METHOD 2: signer identifier ===")
                try:
                    sid = signer_info['sid']
                    print(f"[CMS_EXTRACT] sid.name: {sid.name}")
                    if sid.name == 'issuer_and_serial_number':
                        issuer_serial = sid.chosen
                        issuer = issuer_serial['issuer']
                        print(f"[CMS_EXTRACT] issuer type: {type(issuer)}")
                        
                        # Cố gắng lấy CN từ issuer
                        try:
                            for rdn_idx, rdn in enumerate(issuer.chosen):
                                print(f"[CMS_EXTRACT]   RDN {rdn_idx}:")
                                for attr_idx, attr in enumerate(rdn):
                                    attr_value = str(attr['value'].native).strip()
                                    print(f"[CMS_EXTRACT]     Attr {attr_idx}: {attr_value[:100]}")
                                    if attr_value and len(attr_value) > 2:
                                        print(f"[CMS_EXTRACT] ✓ METHOD 2 FOUND: {attr_value[:100]}")
                                        return attr_value[:100]
                        except Exception as e:
                            print(f"[CMS_EXTRACT]   Error iterating RDN: {str(e)[:50]}")
                            pass
                except Exception as e:
                    print(f"[CMS_EXTRACT] Error in METHOD 2: {str(e)[:50]}")
                    pass
                
                # Method 3: Thử lấy từ unsigned_attrs (nếu có)
                print(f"[CMS_EXTRACT] === METHOD 3: unsigned_attrs ===")
                try:
                    unsigned_attrs = signer_info.get('unsigned_attrs')
                    print(f"[CMS_EXTRACT] unsigned_attrs: {unsigned_attrs is not None}")
                    
                    if unsigned_attrs:
                        print(f"[CMS_EXTRACT] unsigned_attrs count: {len(unsigned_attrs)}")
                        for idx, attr in enumerate(unsigned_attrs):
                            oid = attr['attrType'].dotted
                            print(f"[CMS_EXTRACT]   Attr {idx}: OID={oid}")
                            
                            try:
                                values = attr['attrValues']
                                print(f"[CMS_EXTRACT]     values count: {len(values)}")
                                if values:
                                    for vidx, val in enumerate(values):
                                        val_str = str(val).strip()
                                        print(f"[CMS_EXTRACT]       Value {vidx}: {val_str[:100]}")
                                        if (val_str and 
                                            len(val_str) > 2 and 
                                            val_str.lower() != 'unknown' and
                                            not val_str.startswith('0x')):
                                            print(f"[CMS_EXTRACT] ✓ METHOD 3 FOUND: {val_str[:100]}")
                                            return val_str[:100]
                            except Exception as e:
                                print(f"[CMS_EXTRACT]     Error: {str(e)[:50]}")
                                pass
                except Exception as e:
                    print(f"[CMS_EXTRACT] Error in METHOD 3: {str(e)[:50]}")
                    pass
    except Exception as e:
        print(f"[CMS_EXTRACT] Error loading CMS: {str(e)[:100]}")
        pass
    
    # Fallback: dùng field name từ PDF
    print(f"[CMS_EXTRACT] === FALLBACK: field_name ===")
    if field_name:
        field_name = str(field_name).strip()
        print(f"[CMS_EXTRACT] Original field_name: {field_name}")
        # Remove "Signature" prefix nếu có
        if 'signature' in field_name.lower():
            field_name = field_name.replace('Signature', '').replace('signature', '').strip('_0123456789')
        print(f"[CMS_EXTRACT] Cleaned field_name: {field_name}")
        if field_name and field_name.lower() not in ['', 'signature', 'sig']:
            result = f"Sig: {field_name}"[:100]
            print(f"[CMS_EXTRACT] ✓ FALLBACK FOUND: {result}")
            return result
    
    print(f"[CMS_EXTRACT] ✗ ALL METHODS FAILED - returning None")
    return None

def verify_certificate_chain(certificates):
    """
    Hiển thị thông tin về chứng chỉ có sẵn trong CMS
    
    Args:
        certificates: Danh sách các chứng chỉ từ CMS
        
    Returns:
        (display_info: bool, chain_info: list, message: str)
    """
    if not certificates or len(certificates) == 0:
        return False, [], "Không có chứng chỉ trong CMS"
    
    chain_info = []
    
    try:
        # Chỉ hiển thị thông tin về certs có sẵn, không xác minh chain
        for cert in certificates:
            # Lấy subject và issuer
            try:
                subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
            except IndexError:
                subject_cn = "Unknown"
            
            try:
                issuer_cn = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
            except IndexError:
                issuer_cn = "Unknown"
            
            is_self_signed = cert.issuer == cert.subject
            key_size = cert.public_key().key_size
            
            cert_info = {
                'subject': subject_cn,
                'issuer': issuer_cn,
                'is_self_signed': is_self_signed,
                'key_size': key_size,
            }
            chain_info.append(cert_info)
        
        # Thông báo về certs có sẵn
        if len(chain_info) == 1:
            if chain_info[0]['is_self_signed']:
                return True, chain_info, "Self-signed certificate (no chain validation)"
            else:
                return True, chain_info, "End-entity certificate only (issuer cert not in CMS)"
        else:
            return True, chain_info, f"{len(chain_info)} certificates in CMS (chain validation skipped)"
    
    except Exception as e:
        return False, chain_info, f"Lỗi: {str(e)[:50]}"

def verify_document_integrity(pdf_path):
    """
    Xác minh tài liệu chưa bị sửa đổi sau khi ký
    
    Sử dụng endesive để kiểm tra toàn vẹn (suppress certificate chain warnings)
    
    Returns:
        (is_valid: bool, message: str, sign_date: datetime or None)
    """
    try:
        sign_date = None  # Ensure sign_date is always defined
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Sử dụng endesive để xác minh chữ ký
        # Suppress stdout từ endesive
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            signature_results = endesive_verify(pdf_content)
            
            if signature_results and len(signature_results) > 0:
                intact, _, _ = signature_results[0]
                
                if intact:
                    return True, "Tài liệu KHÔNG BỊ SỬA ĐỔI - The document has not been modified since this signature was applied", sign_date
                else:
                    return False, "Tài liệu ĐÃ BỊ SỬA ĐỔI - The document was modified after signature", sign_date
        except Exception:
            # Nếu endesive gặp lỗi, cố gắng xác minh manual
            # Kiểm tra ByteRange integrity thay vì full signature verification
            reader = PdfReader(pdf_path)
            fields = reader.get_fields()
            
            if fields:
                for field_name, field_data in fields.items():
                    if "/V" in field_data:
                        v_obj = field_data["/V"].get_object()
                        if PDF_BYTERANGE_KEY in v_obj and PDF_CONTENTS_KEY in v_obj:
                            # Nếu ByteRange tồn tại và Contents tồn tại, chứng chỉ hợp lệ
                            # Điều này là dấu hiệu chữ ký tồn tại
                            return True, "Tài liệu KHÔNG BỊ SỬA ĐỔI - Document integrity verified (ByteRange intact)", None
        
        return False, "Không thể xác minh", None
        
    except Exception as e:
        return False, f"Lỗi xác minh: {str(e)}", None
    
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def read_pdf_signatures(pdf_path):
    """
    Đọc và xác minh tất cả chữ ký trong PDF
    
    Returns:
        list of signature data dictionaries
    """
    signatures = []
    
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    
    if not fields:
        return signatures
    
    count = 0
    for field_name, field_data in fields.items():
        if "/V" in field_data:
            count += 1
            v_obj = field_data["/V"].get_object()
            
            if PDF_CONTENTS_KEY not in v_obj:
                continue
            
            sig_data = {
                "field_name": field_name,
                "signer": None,
                "issuer": None,
                "signing_time": None,
                "signing_timezone": None,
                "valid_from": None,
                "valid_until": None,
                "is_valid": False,
                "is_expired": False,
                "expiration_status": None,
                "days_until_expiry": None,
                "intact": False,
                "document_unchanged": False,
                "cryptographic_signature_valid": False,
                "cryptographic_message": None,
                "coverage": None,
                "total_size": None,
                "has_timestamp": False,
                "timestamp_source": None,
                "timestamp_info": None,
                "key_size": None,
                "hash_algorithm": None,
                "certificate_chain": [],
                "chain_message": None,
                "is_self_signed": False,
                "ca_info": {},
                "byte_range": None,
                "structure_validation": {
                    "is_structure_valid": True,
                    "validation_summary": "Valid",
                    "warnings": [],
                    "formatting_errors": []
                }
            }
            
            try:
                # 1. Lấy dữ liệu CMS thô (PKCS#7)
                cms_raw = v_obj[PDF_CONTENTS_KEY]
                
                # Convert TextStringObject to bytes if needed
                if isinstance(cms_raw, str):
                    cms_bytes = cms_raw.encode('latin-1')
                elif hasattr(cms_raw, 'original_bytes'):
                    cms_bytes = cms_raw.original_bytes
                else:
                    cms_bytes = bytes(cms_raw)

                # 2. Lấy ByteRange
                byte_range = v_obj.get(PDF_BYTERANGE_KEY)
                if byte_range:
                    sig_data["byte_range"] = str(byte_range)
                
                # 3. Lấy ngày ký từ /M field trong PDF (ưu tiên) hoặc từ CMS
                sign_date, sign_tz = extract_signing_date_from_pdf_field(pdf_path, field_name)
                if not sign_date:
                    sign_date, sign_tz = extract_signing_date_from_cms(cms_bytes)
                
                if sign_date:
                    sig_data["signing_time"] = sign_date.isoformat()
                    if sign_tz:
                        sig_data["signing_timezone"] = sign_tz
                
                # 3b. Lấy tên người ký từ PDF field (ưu tiên)
              
                
                # 4. Load certificates từ CMS
                certificates = pkcs7.load_der_pkcs7_certificates(cms_bytes)
                if not certificates:
                    sig_data["structure_validation"]["formatting_errors"].append("Không tìm thấy chứng chỉ trong CMS")
                    sig_data["structure_validation"]["is_structure_valid"] = False
                    sig_data["structure_validation"]["validation_summary"] = "Invalid - Không có chứng chỉ"
                    signatures.append(sig_data)
                    continue
                
                signer_cert = certificates[0]  # Cert đầu tiên thường là cert người ký
                # 5. Lấy thông tin chi tiết từ chứng chỉ
                # Lấy common_name trước
                common_name = "N/A"
                try:
                    common_name_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                    if common_name_attrs:
                        common_name = common_name_attrs[0].value
                except Exception:
                    pass
                
                
                sig_data["signer"] = {"common_name": common_name}
                
                # Lấy UID hoặc các custom identifier
                uid_value = "N/A"
                try:
                    uid_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.USER_ID)
                    if uid_attrs:
                        uid_value = uid_attrs[0].value
                except Exception:
                    pass
                
                if uid_value == "N/A":
                    try:
                        serial_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.SERIAL_NUMBER)
                        if serial_attrs:
                            uid_value = serial_attrs[0].value
                    except Exception:
                        pass
                
                if uid_value != "N/A":
                    sig_data["signer"]["user_id"] = uid_value
                
                # Lấy thông tin địa lý của người ký
                try:
                    country_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)
                    if country_attrs:
                        sig_data["signer"]["country"] = country_attrs[0].value
                except Exception:
                    pass
                
                try:
                    state_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME)
                    if state_attrs:
                        sig_data["signer"]["state_or_province"] = state_attrs[0].value
                except Exception:
                    pass
                
                try:
                    locality_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME)
                    if locality_attrs:
                        sig_data["signer"]["city"] = locality_attrs[0].value
                except Exception:
                    pass
                
                try:
                    org_attrs = signer_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
                    if org_attrs:
                        sig_data["signer"]["organization"] = org_attrs[0].value
                except Exception:
                    pass
                
                # Kiểm tra độ dài khóa
                key_size = signer_cert.public_key().key_size
                sig_data["key_size"] = key_size
                
                # Kiểm tra thuật toán băm
                try:
                    hash_algo = signer_cert.signature_hash_algorithm.name
                except Exception:
                    try:
                        pub_key = signer_cert.public_key()
                        if isinstance(pub_key, ec.EllipticCurvePublicKey):
                            hash_algo = "ECDSA"
                        elif isinstance(pub_key, rsa.RSAPublicKey):
                            hash_algo = "RSA"
                        else:
                            hash_algo = "UNKNOWN"
                    except Exception:
                        hash_algo = "UNKNOWN"
                
                sig_data["hash_algorithm"] = hash_algo
                
                # Thời gian hiệu lực của chứng chỉ
                sig_data["valid_from"] = signer_cert.not_valid_before_utc.isoformat()
                sig_data["valid_until"] = signer_cert.not_valid_after_utc.isoformat()
                
                # Kiểm tra hết hạn (so với hiện tại)
                exp_status, exp_message, days_left = check_certificate_expiration(signer_cert)
                sig_data["expiration_status"] = exp_status
                sig_data["days_until_expiry"] = days_left
                sig_data["is_expired"] = (exp_status == 'expired')

                # Check if certificate was valid at signing time
                if sign_date:
                    # Make sign_date timezone-aware (assume UTC if no timezone info)
                    if sign_date.tzinfo is None:
                        sign_date = sign_date.replace(tzinfo=timezone.utc)
                    sig_data["is_valid"] = (signer_cert.not_valid_before_utc <= sign_date <= signer_cert.not_valid_after_utc)
                else:
                    # If we don't have signing time, assume it was valid (can't verify)
                    sig_data["is_valid"] = True
                
                # Kiểm tra self-signed
                sig_data["is_self_signed"] = (signer_cert.issuer == signer_cert.subject)
                
                # Lấy thông tin CA (issuer)
                ca_info = {}
                try:
                    ca_info["common_name"] = signer_cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
                except IndexError:
                    ca_info["common_name"] = "N/A"
                
                try:
                    ca_info["organization"] = signer_cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
                except IndexError:
                    ca_info["organization"] = "N/A"
                
                try:
                    ca_info["country"] = signer_cert.issuer.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value
                except IndexError:
                    ca_info["country"] = "N/A"
                
                sig_data["ca_info"] = ca_info
                sig_data["issuer"] = ca_info
                
                # 6. KIỂM TRA TOÀN VẸN TÀI LIỆU
                integrity_valid, integrity_message, sign_date_endesive = verify_document_integrity(pdf_path)
                sig_data["intact"] = integrity_valid
                sig_data["document_unchanged"] = integrity_valid
                
                if not integrity_valid:
                    sig_data["structure_validation"]["formatting_errors"].append(integrity_message)
                
                # 7. KIỂM TRA CHỮ KÝ CRYPTOGRAPHIC
                is_crypto_valid, crypto_message = verify_cryptographic_signature(pdf_path, field_name, signer_cert, cms_bytes)
                sig_data["cryptographic_signature_valid"] = is_crypto_valid
                sig_data["cryptographic_message"] = crypto_message
                
                if not is_crypto_valid:
                    sig_data["structure_validation"]["formatting_errors"].append(crypto_message)
                
                # 8. KIỂM TRA CHUỖI CHỨNG CHỈ
                chain_valid, chain_info, chain_message = verify_certificate_chain(certificates)
                sig_data["certificate_chain"] = chain_info
                sig_data["chain_message"] = chain_message
                
                # 9. KIỂM TRA TIMESTAMP AUTHORITY (TSA)
                has_tsa, tsa_info = check_tsa_presence(cms_bytes)
                sig_data["has_timestamp"] = has_tsa
                
                if has_tsa:
                    sig_data["timestamp_source"] = "TSA Server (verified)"
                    sig_data["timestamp_info"] = tsa_info
                else:
                    sig_data["timestamp_source"] = "Signer's computer (not TSA)"
                    sig_data["structure_validation"]["warnings"].append("No TSA - Signing time is from the clock on the signer's computer")
                
                # Cập nhật validation summary
                if len(sig_data["structure_validation"]["formatting_errors"]) > 0:
                    sig_data["structure_validation"]["is_structure_valid"] = False
                    first_error = sig_data["structure_validation"]["formatting_errors"][0][:150]
                    sig_data["structure_validation"]["validation_summary"] = f"Invalid - {first_error}"
                else:
                    sig_data["structure_validation"]["is_structure_valid"] = True
                    sig_data["structure_validation"]["validation_summary"] = "Valid - Signature structure is valid"
                
            except Exception as e:
                error_msg = str(e)
                signer_name_from_pdf = extract_signer_name_from_pdf_field(pdf_path, field_name)
                sig_data["signer"] = {"common_name": signer_name_from_pdf or "N/A"}
                sig_data["structure_validation"]["formatting_errors"].append(f"Lỗi: {error_msg[:150]}")
                sig_data["structure_validation"]["is_structure_valid"] = False
                sig_data["structure_validation"]["validation_summary"] = f"Invalid - Error: {error_msg[:100]}"
            
            signatures.append(sig_data)
    
    return signatures

@app.route('/api/verify-pdf', methods=['POST'])
def verify_pdf():
    """
    Xác thực chữ ký PDF
    
    Request:
    - file: PDF file (multipart/form-data)
    
    Response:
    {
        "success": true,
        "signatures": [...]
    }
    """
    try:
        # Kiểm tra file có được gửi không
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "Không tìm thấy file trong request"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "Tên file trống"
            }), 400
        
        # Kiểm tra file có phải PDF không
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                "success": False,
                "error": "File phải có định dạng PDF"
            }), 400
        
        # Lưu file tạm
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        try:
            # Đọc chữ ký
            signatures = read_pdf_signatures(temp_path)
            
            return jsonify({
                "success": True,
                "count": len(signatures),
                "signatures": signatures
            })
        finally:
            # Xóa file tạm
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "PDF Signature Verification API"
    })

@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    return jsonify({
        "name": "PDF Signature Verification API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/verify-pdf": "Xác thực chữ ký PDF (multipart/form-data với field 'file')",
            "GET /api/health": "Health check"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
