# ByteRange Validation - Foxit SDK Style

## Tổng quan

Module này thực hiện kiểm tra ByteRange cực kỳ nghiêm ngặt, tương tự như Foxit Web SDK. Nó có khả năng phát hiện khi một revision sau (Rev.2) làm hỏng revision trước (Rev.1) bằng cách ghi đè lên vùng dữ liệu đã được ký.

## ByteRange Format

ByteRange trong PDF signature có format: `[start1, length1, start2, length2]`

- **start1**: Offset bắt đầu vùng đầu tiên (thường là 0)
- **length1**: Độ dài vùng đầu tiên
- **start2**: Offset bắt đầu vùng thứ hai
- **length2**: Độ dài vùng thứ hai

**Vùng signature content** (không được sign) nằm giữa: `[start1+length1, start2)`

Ví dụ:
```
ByteRange: [0, 1000, 1500, 2000]
- Vùng signed #1: bytes 0-999
- Signature content: bytes 1000-1499 (không sign)
- Vùng signed #2: bytes 1500-3499
```

## Các kiểm tra được thực hiện

### 1. Basic ByteRange Validation

✅ **ByteRange phải bắt đầu từ offset 0**
```
[Foxit SDK] ByteRange Error: ByteRange phải bắt đầu từ offset 0
```

✅ **ByteRange phải có đúng 4 số**
```
[Foxit SDK] ByteRange Format Error: ByteRange phải có đúng 4 số [start1, length1, start2, length2]
```

### 2. ByteRange Integrity Check (CRITICAL)

Kiểm tra xem revision mới có ghi đè lên vùng signature của revision cũ không.

**Case phát hiện lỗi:**
- Rev.1 có ByteRange: `[0, 1000, 1500, 2000]`
  - Signature content tại: bytes 1000-1499
- Rev.2 có ByteRange: `[0, 1200, 1800, 2500]`
  - Vùng signed bao gồm: bytes 0-1199 và 1800-4299
  - ❌ Vùng 0-1199 **ghi đè** lên signature content của Rev.1 (1000-1499)

**Error message:**
```
[Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè lên vùng signature của Revision 1 
(offset 1000-1500). Điều này làm hỏng cấu trúc chữ ký trước đó. 
Warning: Document has been modified after signing (Rev.1 corrupted by Rev.2)
```

### 3. ByteRange Overlap Detection

Phát hiện khi các ByteRange overlap không hợp lệ.

**Case phát hiện lỗi:**
```
[Foxit SDK] ByteRange Overlap: Phát hiện overlap giữa Rev.2 và Rev.1 tại offset 1200-1500
```

### 4. Incremental Update Validation

Kiểm tra incremental update có hợp lệ không.

**Incremental update hợp lệ:**
- Revision mới phải bắt đầu sau khi revision cũ kết thúc hoàn toàn

**Case phát hiện lỗi:**
```
[Foxit SDK] Incremental Update Error: Rev.2 bắt đầu tại offset 3000, 
nhưng Rev.1 chưa kết thúc (kết thúc tại 3500). 
Revision mới đã ghi đè lên dữ liệu của revision cũ, làm hỏng chữ ký trước đó.
```

### 5. Coverage Warning

Cảnh báo khi chữ ký không cover toàn bộ revision:

```
[Foxit SDK] Coverage Warning: Chữ ký Rev.2 không cover toàn bộ revision. 
Coverage: CONTIGUOUS_BLOCK_FROM_START
```

## Validation Summary

Kết quả validation được tổng hợp trong `structure_validation`:

```json
{
  "structure_validation": {
    "has_byterange_error": true,
    "is_structure_valid": false,
    "validation_summary": "Invalid - ByteRange Error (Foxit strict validation): [Foxit SDK] ByteRange Integrity Error...",
    "byterange": "[0, 1000, 1500, 2000]",
    "revision_number": 1,
    "is_incremental_update": false,
    "formatting_errors": [
      "[Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè lên vùng signature của Revision 1..."
    ],
    "warnings": []
  }
}
```

## So sánh với Foxit SDK

| Feature | PyHanko Default | This Implementation | Foxit SDK |
|---------|----------------|---------------------|-----------|
| ByteRange basic check | ✅ | ✅ | ✅ |
| Detect Rev.2 corrupts Rev.1 | ❌ | ✅ | ✅ |
| ByteRange overlap detection | ❌ | ✅ | ✅ |
| Incremental update validation | ❌ | ✅ | ✅ |
| Detailed error messages | ❌ | ✅ | ✅ |
| Coverage warnings | ❌ | ✅ | ✅ |

## Usage

### API Endpoint

```bash
curl -X POST http://localhost:5001/api/verify-pdf \
  -F "file=@sample_signed.pdf"
```

### Test Script

```bash
cd pdf-python
python test_byterange_validation.py sample_signed.pdf
```

### Python Code

```python
from api import read_pdf_signatures

signatures = read_pdf_signatures("sample_signed.pdf")

for sig in signatures:
    struct = sig['structure_validation']
    
    if struct['has_byterange_error']:
        print("❌ ByteRange Error Detected!")
        for error in struct['formatting_errors']:
            if 'ByteRange Integrity' in error:
                print(f"  CRITICAL: {error}")
```

## Test Cases

### Test Case 1: Valid Single Signature
**File:** `valid_single_sig.pdf`
**Expected:** ✅ Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)

### Test Case 2: Valid Double Signature (Incremental Update)
**File:** `valid_double_sig.pdf`
**Expected:** 
- Rev.1: ✅ Valid
- Rev.2: ✅ Valid (incremental update hợp lệ)

### Test Case 3: Invalid - Rev.2 Corrupts Rev.1
**File:** `invalid_corrupted_sig.pdf`
**Expected:**
- Rev.1: ✅ Valid
- Rev.2: ❌ Invalid - ByteRange Integrity Error

### Test Case 4: Invalid - ByteRange Overlap
**File:** `invalid_overlap.pdf`
**Expected:** ❌ Invalid - ByteRange Overlap detected

## Debug Output

Enable debug mode để xem chi tiết:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

signatures = read_pdf_signatures("sample.pdf")
```

## Troubleshooting

**Q: Tại sao Rev.2 được báo lỗi dù file mở bình thường?**
A: Một số PDF reader bỏ qua lỗi ByteRange, nhưng Foxit SDK kiểm tra nghiêm ngặt. Nếu Rev.2 ghi đè lên vùng signature của Rev.1, đó là lỗi thực sự cần được cảnh báo.

**Q: Incremental update hợp lệ cần điều kiện gì?**
A: Revision mới phải bắt đầu từ offset sau khi revision cũ kết thúc. Không được overlap.

**Q: Có thể tắt strict validation không?**
A: Không nên. Strict validation giúp phát hiện các cuộc tấn công manipulate PDF sau khi đã ký.

## References

- [PDF Reference 1.7 - Digital Signatures](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/PDF32000_2008.pdf)
- [Foxit PDF SDK Documentation](https://developers.foxit.com/)
- [PyHanko Documentation](https://pyhanko.readthedocs.io/)
