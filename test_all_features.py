# -*- coding: utf-8 -*-
"""AUTO-EVO-AI 全面功能实际测试"""
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8765"

def test(name, msg, expect_keyword=""):
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
        ok = data.get("success", False)
        result = data.get("result", "")
        mode = data.get("mode", "?")
        # 检查是否包含期望关键词
        if expect_keyword and ok and expect_keyword not in result:
            return False, f"缺少关键词[{expect_keyword}]", mode
        return ok, result[:120], mode
    except Exception as e:
        return False, str(e), "error"

# ===== 测试用例 =====
cases = [
    # 核心功能
    ("📊 系统状态", "系统怎么样", "模块"),
    ("🔥 GitHub热门", "GitHub今天热门项目", "热门项目"),
    ("📝 写合同", "帮我写一份隔热膜销售合同 单价45 总价170000", "合同已生成"),
    ("📊 做PPT", "帮我做一个五页的AI介绍PPT", "PPT 已生成"),
    
    # 关键词感知
    ("❓ 帮助功能", "你会什么", "查状态"),
    ("❓ 列举功能", "列举本系统可以做的事情", "我能帮你"),
    ("❓ 系统健康", "系统健康吗", "模块"),
    
    # 业务场景 - 不同行业关键词
    ("🏭 制造业", "帮我写一份进销存管理方案", "合同已生成"),
    ("🏪 零售业", "帮我写一份会员管理制度", "合同已生成"),
    ("🏦 金融业", "帮我写一份财务报表模板", "合同已生成"),
    ("🏥 医疗业", "帮我写一份病历管理制度", "合同已生成"),
    ("🎓 教育业", "帮我写一份课程管理方案", "合同已生成"),
    ("👥 人力资源", "帮我写一份员工考勤制度", "合同已生成"),
    ("💻 IT科技", "帮我写一份代码规范文档", "合同已生成"),
    ("⚖️ 法务", "帮我写一份合同管理方案", "合同已生成"),
    ("🎬 媒体", "帮我写一份内容管理方案", "合同已生成"),
    ("🏗️ 建筑业", "帮我写一份项目施工方案", "合同已生成"),
    
    # 降级规则
    ("📅 定时任务", "每天下午5点备份数据库", "定时"),
    ("🤖 团队讨论", "团队讨论安全方案", "房间"),
]

print(f"{'='*70}")
print(f"  AUTO-EVO-AI 全面功能实际测试")
print(f"{'='*70}\n")

passed = 0
failed = 0
results = []

for icon_name, msg, kw in cases:
    ok, result, mode = test(icon_name, msg, kw)
    status = "✅" if ok else "❌"
    if ok:
        passed += 1
    else:
        failed += 1
    results.append((status, icon_name, mode, result[:80]))
    print(f"  {status} {icon_name}")
    print(f"    输入: {msg[:30]}...")
    print(f"    模式: {mode} | 结果: {result[:80]}...\n")

print(f"{'='*70}")
print(f"  总评: ✅ {passed} 通过 | ❌ {failed} 失败 | {passed+failed} 项")
if passed == len(cases):
    print(f"  等级: 🏆 全功能运行正常")
elif passed / len(cases) >= 0.8:
    print(f"  等级: 👍 核心功能正常")
else:
    print(f"  等级: ⚠️ 需要修复")
print(f"{'='*70}")
