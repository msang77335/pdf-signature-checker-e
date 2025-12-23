# PDF Signature Verification API

REST API để xác thực chữ ký số trong file PDF.

## Cài đặt

```bash
pip install flask pyhanko pyhanko-certvalidator
```

## Chạy API

```bash
python api.py
```

Server sẽ chạy tại `http://localhost:5000`

## Endpoints

### 1. Health Check
```
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "PDF Signature Verification API"
}
```

### 2. Xác thực chữ ký PDF
```
POST /api/verify-pdf
Content-Type: multipart/form-data
```

**Request:**
- `file`: PDF file (multipart/form-data)

**Response:**
```json
{
  "success": true,
  "count": 2,
  "signatures": [
    {
      "field_name": "Signature_0",
      "signer": "CÔNG TY CỔ PHẦN THANH TOÁN NEO",
      "issuer": "FastCA SHA-256 R1",
      "signing_time": "2025-12-07T16:47:47+07:00",
      "valid_from": "2025-12-04T07:48:00+00:00",
      "valid_until": "2028-12-04T07:48:00+00:00",
      "is_valid": true,
      "is_expired": false,
      "intact": true,
      "document_unchanged": true,
      "valid_at_signing_time": true,
      "coverage": "SignatureCoverageLevel.ENTIRE_REVISION",
      "total_size": 773675
    }
  ]
}
```

## Test API

### Sử dụng cURL:

```bash
# Health check
curl http://localhost:5000/api/health

# Xác thực PDF
curl -X POST http://localhost:5000/api/verify-pdf \
  -F "file=@Test.pdf"
```

### Sử dụng test script:

```bash
chmod +x test_api.sh
./test_api.sh
```

### Sử dụng Python requests:

```python
import requests

# Upload và xác thực PDF
with open('Test.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/verify-pdf',
        files={'file': f}
    )
    print(response.json())
```

## Các trường trong response

- `field_name`: Tên trường chữ ký
- `signer`: Thông tin người ký
- `issuer`: Đơn vị cấp chứng thư
- `signing_time`: Thời gian ký
- `valid_from`: Ngày bắt đầu hiệu lực chứng thư
- `valid_until`: Ngày hết hạn chứng thư
- `is_valid`: Chứng thư còn hiệu lực (hiện tại)
- `is_expired`: Chứng thư đã hết hạn
- `intact`: Tính toàn vẹn của chữ ký
- `document_unchanged`: Tài liệu không bị thay đổi sau khi ký
- `valid_at_signing_time`: Chứng thư hợp lệ tại thời điểm ký
- `coverage`: Mức độ bao phủ của chữ ký
- `total_size`: Kích thước file
