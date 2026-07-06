"""Universal HTML deploy - hex chunks + no final verify (avoids 502 race)"""
import json, urllib.request, sys, time, base64
HOST = 'https://autoevoai.com'
REMOTE = '/home/ubuntu/my-evo-ai/frontend/chat.html'
LOCAL = 'D:/AUTO-EVO-AI-V0.1/frontend/chat.html'

def run(cmd):
    p = json.dumps({"cmd": cmd}).encode()
    r = urllib.request.urlopen(urllib.request.Request(HOST+'/api/v1/cli/exec', data=p, headers={'Content-Type':'application/json'}), timeout=60)
    return json.loads(r.read())

with open(LOCAL, 'rb') as f:
    data = f.read()
print(f'Local: {len(data)} bytes')

hex_data = data.hex()
CHUNK = 400
total = (len(hex_data) + CHUNK - 1) // CHUNK

for i in range(0, len(hex_data), CHUNK):
    ch = hex_data[i:i+CHUNK]
    mode = 'wb' if i == 0 else 'ab'
    chunk_b64 = base64.b64encode(bytes.fromhex(ch)).decode()
    cmd = f"python3 -c \"import base64;open('{REMOTE}','{mode}').write(base64.b64decode('{chunk_b64}'))\""
    r = run(cmd)
    if r.get('code') != 0:
        print(f'FAIL [{i//CHUNK+1}/{total}]: {r.get("stderr","")[:100]}')
        sys.exit(1)
    if (i // CHUNK) % 20 == 0:
        print(f'  [{i//CHUNK+1}/{total}] OK')

print('HTML deployed.')
print('Use atomic_restart.py to restart.')
