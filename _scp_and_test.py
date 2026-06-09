"""SCP fixed files to public server"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# SCP the 2 fixed files
sftp = ssh.open_sftp()

# Fix 1: routes_smart_chat.py
with open(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_smart_chat.py', 'r', encoding='utf-8') as f:
    content1 = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/routes/routes_smart_chat.py', 'w') as f:
    f.write(content1)
print('SCP routes_smart_chat.py: OK')

# Fix 2: agent_core.py
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_core.py', 'r', encoding='utf-8') as f:
    content2 = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/agent_core.py', 'w') as f:
    f.write(content2)
print('SCP agent_core.py: OK')

sftp.close()

# Restart
ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(8)

# Verify version
_,o2,_ = ssh.exec_command('curl -s http://127.0.0.1:8766/api/v1/version', timeout=10)
print('VERIFY:', o2.read().decode()[:200])

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
