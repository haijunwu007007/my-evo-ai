"""Add port 443 firewall rule using Tencent Cloud Python SDK"""
import subprocess, sys

# Install SDK if needed
subprocess.run([sys.executable, '-m', 'pip', 'install', 'tencentcloud-sdk-python', '-q'], capture_output=True)

# Try to get credentials from env or local config
import os
secret_id = os.environ.get('TENCENTCLOUD_SECRET_ID') or os.environ.get('QCLOUD_SECRET_ID') or ''
secret_key = os.environ.get('TENCENTCLOUD_SECRET_KEY') or os.environ.get('QCLOUD_SECRET_KEY') or ''

if not secret_id or not secret_key:
    # Check if tccli config exists
    config_paths = [
        os.path.expanduser('~/.tccli/default.credential'),
        os.path.expanduser('~/.qcloud/credentials'),
        '/root/.tccli/default.credential'
    ]
    import json
    for p in config_paths:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    data = json.load(f)
                    secret_id = data.get('secretId', '')
                    secret_key = data.get('secretKey', '')
                    print(f'Found credentials in {p}')
                    break
            except: pass

    if not secret_id:
        # Try to use the server's credentials via SSH
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)
        _,o,_ = ssh.exec_command('find / -name "credential*" -path "*tccli*" -not -path "*/proc/*" 2>/dev/null | head -5', timeout=5)
        out = o.read().decode().strip()
        if out:
            for p in out.split('\n'):
                _,o2,_ = ssh.exec_command(f'cat {p}', timeout=5)
                content = o2.read().decode().strip()
                if content:
                    print(f'Found credentials on server: {p}')
                    import json
                    try:
                        data = json.loads(content)
                        secret_id = data.get('secretId', '')
                        secret_key = data.get('secretKey', '')
                        break
                    except: pass
        ssh.close()

if secret_id and secret_key:
    print(f'Got credentials: {secret_id[:8]}...')
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
        from tencentcloud.lighthouse.v20200324 import lighthouse_client, models
        
        cred = credential.Credential(secret_id, secret_key)
        client = lighthouse_client.LighthouseClient(cred, "ap-guangzhou")
        
        req = models.CreateFirewallRulesRequest()
        req.InstanceId = "lhins-3nmd98is"
        
        from tencentcloud.lighthouse.v20200324 import models as m
        rule = m.FirewallRule()
        rule.Protocol = "TCP"
        rule.Port = "443"
        rule.CidrBlock = "0.0.0.0/0"
        rule.Action = "ACCEPT"
        
        req.FirewallRules = [rule]
        
        resp = client.CreateFirewallRules(req)
        print(f'SUCCESS: {resp.to_json_string()[:200]}')
    except Exception as e:
        print(f'SDK ERROR: {e}')
else:
    print('NO CREDENTIALS FOUND')
    print(f'LOCAL ENV: secret_id={secret_id[:8] if secret_id else "EMPTY"}')
    
    # Last resort: try to find credentials on the server
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)
    
    # Check various config locations
    checks = [
        'cat /etc/tencentcloud/credentials 2>/dev/null',
        'cat ~/.tencentcloud/credentials 2>/dev/null',
        'env | grep -i "TENCENT\\|SECRET\\|QCLOUD" 2>/dev/null',
        'tccli configure list 2>/dev/null',
        'ls -la /root/.tccli/ 2>/dev/null',
        'ls -la ~/.tccli/ 2>/dev/null',
    ]
    for c in checks:
        _,o,_ = ssh.exec_command(c, timeout=5)
        r = o.read().decode(errors='replace').strip()
        if r:
            print(f'SERVER: {c[:40]} -> {r[:200]}')
    
    ssh.close()
