"""Sync to public server and test smart chat"""
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Git sync
_,o,_ = ssh.exec_command('cd /home/ubuntu/my-evo-ai && git fetch origin 2>&1 && git reset --hard origin/master 2>&1', timeout=30)
print('GIT:', o.read().decode()[:300])

# Restart
ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(8)

# Verify version
_,o2,_ = ssh.exec_command('curl -s http://127.0.0.1:8766/api/v1/version', timeout=10)
print('VERIFY:', o2.read().decode()[:300])

# Test smart chat
_,o3,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"你好"}\' '
    '--max-time 60',
    timeout=65
)
print('CHAT:', o3.read().decode()[:800])

# Test search tool
_,o4,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"搜索Python最新版本"}\' '
    '--max-time 90',
    timeout=95
)
print('SEARCH:', o4.read().decode()[:800])

ssh.close()
print("DONE")
