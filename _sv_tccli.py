"""Try Tencent Cloud CLI or Python SDK to add firewall rule"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

cmds = [
    'which tccli 2>/dev/null; pip3 list 2>/dev/null | grep tencent',  # check tools
    'find /root -name "credentials" -not -path "*/proc/*" 2>/dev/null; find /home -name "credentials" -not -path "*/proc/*" 2>/dev/null',
]
for c in cmds:
    _,o,_ = ssh.exec_command(c, timeout=8)
    r = o.read().decode(errors='replace').strip()
    print(f'=== {c[:40]} ===')
    print(r[:500])

# Try tccli with no args to see if it's configured
_,o2,_ = ssh.exec_command('tccli lighthouse DescribeFirewallRules --instanceId lhins-3nmd98is 2>&1 | head -20', timeout=10)
r2 = o2.read().decode(errors='replace').strip()
print(f'=== tccli test ===')
print(r2[:500])

# Try Python SDK approach
_,o3,_ = ssh.exec_command('python3 -c "
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lighthouse.v20200324 import lighthouse_client, models
import os
try:
    # Try env vars first
    cred = credential.Credential(
        os.environ.get(\"TENCENTCLOUD_SECRET_ID\",\"\"),
        os.environ.get(\"TENCENTCLOUD_SECRET_KEY\",\"\")
    )
    print(f\"ID: {cred.secret_id[:8] if cred.secret_id else \"EMPTY\"}\")
except Exception as e:
    print(f\"ERROR: {e}\")
" 2>&1', timeout=10)
r3 = o3.read().decode(errors='replace').strip()
print(f'=== SDK test ===')
print(r3[:300])

ssh.close()
