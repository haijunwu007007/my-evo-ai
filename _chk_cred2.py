"""Quick check for Tencent cloud API keys"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

cmds = [
    'cat /home/ubuntu/.tencentcloud/credentials 2>/dev/null || echo NF',
    'find /home/ubuntu -maxdepth 2 -name "credentials" 2>/dev/null | head -3',
    'env | grep -iE "SECRET" 2>/dev/null | head -5',
]
for c in cmds:
    _,o,_ = ssh.exec_command(c, timeout=8)
    r = o.read().decode().strip()
    print(f'CMD: {c[:50]}')
    print(f'  => {r[:200]}\n')

ssh.close()
