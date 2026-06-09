"""排查启动失败"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

def run(cmd):
    stdin,stdout,stderr = ssh.exec_command(cmd, timeout=10)
    return stdout.read().decode(errors='replace')[:2000]

# 只看最新的报错
print(run("sudo journalctl -u evo.service -n 30 --no-pager 2>&1 | grep -E 'Error|error|Indentation|Traceback' | head -10"))

# 也看完整尾段
print("===TAIL===")
print(run("sudo journalctl -u evo.service -n 10 --no-pager 2>&1"))

ssh.close()
