# Example API Response - ByteRange Validation

## Case 1: Valid Single Signature ✅

```json
{
  "success": true,
  "count": 1,
  "signatures": [
    {
      "field_name": "Signature1",
      "signer": {
        "common_name": "CÔNG TY CỔ PHẦN ABC",
        "user_id": "MST:0314363533",
        "country": "VN"
      },
      "issuer": {
        "common_name": "FastCA SHA-256 R1",
        "country": "VN"
      },
      "signing_time": "2025-12-23T10:30:00+07:00",
      "valid_from": "2025-01-01T00:00:00+00:00",
      "valid_until": "2026-01-01T00:00:00+00:00",
      "is_valid": true,
      "is_expired": false,
      "intact": true,
      "document_unchanged": true,
      "valid_at_signing_time": true,
      "coverage": "SignatureCoverageLevel.ENTIRE_FILE",
      "total_size": 500000,
      "structure_validation": {
        "has_byterange_error": false,
        "has_timestamp": true,
        "timestamp_source": "TSA Server",
        "has_ltv": true,
        "has_crl": true,
        "has_ocsp": true,
        "revision_number": 0,
        "is_incremental_update": false,
        "formatting_errors": [],
        "warnings": [],
        "is_structure_valid": true,
        "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
        "byterange": "[0, 10000, 15000, 485000]"
      }
    }
  ]
}
```

## Case 2: Valid Double Signature (Incremental Update) ✅✅

```json
{
  "success": true,
  "count": 2,
  "signatures": [
    {
      "field_name": "Signature1",
      "signer": {
        "common_name": "CÔNG TY ABC"
      },
      "structure_validation": {
        "has_byterange_error": false,
        "revision_number": 0,
        "is_incremental_update": false,
        "formatting_errors": [],
        "warnings": [],
        "is_structure_valid": true,
        "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
        "byterange": "[0, 10000, 15000, 485000]"
      }
    },
    {
      "field_name": "Signature2",
      "signer": {
        "common_name": "CÔNG TY XYZ"
      },
      "structure_validation": {
        "has_byterange_error": false,
        "revision_number": 1,
        "is_incremental_update": true,
        "formatting_errors": [],
        "warnings": [],
        "is_structure_valid": true,
        "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
        "byterange": "[0, 500000, 505000, 200000]"
      }
    }
  ]
}
```

## Case 3: Invalid - Rev.2 Corrupts Rev.1 ❌

```json
{
  "success": true,
  "count": 2,
  "signatures": [
    {
      "field_name": "Signature1",
      "signer": {
        "common_name": "CÔNG TY ABC"
      },
      "intact": true,
      "document_unchanged": true,
      "structure_validation": {
        "has_byterange_error": false,
        "revision_number": 0,
        "is_incremental_update": false,
        "formatting_errors": [],
        "warnings": [],
        "is_structure_valid": true,
        "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
        "byterange": "[0, 10000, 15000, 485000]"
      }
    },
    {
      "field_name": "Signature2",
      "signer": {
        "common_name": "CÔNG TY XYZ"
      },
      "intact": false,
      "document_unchanged": false,
      "structure_validation": {
        "has_byterange_error": true,
        "revision_number": 1,
        "is_incremental_update": true,
        "formatting_errors": [
          "[Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè lên vùng signature của Revision 1 (offset 10000-15000). Điều này làm hỏng cấu trúc chữ ký trước đó. Warning: Document has been modified after signing (Rev.1 corrupted by Rev.2)"
        ],
        "warnings": [],
        "is_structure_valid": false,
        "validation_summary": "Invalid - ByteRange Error (Foxit strict validation): [Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè lên vùng signature của Rev...",
        "byterange": "[0, 12000, 18000, 482000]"
      }
    }
  ]
}
```

**Giải thích:**
- Rev.1 ByteRange: `[0, 10000, 15000, 485000]`
  - Vùng signature content: bytes 10000-14999
- Rev.2 ByteRange: `[0, 12000, 18000, 482000]`
  - Vùng signed bao gồm: bytes 0-11999
  - ❌ **Vùng 10000-11999 ghi đè lên signature content của Rev.1**
  - 🔴 **CRITICAL: Rev.2 đã làm hỏng Rev.1!**

## Case 4: Invalid - ByteRange Not Starting from 0 ❌

```json
{
  "success": true,
  "count": 1,
  "signatures": [
    {
      "field_name": "Signature1",
      "structure_validation": {
        "has_byterange_error": true,
        "formatting_errors": [
          "[Foxit SDK] ByteRange Error: ByteRange phải bắt đầu từ offset 0"
        ],
        "warnings": [],
        "is_structure_valid": false,
        "validation_summary": "Invalid - ByteRange Error (Foxit strict validation): [Foxit SDK] ByteRange Error: ByteRange phải bắt đầu từ offset 0",
        "byterange": "[100, 10000, 15000, 485000]"
      }
    }
  ]
}
```

## Case 5: Warning - Missing LTV Info ⚠️

```json
{
  "success": true,
  "count": 1,
  "signatures": [
    {
      "field_name": "Signature1",
      "structure_validation": {
        "has_byterange_error": false,
        "has_ltv": false,
        "has_crl": false,
        "has_ocsp": false,
        "formatting_errors": [],
        "warnings": [
          "Thiếu thông tin LTV (CRL/OCSP) cho Long Term Validation"
        ],
        "is_structure_valid": true,
        "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
        "byterange": "[0, 10000, 15000, 485000]"
      }
    }
  ]
}
```

**Note:** Warnings không làm chữ ký invalid, chỉ là thông tin cảnh báo.

## Frontend Integration

### Display Validation Status

```typescript
interface StructureValidation {
  has_byterange_error: boolean;
  is_structure_valid: boolean;
  formatting_errors: string[];
  warnings: string[];
  validation_summary: string;
  byterange?: string;
}

function displayValidationStatus(validation: StructureValidation) {
  if (validation.has_byterange_error) {
    // Show CRITICAL error
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>ByteRange Integrity Error</AlertTitle>
        <AlertDescription>
          {validation.formatting_errors.map((error, idx) => (
            <div key={idx} className="mt-2">
              {error}
            </div>
          ))}
        </AlertDescription>
      </Alert>
    );
  }
  
  if (!validation.is_structure_valid) {
    // Show error
    return (
      <Alert variant="destructive">
        <AlertTitle>Invalid Signature</AlertTitle>
        <AlertDescription>
          {validation.validation_summary}
        </AlertDescription>
      </Alert>
    );
  }
  
  if (validation.warnings.length > 0) {
    // Show warnings
    return (
      <Alert variant="warning">
        <AlertTitle>Valid with Warnings</AlertTitle>
        <AlertDescription>
          {validation.warnings.map((warning, idx) => (
            <div key={idx}>{warning}</div>
          ))}
        </AlertDescription>
      </Alert>
    );
  }
  
  // Valid
  return (
    <Alert variant="success">
      <CheckCircle className="h-4 w-4" />
      <AlertTitle>Valid Signature</AlertTitle>
      <AlertDescription>
        {validation.validation_summary}
      </AlertDescription>
    </Alert>
  );
}
```

## Testing with cURL

```bash
# Test with a signed PDF
curl -X POST http://localhost:5001/api/verify-pdf \
  -F "file=@sample_signed.pdf" \
  | jq '.signatures[].structure_validation'

# Expected output for valid signature:
{
  "has_byterange_error": false,
  "is_structure_valid": true,
  "formatting_errors": [],
  "warnings": [],
  "validation_summary": "Valid - Cấu trúc chữ ký hợp lệ (Foxit SDK compliant)",
  "byterange": "[0, 10000, 15000, 485000]"
}

# Expected output for corrupted signature:
{
  "has_byterange_error": true,
  "is_structure_valid": false,
  "formatting_errors": [
    "[Foxit SDK] ByteRange Integrity Error: Revision 2 đã ghi đè..."
  ],
  "warnings": [],
  "validation_summary": "Invalid - ByteRange Error (Foxit strict validation)...",
  "byterange": "[0, 12000, 18000, 482000]"
}
```
