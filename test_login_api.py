#!/usr/bin/env python3
import json
import subprocess

# Test login via curl
cmd = [
    "docker", "exec", "weather-api", "python", "-m", "http.client",
    "POST", "/api/v1/auth/login", 
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"username": "admin", "password": "admin"})
]

print("Testing login with admin/admin...")
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
