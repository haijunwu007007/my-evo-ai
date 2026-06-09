"""Final server status check"""
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, t=10):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(1)
    r = b''
    while o.channel.recv_ready(): r += o.channel.recv(4096)
    return r.decode(errors='replace').strip()[:500]

# Git version
_,o,_ = ssh.exec_command('cd /home/ubuntu/my-evo-ai && git log --oneline -1 && echo SEP && git fetch origin 2>&1; echo SEP2; git log --oneline origin/master -1', timeout=15)
r = o.read().decode(errors='replace').strip()
print('GIT:', r[:500])

# Journal errors
_,o2,_ = ssh.exec_command('sudo journalctl -u evo.service --no-pager -n 50 2>&1 | grep -E "error|traceback|exception" | tail -3', timeout=10)
print('ERRORS:', o2.read().decode(errors='replace').strip()[:500])

# Disk
_,o3,_ = ssh.exec_command('df -h /', timeout=5)
print('DISK:', o3.read().decode(errors='replace').strip())

ssh.close()
