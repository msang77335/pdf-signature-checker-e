import warnings
import logging

# Tắt các warning và log không cần thiết TRƯỚC khi import
warnings.filterwarnings('ignore')
logging.getLogger('pyhanko').setLevel(logging.CRITICAL)

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.validation import RevocationInfoValidationType
from pyhanko.sign.validation import validate_pdf_ltv_signature

import json
from datetime import datetime, timezone

def read_pdf_signatures(pdf_path):
    signatures = []
    
    with open(pdf_path, 'rb') as f:
        # 1. Khởi tạo context để validate (bỏ qua Root CA)
        vc = ValidationContext(
            allow_fetching=False,
            weak_hash_algos={'md5', 'md2'},
            revocation_mode='soft-fail',
            trust_roots=[]  # Bỏ qua kiểm tra Root CA
        )
        
        # 2. Đọc file PDF
        from pyhanko.pdf_utils.reader import PdfFileReader
        reader = PdfFileReader(f)
        
        # 3. Duyệt qua tất cả các chữ ký trong file
        for sig in reader.embedded_signatures:
            sig_data = {
                "field_name": sig.field_name,
                "signer": None,
                "issuer": None,
                "signing_time": None,
                "valid_from": None,
                "valid_until": None,
                "is_valid": False,
                "is_expired": False,
                "intact": False,
                "document_unchanged": False,  # Tài liệu không bị thay đổi
                "valid_at_signing_time": False,  # Hợp lệ tại thời điểm ký
                "coverage": None,
                "total_size": None
            }
            
            try:
                # Lấy thông tin cơ bản từ chữ ký
                status = validate_pdf_signature(sig, vc, diff_policy=None)
                
                cert = status.signing_cert
                sig_data["signer"] = cert.subject.human_friendly
                sig_data["issuer"] = cert.issuer.human_friendly
                
                # Lấy thời gian ký
                signing_dt = None
                if hasattr(status, 'signer_reported_dt') and status.signer_reported_dt:
                    signing_dt = status.signer_reported_dt
                    sig_data["signing_time"] = signing_dt.isoformat()
                elif hasattr(status, 'timestamp_validity') and status.timestamp_validity:
                    signing_dt = status.timestamp_validity.timestamp
                    sig_data["signing_time"] = signing_dt.isoformat()
                
                # Hiển thị thời hạn của chứng thư
                if hasattr(cert, 'not_valid_before'):
                    sig_data["valid_from"] = cert.not_valid_before.isoformat()
                if hasattr(cert, 'not_valid_after'):
                    sig_data["valid_until"] = cert.not_valid_after.isoformat()
                    now = datetime.now(timezone.utc)
                    sig_data["is_expired"] = cert.not_valid_after <= now
                    sig_data["is_valid"] = cert.not_valid_after > now
                    
                    # Kiểm tra chữ ký có hợp lệ tại thời điểm ký không
                    if signing_dt and hasattr(cert, 'not_valid_before'):
                        sig_data["valid_at_signing_time"] = (
                            cert.not_valid_before <= signing_dt <= cert.not_valid_after
                        )
                
                # Kiểm tra tính toàn vẹn
                sig_data["intact"] = status.intact
                sig_data["document_unchanged"] = status.intact  # Tài liệu không bị thay đổi
                sig_data["coverage"] = str(sig.coverage)
                sig_data["total_size"] = sig.total_len
                
            except Exception as e:
                sig_data["error"] = "Không thể xác thực đầy đủ (thiếu Root CA)"
                try:
                    sig_data["coverage"] = str(sig.coverage)
                    sig_data["total_size"] = sig.total_len
                except:
                    pass
            
            signatures.append(sig_data)
    
    return signatures

# Sử dụng tool
pdf_file = "./Test.pdf"  # Thay bằng đường dẫn file của bạn
result = read_pdf_signatures(pdf_file)
print(json.dumps(result, indent=2, ensure_ascii=False))