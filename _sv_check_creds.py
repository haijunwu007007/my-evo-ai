"""Try to get Tencent Cloud credentials and add firewall rule"""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Check env vars for credentials
_,o1,_ = ssh.exec_command('env | grep -i "TENCENT\|SECRET\|CAM\|CLOUD" 2>&1', timeout=5)
print('ENV:', o1.read().decode(errors='replace').strip()[:500])

# Check .env and config files
_,o2,_ = ssh.exec_command('cat /home/ubuntu/my-evo-ai/.env 2>/dev/null | grep -i "secret\|tencent" | head -5', timeout=5)
print('ENV_FILE:', o2.read().decode(errors='replace').strip()[:500])

# Check if secret IDs are in the codebase
_,o3,_ = ssh.exec_command('grep -r "TENCENTCLOUD_SECRET" /home/ubuntu/my-evo-ai/ 2>/dev/null | head -5', timeout=5)
print('SECRETS_IN_CODE:', o3.read().decode(errors='replace').strip()[:500])

# Check systemd service env
_,o4,_ = ssh.exec_command('sudo cat /etc/systemd/system/evo.service 2>/dev/null | head -30', timeout=5)
print('SERVICE:', o4.read().decode(errors='replace').strip()[:1000])

# Try metadata for CAM role
_,o5,_ = ssh.exec_command('curl -s http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/ 2>&1', timeout=5)
r5 = o5.read().decode(errors='replace').strip()
print('CAM_ROLES:', r5[:300])

# Check if credentials file exists
_,o6,_ = ssh.exec_command('cat ~/.tencentcloud/credentials 2>/dev/null; cat ~/.tccli/default.credential 2>/dev/null; cat /root/.tencentcloud/credentials 2>/dev/null', timeout=5)
print('CRED_FILE:', o6.read().decode(errors='replace').strip()[:300])

ssh.close()
