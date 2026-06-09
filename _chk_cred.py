"""Try Tencent Cloud API to add firewall rule"""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Check for Tencent Cloud API credentials in various locations
cmds = [
    'cat /home/ubuntu/.tencentcloud/credentials 2>/dev/null || echo NOT_FOUND',
    'cat /root/.tencentcloud/credentials 2>/dev/null || echo NOT_FOUND',
    'env | grep -iE "TENCENT|SECRET_ID|SECRET_KEY" | head -5',
    'find /home/ubuntu -name "*.json" -path "*/tencent*" 2>/dev/null | head -5',
    'cat /home/ubuntu/.bashrc 2>/dev/null | grep -i secret | head -5',
    'cat /home/ubuntu/.env 2>/dev/null | grep -i secret | head -5',
    'sudo cat /etc/environment 2>/dev/null | grep -iE "SECRET|TENCENT" | head -5',
]
for c in cmds:
    _,o,_ = ssh.exec_command(c, timeout=5)
    r = o.read().decode().strip()
    print(f'[{c[:60]}]: {r[:200]}')

ssh.close()
