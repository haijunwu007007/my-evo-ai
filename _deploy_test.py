"""SCP fixed agent_core.py and test on public server"""
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# SCP the fixed file
sftp = ssh.open_sftp()
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_core.py', 'r', encoding='utf-8') as f:
    content = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/agent_core.py', 'w') as f:
    f.write(content)
sftp.close()
print('SCP agent_core.py: OK')

# Restart
ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(8)

# Test 1: Simple chat (should now return real LLM response, not fallback)
_,o1,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"你好"}\' '
    '--max-time 60',
    timeout=65
)
r1 = o1.read().decode()
print('CHAT:', r1[:500])

# Test 2: Search (should use web_search tool)
_,o2,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"搜索Python最新版本"}\' '
    '--max-time 90',
    timeout=95
)
r2 = o2.read().decode()
print('SEARCH:', r2[:800])

# Test 3: Draw image (should call Zhipu API)
_,o3,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"画一只猫"}\' '
    '--max-time 90',
    timeout=95
)
r3 = o3.read().decode()
print('DRAW:', r3[:800])

ssh.close()
print("DONE")
