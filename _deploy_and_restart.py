"""部署并重启"""
import urllib.request, json, time, binascii

REMOTE = "/home/ubuntu/my-evo-ai/api/routes/routes_static.py"
LOCAL = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"
HOST = "https://autoevoai.com"

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request(f"{HOST}/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"}), timeout=15).read().decode())

# Write
hex_data = open(LOCAL, "rb").read().hex()
for i in range(0, len(hex_data), 200):
    c = hex_data[i:i+200]
    mode = "wb" if i == 0 else "ab"
    r = api("python3", f"-c \"import binascii; open('{REMOTE}','{mode}').write(binascii.unhexlify('{c}'))\"")
    if not r.get("success"):
        print(f"FAIL chunk {i}: {r.get('stderr','')}")

# Verify size
r = api("python3", f"-c \"import os; print(os.path.getsize('{REMOTE}'))\"")
print(f"Size: {r.get('stdout','')} vs local {len(open(LOCAL,'rb').read())}")

# Restart
api("pkill", "-f api_server")
time.sleep(2)

# Test
for i in range(25):
    try:
        r = urllib.request.urlopen(f"{HOST}/agents", timeout=5)
        print(f"OK /agents -> {r.status} ({i+1}s)")
        print(f"Location: {r.headers.get('location','')}")
        break
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print(f"OK redirect to {e.headers.get('location','')}")
            break
        if i < 23:
            time.sleep(1)
        else:
            print(f"FAIL: {e.code}")
    except:
        time.sleep(1)
