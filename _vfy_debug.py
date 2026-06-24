import urllib.request, json
r = urllib.request.urlopen("http://122.51.144.227:8765/api/v1/qodo-review/status", timeout=15)
d = json.loads(r.read())
print("Status:", r.status)
print("Response:", json.dumps(d, indent=2))
print()
# Try POST execute
body = json.dumps({"action":"status","params":{}}).encode()
req = urllib.request.Request("http://122.51.144.227:8765/api/v1/qodo-review/execute", data=body, headers={"Content-Type":"application/json"})
r2 = urllib.request.urlopen(req, timeout=15)
d2 = json.loads(r2.read())
print("POST Status:", r2.status)
print("POST Response:", json.dumps(d2, indent=2))
