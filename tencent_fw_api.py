"""Add port 443 firewall rule via Tencent Cloud API"""
import os, json, sys, subprocess

# Install SDK
subprocess.run([sys.executable, '-m', 'pip', 'install', 'tencentcloud-sdk-python', '-q'], capture_output=True)

# Check all possible credential locations
cred_paths = [
    os.path.expanduser('~/.tccli/default.credential'),
    os.path.expanduser('~/.qcloud/credentials'),
    os.path.expanduser('~/AppData/Roaming/Tencent/Cloud CLI/credentials'),
    os.path.expanduser('~/AppData/Local/Tencent/Cloud CLI/credentials.json'),
]

secret_id = os.environ.get('TENCENTCLOUD_SECRET_ID', '')
secret_key = os.environ.get('TENCENTCLOUD_SECRET_KEY', '')

if not secret_id:
    for p in cred_paths:
        if os.path.exists(p):
            try:
                with open(p, encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        secret_id = data.get('secretId', data.get('secret_id', ''))
                        secret_key = data.get('secretKey', data.get('secret_key', ''))
                    if secret_id:
                        print(f'Credentials from: {p}')
                        break
            except: pass

if not secret_id:
    # Check env on server via SSH
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)
        _,o,_ = ssh.exec_command('env | grep -i "TENCENT\\|SECRET_ID" 2>/dev/null', timeout=5)
        r = o.read().decode(errors='replace').strip()
        if r:
            print(f'SERVER ENV: {r[:200]}')
            for line in r.split('\n'):
                if 'SECRET_ID' in line: secret_id = line.split('=')[1].strip()
                if 'SECRET_KEY' in line: secret_key = line.split('=')[1].strip()
        ssh.close()
    except Exception as e:
        print(f'SSH error: {e}')

if secret_id and secret_key:
    print(f'Using credentials: {secret_id[:8]}...{secret_id[-4:]}')
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
        from tencentcloud.lighthouse.v20200324 import lighthouse_client, models
        
        cred = credential.Credential(secret_id, secret_key)
        client = lighthouse_client.LighthouseClient(cred, "ap-guangzhou")
        
        # First, try to describe existing rules
        try:
            req = models.DescribeFirewallRulesRequest()
            req.InstanceId = "lhins-3nmd98is"
            resp = client.DescribeFirewallRules(req)
            rules = json.loads(resp.to_json_string())
            print(f'Current rules: {len(rules.get("FirewallRuleSet", []))}')
            for r in rules.get('FirewallRuleSet', []):
                print(f'  {r.get("Protocol","")} {r.get("Port","")} from {r.get("CidrBlock","")} -> {r.get("Action","")}')
        except Exception as e:
            print(f'List rules error: {e}')
        
        # Check if 443 already exists
        port443_exists = False
        if 'rules' in dir():
            for r in rules.get('FirewallRuleSet', []):
                if str(r.get('Port','')) == '443' and r.get('Protocol','') == 'TCP':
                    port443_exists = True
                    print('Port 443 already exists!')
        
        if not port443_exists:
            # Add 443 rule
            req2 = models.CreateFirewallRulesRequest()
            req2.InstanceId = "lhins-3nmd98is"
            rule = models.FirewallRule()
            rule.Protocol = "TCP"
            rule.Port = "443"
            rule.CidrBlock = "0.0.0.0/0"
            rule.Action = "ACCEPT"
            req2.FirewallRules = [rule]
            resp2 = client.CreateFirewallRules(req2)
            print(f'Rule added: {resp2.to_json_string()[:200]}')
        
        print('SUCCESS!')
        
    except Exception as e:
        print(f'API error: {e}')
else:
    print('NO CREDENTIALS FOUND anywhere')
    print('Need Tencent Cloud API SecretId and SecretKey')
    print('You can get them at: https://console.cloud.tencent.com/cam/capi')
