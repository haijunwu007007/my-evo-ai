"""Try Python SDK for Tencent Cloud"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

script = '''
import os
from tencentcloud.common import credential
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID",""),
    os.environ.get("TENCENTCLOUD_SECRET_KEY","")
)
print("ID:", cred.secret_id[:8] if cred.secret_id else "EMPTY")
'''
cmd = f'python3 -c {json.dumps(script)}'
_,o,_ = ssh.exec_command(cmd, timeout=10)
print('SDK:', o.read().decode(errors='replace').strip()[:300])

# Also check any credentials file
_,o2,_ = ssh.exec_command('find / -name "credentials" -path "*tencent*" 2>/dev/null | head -3', timeout=5)
print('CRED_FILE:', o2.read().decode(errors='replace').strip()[:200])

ssh.close()
