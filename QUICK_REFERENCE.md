# ByteRange Validation - Quick Reference

## 🎯 Mục đích
Phát hiện khi **Rev.2 làm hỏng Rev.1** trong PDF có nhiều chữ ký số.

## 📐 ByteRange Format
```
[start1, length1, start2, length2]
```

**Vùng được sign:**
- Vùng 1: `[start1, start1+length1)`
- Vùng 2: `[start2, start2+length2)`

**Vùng signature content (KHÔNG được sign):**
- `[start1+length1, start2)`

## ✅ Valid Cases

### Case 1: Single Signature
```
ByteRange: [0, 1000, 1500, 2000]
Status: ✅ Valid
```

### Case 2: Double Signature (Valid Incremental Update)
```
Rev.1: [0, 1000, 1500, 2000]  → End at 3500
Rev.2: [0, 3500, 4000, 1000]  → Start at 0, but only signs up to 3499
Status: ✅ Valid (no overlap)
```

## ❌ Invalid Cases

### Case 1: Rev.2 Corrupts Rev.1 Signature Content
```
Rev.1: [0, 1000, 1500, 2000]
       Signature content: 1000-1499

Rev.2: [0, 1200, 1800, 2500]
       Signs: 0-1199 (overlaps 1000-1199 of Rev.1 signature)

Status: ❌ INVALID
Error: [Foxit SDK] ByteRange Integrity Error
```

### Case 2: ByteRange Not Starting from 0
```
ByteRange: [100, 1000, 1500, 2000]

Status: ❌ INVALID
Error: [Foxit SDK] ByteRange Error: ByteRange phải bắt đầu từ offset 0
```

### Case 3: Invalid Incremental Update
```
Rev.1: [0, 1000, 1500, 2000]  → End at 3500
Rev.2: [0, 1000, 3000, 1000]  → Starts at 3000 (before Rev.1 ends)

Status: ❌ INVALID
Error: [Foxit SDK] Incremental Update Error
```

## 🔍 Validation Logic

```python
# 1. Track all ByteRanges
all_byte_ranges = []

# 2. For each signature
for sig in signatures:
    byte_range = sig.byte_range
    
    # 3. Check against previous signatures
    for prev_br in all_byte_ranges:
        # Calculate signature content area
        prev_sig_start = prev_br[0] + prev_br[1]
        prev_sig_end = prev_br[2]
        
        # Check if current ByteRange overlaps signature content
        if current_overlaps(prev_sig_start, prev_sig_end):
            # ❌ ERROR: Rev.N corrupted by Rev.M
            
    # 4. Save for next iteration
    all_byte_ranges.append(byte_range)
```

## 📊 Response Structure

```json
{
  "structure_validation": {
    "has_byterange_error": false,
    "is_structure_valid": true,
    "formatting_errors": [],
    "warnings": [],
    "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
    "byterange": "[0, 10000, 15000, 485000]",
    "revision_number": 0,
    "is_incremental_update": false
  }
}
```

## 🚨 Error Messages

### Critical Errors (has_byterange_error = true)

```
[Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè lên 
vùng signature của Revision 1 (offset 1000-1500). Điều này làm hỏng 
cấu trúc chữ ký trước đó. Warning: Document has been modified after 
signing (Rev.1 corrupted by Rev.2)
```

```
[Foxit SDK] ByteRange Error: ByteRange phải bắt đầu từ offset 0
```

```
[Foxit SDK] ByteRange Overlap: Phát hiện overlap giữa Rev.2 và Rev.1 
tại offset 1200-1500
```

```
[Foxit SDK] Incremental Update Error: Rev.2 bắt đầu tại offset 3000, 
nhưng Rev.1 chưa kết thúc (kết thúc tại 3500). Revision mới đã ghi đè 
lên dữ liệu của revision cũ, làm hỏng chữ ký trước đó.
```

### Warnings (not critical)

```
[Foxit SDK] Coverage Warning: Chữ ký Rev.2 không cover toàn bộ revision.
```

```
Thiếu thông tin LTV (CRL/OCSP) cho Long Term Validation
```

## 🧪 Testing Commands

```bash
# Test with script
python3 test_byterange_validation.py sample.pdf

# Test with API
curl -X POST http://localhost:5001/api/verify-pdf \
  -F "file=@sample.pdf" \
  | jq '.signatures[].structure_validation'

# Check for ByteRange errors
curl -X POST http://localhost:5001/api/verify-pdf \
  -F "file=@sample.pdf" \
  | jq '.signatures[] | select(.structure_validation.has_byterange_error == true)'
```

## 🎨 Frontend Display

```typescript
// Show status badge
{validation.has_byterange_error ? (
  <Badge variant="destructive">ByteRange Error</Badge>
) : validation.is_structure_valid ? (
  <Badge variant="success">Valid</Badge>
) : (
  <Badge variant="warning">Invalid</Badge>
)}

// Show error details
{validation.formatting_errors.map(error => (
  error.includes('ByteRange Integrity') && (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Critical: Signature Corrupted</AlertTitle>
      <AlertDescription>{error}</AlertDescription>
    </Alert>
  )
))}
```

## 📖 Decision Tree

```
Start
  ↓
Has ByteRange? 
  → No → Warning
  → Yes ↓
  
ByteRange starts from 0?
  → No → ❌ ERROR
  → Yes ↓
  
Has 4 numbers?
  → No → ❌ ERROR
  → Yes ↓
  
Overlaps with previous signatures?
  → Yes ↓
    Overlaps signature content area?
      → Yes → ❌ CRITICAL ERROR (Rev.N corrupted)
      → No → Check next
  → No ↓
  
Is incremental update?
  → Yes ↓
    Starts after previous revision ends?
      → No → ❌ ERROR
      → Yes → ✅ VALID
  → No → ✅ VALID
```

## 🔗 Related Files

- Implementation: [`pdf-python/api.py`](pdf-python/api.py#L142-L220)
- Test script: [`pdf-python/test_byterange_validation.py`](pdf-python/test_byterange_validation.py)
- Full docs: [`pdf-python/BYTERANGE_VALIDATION.md`](pdf-python/BYTERANGE_VALIDATION.md)
- Examples: [`pdf-python/EXAMPLE_RESPONSES.md`](pdf-python/EXAMPLE_RESPONSES.md)

## 💡 Pro Tips

1. **Always check `has_byterange_error` first** - This is the most critical flag
2. **ByteRange Integrity Errors are CRITICAL** - Never ignore them
3. **Warnings are informational** - They don't invalidate the signature
4. **Test with real multi-signature PDFs** - Single signature PDFs won't test overlap logic
5. **Check both `is_structure_valid` and `has_byterange_error`** - They serve different purposes
