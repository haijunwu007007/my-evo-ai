"""修复公网服务器 - 改用系统python3而不是venv"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15)

def run(cmd, t=30):
    si,so,se = ssh.exec_command(cmd, timeout=t)
    out = so.read().decode(errors='replace')
    err = se.read().decode(errors='replace')[:500]
    return (out + err).strip()[:500]

# Change service to use system python3
print("=== 修改evo.service ===")
run("sudo sed -i 's|/home/ubuntu/my-evo-ai/venv/bin/uvicorn|/usr/bin/python3 -m uvicorn|' /etc/systemd/system/evo.service 2>&1", 10)
out = run("cat /etc/systemd/system/evo.service | grep uvicorn", 10)
print(f"New ExecStart: {out[:200]}")

run("sudo systemctl daemon-reload 2>&1", 10)

print("\n=== 重启服务 ===")
out = run("sudo systemctl restart evo.service 2>&1", 10)
print(f"Restart: {out[:200]}")

time.sleep(8)

print("\n=== 验证 ===")
out = run("curl -s http://127.0.0.1/api/v1/version 2>&1", 10)
print(f"Version: {out[:200]}")

out = run("sudo systemctl is-active evo.service 2>&1", 10)
print(f"Service: {out[:100]}")

ssh.close()
print("\nDONE")
