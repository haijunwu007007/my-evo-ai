"""Add port 443 firewall rule via Tencent Cloud API"""
import json, os, sys
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lighthouse.v20200324 import lighthouse_client, models

secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID") or ""
secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY") or ""

# Try metadata (CAM role)
if not secret_id:
    try:
        import urllib.request
        role = urllib.request.urlopen("http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/", timeout=3).read().decode().strip()
        if role:
            cred_json = urllib.request.urlopen(f"http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/{role}", timeout=3).read().decode()
            cred_data = json.loads(cred_json)
            if cred_data.get("TmpSecretId"):
                secret_id = cred_data["TmpSecretId"]
                secret_key = cred_data["TmpSecretKey"]
                print(f"CAM role {role}: OK")
    except:
        pass

if not secret_id:
    print("NO_CREDENTIALS")
    sys.exit(0)

try:
    cred = credential.Credential(secret_id, secret_key)
    client = lighthouse_client.LighthouseClient(cred, "ap-shanghai")
    
    # Check existing rules
    req = models.DescribeFirewallRulesRequest()
    req.InstanceId = "lhins-3nmd98is"
    resp = client.DescribeFirewallRules(req)
    rules = json.loads(resp.to_json_string())
    print(f"Existing rules: {len(rules.get('FirewallRuleSet', []))}")
    
    for rule in rules.get('FirewallRuleSet', []):
        if rule.get('Port') == '443':
            print("Port 443 already exists!")
            sys.exit(0)
    
    # Add port 443
    req2 = models.CreateFirewallRulesRequest()
    req2.InstanceId = "lhins-3nmd98is"
    rule = models.FirewallRule()
    rule.Protocol = "TCP"
    rule.Port = "443"
    rule.Action = "ACCEPT"
    req2.FirewallRules = [rule]
    
    resp2 = client.CreateFirewallRules(req2)
    print(f"ADDED: {resp2.to_json_string()[:200]}")
    
except TencentCloudSDKException as e:
    print(f"SDK_ERROR: {e}")
except Exception as e:
    print(f"ERROR: {e}")
