"""One-shot deploy - write entire file in a single command"""
import json, urllib.request, sys, time, base64, os

H = 'https://autoevoai.com'
BASE = r'D:\AUTO-EVO-AI-V0.1'
FILES = [
    # frontend pages
    ('/home/ubuntu/my-evo-ai/frontend/chat_engine.js',     os.path.join(BASE, 'frontend/chat_engine.js')),
    ('/home/ubuntu/my-evo-ai/frontend/chat.html',           os.path.join(BASE, 'frontend/chat.html')),
    ('/home/ubuntu/my-evo-ai/frontend/experts.html',        os.path.join(BASE, 'frontend/experts.html')),
    ('/home/ubuntu/my-evo-ai/frontend/agents.html',         os.path.join(BASE, 'frontend/agents.html')),
    ('/home/ubuntu/my-evo-ai/frontend/skills.html',         os.path.join(BASE, 'frontend/skills.html')),
    ('/home/ubuntu/my-evo-ai/frontend/apps.html',           os.path.join(BASE, 'frontend/apps.html')),
    # new API routes
    ('/home/ubuntu/my-evo-ai/api/routes/routes_apps.py',    os.path.join(BASE, 'api/routes/routes_apps.py')),
    ('/home/ubuntu/my-evo-ai/api/routes/routes_smart_chat.py', os.path.join(BASE, 'api/routes/routes_smart_chat.py')),
    ('/home/ubuntu/my-evo-ai/api/routes/routes_learn.py',   os.path.join(BASE, 'api/routes/routes_learn.py')),
    ('/home/ubuntu/my-evo-ai/api/routes/routes_task_orchestrate.py', os.path.join(BASE, 'api/routes/routes_task_orchestrate.py')),
    # main server (has /api/v1/version, /api/v1/status endpoints)
    ('/home/ubuntu/my-evo-ai/api_server.py',                os.path.join(BASE, 'api_server.py')),
    # overview API
    ('/home/ubuntu/my-evo-ai/api/routes/routes_overview.py', os.path.join(BASE, 'api/routes/routes_overview.py')),
    # shared CSS
    ('/home/ubuntu/my-evo-ai/frontend/share.css',           os.path.join(BASE, 'frontend/share.css')),
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
print('=== Verify server files ===')
r = run("python3 -c \"import os; files = ['frontend/agents.html','frontend/skills.html','frontend/apps.html','api/routes/routes_apps.py','api_server.py']; base='/home/ubuntu/my-evo-ai/'; [print(f, os.path.getsize(base+f)) for f in files]\"")
print(r.get('stdout',''))

print('=== Atomic restart ===')
r = run("python3 -c \"import subprocess, os; subprocess.Popen(['nohup','bash','-c','sleep 5; pkill -9 -f api_server; sleep 3; cd /home/ubuntu/my-evo-ai; AI_DEFAULT_MODEL=zhipu:glm-4-flash nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print('OK')\"")
print(f'Restart: {r.get("stdout","")[:200]}')

time.sleep(14)
print('=== Verify new endpoints ===')
try:
    r = urllib.request.urlopen(H+'/api/v1/apps/list', timeout=10)
    print(f'  /api/v1/apps/list: {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'  /api/v1/apps/list: FAIL {e}')
try:
    r = urllib.request.urlopen(H+'/api/v1/version', timeout=10)
    print(f'  /api/v1/version: {r.status} ({r.read().decode()[:100]})')
except Exception as e:
    print(f'  /api/v1/version: FAIL {e}')
try:
    r = urllib.request.urlopen(H+'/apps', timeout=10)
    print(f'  /apps: {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'  /apps: FAIL {e}')
try:
    import urllib.parse
    r = urllib.request.urlopen(urllib.request.Request(H+'/api/v1/smart', data=json.dumps({"message":"hello"}).encode(), headers={'Content-Type':'application/json'}), timeout=10)
    print(f'  /api/v1/smart: {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'  /api/v1/smart: FAIL {e}')
try:
    r = urllib.request.urlopen(H+'/api/v1/learn', timeout=10)
    print(f'  /api/v1/learn: {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'  /api/v1/learn: FAIL {e}')
try:
    r = urllib.request.urlopen(urllib.request.Request(H+'/api/v1/task/orchestrate', data=json.dumps({"task":"test"}).encode(), headers={'Content-Type':'application/json'}), timeout=10)
    print(f'  /api/v1/task/orchestrate: {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'  /api/v1/task/orchestrate: FAIL {e}')
