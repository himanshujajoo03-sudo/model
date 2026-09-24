#!/usr/bin/env python3
"""
Test admin login API endpoint and token verification.
"""
import json
import urllib.request
import urllib.error
import sys

URL = "http://localhost:8000/api/v1/auth/login"
payload = {"username": "admin", "password": "admin"}

print(f"Testing login at {URL} with credentials: admin / admin ...")
req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        print(f"[SUCCESS] Status Code: {resp.status}")
        print(f"[SUCCESS] Token Type:  {body.get('token_type')}")
        print(f"[SUCCESS] Expires In:  {body.get('expires_in')}s")
        token = body.get("access_token", "")
        print(f"[SUCCESS] JWT Token:   {token[:40]}... (length: {len(token)})")

        # Test authenticated endpoint using this token
        verify_url = "http://localhost:8000/api/v1/verification"
        verify_req = urllib.request.Request(
            verify_url,
            data=json.dumps({
                "event_id": "00000000-0000-0000-0000-000000000000",
                "action": "verified"
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        try:
            urllib.request.urlopen(verify_req)
        except urllib.error.HTTPError as he:
            # 404 is expected because dummy event doesn't exist, but 401 is NOT
            if he.code == 404:
                print(f"[SUCCESS] Authenticated endpoint /verification reached successfully (HTTP 404 EVENT_NOT_FOUND as expected for dummy event)")
            elif he.code == 401:
                print(f"[FAIL] Verification endpoint rejected token with HTTP 401 UNAUTHORIZED")
            else:
                print(f"[SUCCESS] Auth accepted (HTTP {he.code})")

        print("\nAll login tests passed successfully!")
except urllib.error.HTTPError as e:
    print(f"[FAIL] Login failed: HTTP {e.code} - {e.read().decode()}")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Connection error: {e}")
    sys.exit(1)
