"""
AUTO-EVO-AI — 腾讯云安全组一键配置
==================================
添加 8765 端口入站规则，让服务器可通过公网访问。

用法:
  1. 登录 https://console.cloud.tencent.com/cam/capi 获取 SecretId 和 SecretKey
  2. 运行: python fix_security_group.py
"""
import os, sys, json

# ── 引导用户输入 ──
print("=" * 60)
print("  腾讯云安全组配置 — 开放 8765 端口")
print("=" * 60)
print()
print("▶ 请登录 https://console.cloud.tencent.com/cam/capi")
print("  创建一个 API 密钥（或使用已有密钥）")
print()

secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID", "").strip()
secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY", "").strip()

if not secret_id:
    secret_id = input("SecretId: ").strip()
if not secret_key:
    secret_key = input("SecretKey: ").strip()

if not secret_id or not secret_key:
    print("❌ 需要 SecretId 和 SecretKey 才能操作")
    sys.exit(1)

# ── 导入 SDK ──
try:
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.vpc.v20170312 import vpc_client, models
except ImportError:
    print("正在安装 tencentcloud-sdk-python...")
    os.system(f"{sys.executable} -m pip install tencentcloud-sdk-python -q")
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.vpc.v20170312 import vpc_client, models
    from tencentcloud.cvm.v20170312 import cvm_client, cvm_models

# ── 实例 IP → 安全组 ──
INSTANCE_IP = "122.51.144.227"
REGION = "ap-guangzhou"

cred = credential.Credential(secret_id, secret_key)


def get_instance_security_groups():
    """查询实例关联的安全组"""
    try:
        from tencentcloud.cvm.v20170312 import cvm_client, cvm_models
        client = cvm_client.CvmClient(cred, REGION)
        req = cvm_models.DescribeInstancesRequest()
        req.Filters = [{"Name": "private-ip-address", "Values": [INSTANCE_IP]}]
        resp = client.DescribeInstances(req)
        instances = json.loads(resp.to_json_string())
        if instances.get("TotalCount", 0) == 0:
            # Try public IP
            req.Filters = [{"Name": "public-ip-address", "Values": [INSTANCE_IP]}]
            resp = client.DescribeInstances(req)
            instances = json.loads(resp.to_json_string())
        if instances.get("TotalCount", 0) == 0:
            print(f"❌ 未找到 IP {INSTANCE_IP} 对应的实例，请手动在控制台配置安全组")
            return None, None
        instance = instances["InstanceSet"][0]
        sg_ids = [sg["SecurityGroupId"] for sg in instance.get("SecurityGroupIds", [])]
        print(f"✅ 找到实例: {instance.get('InstanceName', 'unknown')} ({instance.get('InstanceId', '')})")
        print(f"  关联安全组: {sg_ids}")
        return instance, sg_ids
    except TencentCloudSDKException as e:
        print(f"⚠ 查询实例失败: {e}")
        print("  改用安全组名称搜索...")
        return None, None


def get_security_group_id(sg_ids=None):
    """获取安全组 ID"""
    vpc = vpc_client.VpcClient(cred, REGION)
    if sg_ids:
        return sg_ids[0]

    # 搜索默认安全组
    try:
        req = models.DescribeSecurityGroupsRequest()
        resp = vpc.DescribeSecurityGroups(req)
        sgs = json.loads(resp.to_json_string())
        for sg in sgs.get("SecurityGroupSet", []):
            if sg.get("SecurityGroupName", "").startswith("default"):
                print(f"  找到默认安全组: {sg['SecurityGroupId']} ({sg.get('SecurityGroupName', '')})")
                return sg["SecurityGroupId"]
        if sgs.get("SecurityGroupSet"):
            sg = sgs["SecurityGroupSet"][0]
            print(f"  使用安全组: {sg['SecurityGroupId']} ({sg.get('SecurityGroupName', '')})")
            return sg["SecurityGroupId"]
    except Exception as e:
        print(f"⚠ 查询安全组失败: {e}")
    return None


def add_port_rule(sg_id):
    """添加 8765 端口入站规则"""
    if not sg_id:
        return False
    vpc = vpc_client.VpcClient(cred, REGION)
    try:
        req = models.CreateSecurityGroupPoliciesRequest()
        req.SecurityGroupId = sg_id

        # 检查规则是否已存在
        desc_req = models.DescribeSecurityGroupPoliciesRequest()
        desc_req.SecurityGroupId = sg_id
        desc_resp = vpc.DescribeSecurityGroupPolicies(desc_req)
        policies = json.loads(desc_resp.to_json_string())
        for p in policies.get("SecurityGroupPolicySet", {}).get("Ingress", []):
            if p.get("Port") == "8765" and p.get("Protocol") == "TCP":
                print(f"✅ 8765 端口规则已存在，无需重复添加")
                return True

        policy = models.SecurityGroupPolicy()
        policy.Protocol = "TCP"
        policy.Port = "8765"
        policy.CidrBlock = "0.0.0.0/0"
        policy.Action = "ACCEPT"
        policy.PolicyDescription = "AUTO-EVO-AI API"

        req.SecurityGroupPolicySet = models.SecurityGroupPolicySet()
        req.SecurityGroupPolicySet.Ingress = [policy]

        resp = vpc.CreateSecurityGroupPolicies(req)
        result = json.loads(resp.to_json_string())
        print(f"✅ 成功添加 8765 端口入站规则到安全组 {sg_id}")
        return True
    except TencentCloudSDKException as e:
        print(f"❌ 添加规则失败: {e}")
        return False


# ── 主流程 ──
def main():
    print("\n[1/3] 查找实例关联的安全组...")
    instance, sg_ids = get_instance_security_groups()

    print("\n[2/3] 获取安全组 ID...")
    sg_id = get_security_group_id(sg_ids)
    if not sg_id and sg_ids:
        sg_id = sg_ids[0]
    if not sg_id:
        print("❌ 无法确定安全组，请手动在控制台配置")
        print("  登录 https://console.cloud.tencent.com/cvm/securitygroup")
        sys.exit(1)
    print(f"  目标安全组: {sg_id}")

    print("\n[3/3] 添加 8765 端口入站规则...")
    success = add_port_rule(sg_id)

    if success:
        print("\n" + "=" * 60)
        print("  ✅ 配置完成！")
        print("=" * 60)
        print()
        print("  现在尝试访问：")
        print(f"  → http://{INSTANCE_IP}:8765/")
        print()
        print("  仍无法访问的话，登录控制台确认规则：")
        print("  https://console.cloud.tencent.com/cvm/securitygroup")
    else:
        print("\n  ⚠ 自动配置失败，请手动操作：")
        print("  https://console.cloud.tencent.com/cvm/securitygroup")
        print("  入站规则 → 添加规则 → TCP:8765 → 0.0.0.0/0 → 允许")


if __name__ == "__main__":
    main()
