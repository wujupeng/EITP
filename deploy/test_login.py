import urllib.request
import json

url = "http://localhost:8000/api/v1/auth/login"
data = json.dumps({
    "tenant_id": "03724bb5-fd4d-46e5-af21-c794b559d406",
    "username": "admin",
    "password": "Qk@2026#Secure99"
}).encode("utf-8")
headers = {
    "Content-Type": "application/json",
    "X-Tenant-Token": "00000000-0000-0000-0000-000000000001",
}
req = urllib.request.Request(url, data=data, headers=headers, method="POST")
try:
    resp = urllib.request.urlopen(req)
    print("Status:", resp.status)
    result = json.loads(resp.read())
    print("Login OK!")
    print("Access Token:", result["access_token"][:50] + "...")
    print("Username:", result["username"])
    print("Tenant ID:", result["tenant_id"])
    print("Is Tenant Admin:", result["is_tenant_admin"])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Response:", e.read().decode())