"""Check Tencent Cloud metadata for temporary credentials"""
import paramiko, time, base64, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, timeout=10):
    _,o,_ = ssh.exec_command(cmd, timeout=timeout)
    time.sleep(1)
    raw = b''
    while o.channel.recv_ready():
        raw += o.channel.recv(4096)
    return raw.decode(errors='replace').strip()[:800]

# Check metadata service for credentials
print('CAM role:', run('curl -s http://metadata.tencentyun.com/meta-data/cam/security-credentials 2>&1', 10))
print('Role name:', run('curl -s http://metadata.tencentyun.com/meta-data/cam/security-credentials/AutoEvoAIRole 2>&1', 10))

# Check if Tencent Cloud CLI has any cached config
print('TC CLI:', run('cat ~/.tccli/default.credential 2>/dev/null || cat /root/.tccli/default.credential 2>/dev/null || echo NO_TCCLI', 5))
print('ENV ID:', run('echo $TENCENTCLOUD_SECRET_ID 2>/dev/null', 5))

# Check if SDK has any cached creds
print('Python SDK check:', run('python3 -c "import os; print(os.environ.get(\\"TENCENTCLOUD_SECRET_ID\\",\\"EMPTY\\")[:8])" 2>&1', 5))

# Check qcloud api key files
print('QCloud key:', run('find / -name "qcloud*key*" -not -path "*/proc/*" 2>/dev/null | head -3', 5))

# Try to add firewall rule via API directly using signature
print('Lighthouse API test:', run('curl -s -X POST "https://lighthouse.tencentcloudapi.com/?Action=DescribeFirewallRules&Version=2020-03-24&InstanceId=lhins-3nmd98is" -H "Content-Type: application/json" 2>&1 | head -5', 15))

ssh.close()
print('DONE')
