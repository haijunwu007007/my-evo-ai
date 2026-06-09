"""排查公网启动错误"""
import paramiko, time, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

def run(cmd):
    stdin,stdout,stderr = ssh.exec_command(cmd, timeout=10)
    return stdout.read().decode(errors='replace') + stderr.read().decode(errors='replace')

# 看journalctl里搜Error和Traceback
print("=== journalctl search ===")
print(run("sudo journalctl -u evo.service --since '2 min ago' --no-pager 2>&1 | grep -i 'error\\|traceback\\|import\\|module' | tail -15"))

# 看完整最新一次启动的报错
print("=== full latest log ===")
print(run("sudo journalctl -u evo.service -n 30 --no-pager 2>&1 | tail -30"))

ssh.close()
print("\nDONE")
