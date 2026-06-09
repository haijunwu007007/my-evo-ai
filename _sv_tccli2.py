"""Check tccli and try API"""
import paramiko, json
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Check tccli
_,o1,_ = ssh.exec_command('which tccli 2>/dev/null; pip3 list 2>/dev/null | grep tencent', timeout=8)
print('TOOLS:', o1.read().decode(errors='replace').strip()[:300])

# Try tccli describe
_,o2,_ = ssh.exec_command('tccli lighthouse DescribeFirewallRules --instanceId lhins-3nmd98is 2>&1', timeout=10)
r2 = o2.read().decode(errors='replace').strip()
print('TCCLI:', r2[:500])

ssh.close()
