"""One-shot deploy - write entire file in a single command"""
import json, urllib.request, sys, time, base64

H = 'https://autoevoai.com'
FILES = [
    ('/home/ubuntu/my-evo-ai/frontend/chat_engine.js', 'D:/AUTO-EVO-AI-V0.1/frontend/chat_engine.js'),
    ('/home/ubuntu/my-evo-ai/frontend/chat.html', 'D:/AUTO-EVO-AI-V0.1/frontend/chat.html'),
    ('/home/ubuntu/my-evo-ai/frontend/experts.html', 'D:/AUTO-EVO-AI-V0.1/frontend/experts.html'),
]

def run(cmd):
    p = json.dumps({"cmd": cmd}).encode()
    r = urllib.request.urlopen(urllib.request.Request(H+'/api/v1/cli/exec', data=p, headers={'Content-Type':'application/json'}), timeout=120)
    return json.loads(r.read())

for remote, local in FILES:
    with open(local, 'rb') as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode()
    fname = remote.split('/')[-1]
    print(f'=== {fname} ({len(raw)} bytes, {len(b64)} base64) ===')
    # Write in one shot - base64 in command line
    cmd = f"python3 -c \"import base64;open('{remote}','wb').write(base64.b64decode('{b64}'))\""
    r = run(cmd)
    if r.get('code') == 0:
        print(f'  OK')
    else:
        print(f'  FAIL: {r.get("stderr","")[:200]}')

print()
print('=== Verify server ===')
r = run("python3 -c \"import os; print('JS:', os.path.getsize('/home/ubuntu/my-evo-ai/frontend/chat_engine.js')); print('HTML:', os.path.getsize('/home/ubuntu/my-evo-ai/frontend/chat.html'))\"")
print(r.get('stdout',''))

print('=== Atomic restart ===')
r = run("python3 -c \"import subprocess, os; subprocess.Popen(['nohup','bash','-c','sleep 5; pkill -9 -f api_server; sleep 3; cd /home/ubuntu/my-evo-ai; AI_DEFAULT_MODEL=zhipu:glm-4-flash nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print('OK')\"")
print(f'Restart: {r.get("stdout","")[:200]}')

time.sleep(14)
r = urllib.request.urlopen(H+'/frontend/chat_engine.js', timeout=10)
js = r.read()
print(f'JS served: {len(js)} bytes')
print(f'URLSearchParams: {b"URLSearchParams" in js}')
print(f'replaceState: {b"replaceState" in js}')
# check omitted - verify in next step
