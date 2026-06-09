"""SCP修复后的文件到公网服务器并重启"""
import paramiko, time, os
from pathlib import Path

BASE = Path(r"D:\AUTO-EVO-AI-V0.1")
REMOTE = "/home/ubuntu/my-evo-ai"

# 所有被修改过的文件（基于git diff）
changed_files = [
    "api/routes/routes_mcp.py",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)
sftp = ssh.open_sftp()

for f in changed_files:
    local = str(BASE / f)
    remote = f"{REMOTE}/{f}"
    if Path(local).exists():
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote)
        ssh.exec_command(f"mkdir -p {remote_dir}", timeout=5)
        sftp.put(local, remote)
        print(f"  {f} -> OK")

sftp.close()

# 重启服务
print("Restarting...")
stdin,stdout,stderr = ssh.exec_command("sudo systemctl restart evo.service", timeout=10)
print(stdout.read().decode(errors='replace')[:200])
print(stderr.read().decode(errors='replace')[:200])

time.sleep(5)

# 验证
stdin2,stdout2,stderr2 = ssh.exec_command("curl -s http://127.0.0.1:8765/api/v1/version 2>&1", timeout=10)
ver = stdout2.read().decode(errors='replace')[:200]
print(f"VERIFY: {ver}")

ssh.close()
print("DONE")
