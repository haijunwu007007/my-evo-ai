"""SCP deploy and verify on public server"""
import paramiko, time, json, os, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

BASE = r"D:\AUTO-EVO-AI-V0.1"

# Files to SCP
files_to_scp = [
    "api/agent_core.py",
    "api/agent_tools.py",
    "api/agent_llm.py",
    "api/middleware.py",
    "api/infra.py",
    "api/startup.py",
    "api_server.py",
    "frontend/chat.html",
]
# Add all routes and agents
routes_dir = os.path.join(BASE, "api/routes")
agents_dir = os.path.join(BASE, "api/agents")
for f in os.listdir(routes_dir):
    if f.endswith(".py"):
        files_to_scp.append(f"api/routes/{f}")
for f in os.listdir(agents_dir):
    if f.endswith(".py"):
        files_to_scp.append(f"api/agents/{f}")
# Also core modules
core_dir = os.path.join(BASE, "core")
for f in os.listdir(core_dir):
    if f.endswith(".py"):
        files_to_scp.append(f"core/{f}")

sftp = ssh.open_sftp()
remote_base = "/home/ubuntu/my-evo-ai"

total = len(files_to_scp)
for i, relpath in enumerate(files_to_scp):
    local = os.path.join(BASE, relpath.replace("/", os.sep))
    remote = f"{remote_base}/{relpath}"
    try:
        # Ensure remote dir exists
        rdir = "/".join(remote.split("/")[:-1])
        ssh.exec_command(f"mkdir -p {rdir}", timeout=5)
        sftp.put(local, remote)
    except Exception as e:
        print(f"  {i+1}/{total} FAIL {relpath}: {e}")
        continue

sftp.close()
print(f"SCP {total} files: OK")

# Restart
_,o1,_ = ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(8)

# Verify API
_,o2,_ = ssh.exec_command('curl -s http://127.0.0.1:8766/api/v1/version --max-time 5', timeout=10)
print(f"VERSION: {o2.read().decode()[:150]}")

# Test chat
_,o3,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"你好"}\' --max-time 30', timeout=35)
r3 = o3.read().decode()
try:
    d3 = json.loads(r3)
    print(f"CHAT: mode={d3.get('mode')} result={d3.get('result','')[:80]}")
except:
    print(f"CHAT ERR: {r3[:200]}")

# Test HTTPS
try:
    import httpx
    r4 = httpx.get('https://autoevoai.com/api/v1/version', timeout=10, verify=False)
    print(f"HTTPS: {r4.status_code} {r4.json().get('version','')[:30]}")
except Exception as e:
    print(f"HTTPS: {str(e)[:100]}")

ssh.close()
print("DONE")
