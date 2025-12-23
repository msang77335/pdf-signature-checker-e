import warnings
import logging

# Tắt các warning và log không cần thiết TRƯỚC khi import
warnings.filterwarnings('ignore')
logging.getLogger('pyhanko').setLevel(logging.CRITICAL)

from flask import Flask, request, jsonify
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
import json
from datetime import datetime, timezone
import os

app = Flask(__name__)

def parse_certificate_name(cert_name):
    """
    Parse certificate name thành object
    
    Input: "User ID: MST:0314363533, Common Name: CÔNG TY..., State/Province: ..., Country: VN"
    Output: {
        "user_id": "MST:0314363533",
        "common_name": "CÔNG TY...",
        "state_province": "...",
        "country": "VN",
        ...
    }
    """
    result = {}
    parts = cert_name.split(", ")
    
    for part in parts:
        if ": " in part:
            key, value = part.split(": ", 1)
            # Chuẩn hóa key thành snake_case
            key_normalized = key.lower().replace(" ", "_").replace("/", "_")
            result[key_normalized] = value
    
    return result

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
                "document_unchanged": False,
                "valid_at_signing_time": False,
                "coverage": None,
                "total_size": None
            }
            
            try:
                # Lấy thông tin cơ bản từ chữ ký
                status = validate_pdf_signature(sig, vc, diff_policy=None)
                
                cert = status.signing_cert
                # Parse signer và issuer thành object
                sig_data["signer"] = parse_certificate_name(cert.subject.human_friendly)
                sig_data["issuer"] = parse_certificate_name(cert.issuer.human_friendly)
                
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
                sig_data["document_unchanged"] = status.intact
                sig_data["coverage"] = str(sig.coverage)
                sig_data["total_size"] = sig.total_len
                
            except Exception as e:
                sig_data["error"] = str(e)[:200]
                try:
                    sig_data["coverage"] = str(sig.coverage)
                    sig_data["total_size"] = sig.total_len
                except:
                    pass
            
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
