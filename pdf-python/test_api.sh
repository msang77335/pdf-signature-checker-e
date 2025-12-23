#!/bin/bash

# Test script cho PDF Signature Verification API

echo "=== Testing PDF Signature Verification API ==="
echo ""

# 1. Health check
echo "1. Health Check:"
curl -X GET http://localhost:5001/api/health
echo -e "\n"

# 2. Get API info
echo "2. API Info:"
curl -X GET http://localhost:5001/
echo -e "\n"

# 3. Verify PDF (thay Test.pdf bằng file của bạn)
echo "3. Verify PDF Signature:"
curl -X POST http://localhost:5001/api/verify-pdf \
  -F "file=@Test.pdf" \
  -H "Content-Type: multipart/form-data"
echo -e "\n"
