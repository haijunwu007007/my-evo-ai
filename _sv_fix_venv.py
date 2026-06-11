"""修复公网服务器venv"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15)

def run(cmd, t=30):
    si,so,se = ssh.exec_command(cmd, timeout=t)
    out = so.read().decode(errors='replace')
    err = se.read().decode(errors='replace')[:500]
    return (out + err).strip()[:500]

# Step 1: Fix venv - recreate it
print("=== 重建venv ===")
out = run("cd /home/ubuntu/my-evo-ai && rm -rf venv && python3 -m venv venv 2>&1")
print(f"Create venv: {out[:200]}")

# Step 2: Install packages
print("\n=== 安装依赖 ===")
if "Error" not in out:
    out = run("cd /home/ubuntu/my-evo-ai && venv/bin/pip install --quiet uvicorn fastapi httpx websockets jinja2 python-multipart aiofiles python-dotenv 2>&1", 120)
    print(f"Install: {out[:300]}")

# Step 3: Verify
print("\n=== 验证 ===")
out = run("ls /home/ubuntu/my-evo-ai/venv/bin/uvicorn 2>&1")
print(f"Uvicorn binary: {out[:100]}")

out = run("python3 -c 'import fastapi; print(\"FASTAPI_OK\")' 2>&1")
print(f"FastAPI: {out[:200]}")

# Step 4: Restart service
print("\n=== 重启服务 ===")
out = run("sudo systemctl restart evo.service 2>&1", 10)
print(f"Restart: {out[:200]}")

time.sleep(5)

# Step 5: Verify
out = run("curl -s http://127.0.0.1/api/v1/version 2>&1", 10)
print(f"\nVersion: {out[:200]}")

out = run("sudo systemctl is-active evo.service 2>&1", 10)
print(f"Service: {out[:100]}")

ssh.close()
print("\nDONE")
