import requests
import json

# Test REST API
url = "http://localhost:5001/api/verify-pdf"

# Upload file PDF
with open("Test.pdf", "rb") as f:
    response = requests.post(url, files={"file": f})
    
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
