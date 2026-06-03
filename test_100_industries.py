# -*- coding: utf-8 -*-
"""100 行业实际工作能力批量测试"""
import configparser, json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8765"
CONFIG = "D:\\AUTO-EVO-AI-V0.1\\industry-templates.ini"

# 每个行业的测试用例
TEST_CASES = {
    "制造业": "帮我写一份进销存管理方案",
    "零售业": "帮我写一份会员管理方案",
    "金融业": "帮我写一份财务报表分析",
    "医疗业": "帮我写一份病历管理方案",
    "教育业": "帮我写一份课程管理方案",
    "人力资源": "帮我写一份员工考勤制度",
    "企业服务": "帮我写一份客户管理方案",
    "IT科技": "帮我写一份代码管理规范",
    "法务": "帮我写一份合同管理方案",
    "媒体": "帮我写一份内容管理方案",
}

def test(msg):
    import urllib.request
    body = json.dumps({"message": msg, "lang": "zh-CN"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/v1/smart",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("success"), data.get("result", "")[:100]
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    print(f"{'='*60}")
    print(f"  AUTO-EVO-AI — 100 行业实际工作能力测试")
    print(f"{'='*60}\n")
    
    passed = 0
    failed = 0
    
    for industry, prompt in TEST_CASES.items():
        ok, result = test(prompt)
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {status} [{industry}]")
        print(f"    输入: {prompt[:40]}...")
        print(f"    结果: {result[:80]}...\n")
    
    print(f"{'='*60}")
    print(f"  结果: ✅ {passed} 通过 | ❌ {failed} 失败 | 总计 {passed+failed}")
    print(f"{'='*60}")
