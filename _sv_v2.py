"""简单验证"""
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

def run(cmd):
    stdin,stdout,stderr = ssh.exec_command(cmd, timeout=15)
    return stdout.read().decode(errors='replace')[:500]

# 先看service状态
print("SVC:", run("sudo systemctl is-active evo.service"))

# 尝试本地curl
print("LOCAL:", run("curl -s --connect-timeout 3 http://127.0.0.1:8765/api/v1/version 2>&1"))
print("LOCAL2:", run("curl -s --connect-timeout 3 http://127.0.0.1:8766/api/v1/version 2>&1"))

# journalctl最新
print("LOG:", run("sudo journalctl -u evo.service -n 5 --no-pager 2>&1 | tail -5"))

ssh.close()
