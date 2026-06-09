"""Check all remaining system defects"""
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, t=15):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(1)
    r=b''
    while o.channel.recv_ready(): r+=o.channel.recv(4096)
    return r.decode(errors='replace').strip()[:800]

# 1. API basic
print('=== 1. 基础API ===')
print('Version:', run('curl -s http://127.0.0.1:8766/api/v1/version', 10))

# 2. Chat
print('\n=== 2. 智能聊天 ===')
_,o,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"你好"}\' --max-time 30', timeout=35)
r = o.read().decode(errors='replace')[:300]
print('你好:', r)

# 3. Search
_,o2,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart '
    '-H "Content-Type: application/json" '
    '-d \'{"message":"搜索Python"}\' --max-time 60', timeout=65)
r2 = o2.read().decode(errors='replace')[:400]
print('搜索:', r2)

# 4. HTTPS
print('\n=== 3. HTTPS ===')
print('Local:', run('curl -sk https://127.0.0.1/api/v1/version', 10))
print('Ports:', run("ss -tlnp | grep -E '443|80'", 5))

# 5. Docker
print('\n=== 4. Docker容器 ===')
for p, n in [('7700','MeiliSearch'),('3001','UptimeKuma'),('9001','MinIO'),('8081','NocoDB')]:
    r = run(f'curl -s --connect-timeout 3 http://127.0.0.1:{p}/ 2>&1', 8)
    print(f'{n}:', r[:80])

# 6. Git status
print('\n=== 5. Git状态 ===')
print('Branch:', run('cd /home/ubuntu/my-evo-ai && git log --oneline -3', 5))
print('Status:', run('cd /home/ubuntu/my-evo-ai && git status --short | head -20', 5))

# 7. Service health
print('\n=== 6. 服务状态 ===')
print('Evo:', run('sudo systemctl is-active evo.service', 5))
print('CPU:', run("top -bn1 | head -3", 5))
print('Memory:', run("free -h | head -2", 5))

ssh.close()
print('\nDONE')
