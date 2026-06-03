# -*- coding: utf-8 -*-
"""深度能力测试 — 搜索/总结/屏幕/软件操作等"""
import json, urllib.request, time, sys
sys.stdout.reconfigure(encoding="utf-8")
API = "http://127.0.0.1:8765/api/v1/smart"
def t(msg, to=90):
    b = json.dumps({"message": msg, "lang": "zh-CN"}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(API, data=b, headers={"Content-Type":"application/json"}, method="POST"), timeout=to)
        d = json.loads(r.read())
        return d.get("success"), d.get("mode","?"), str(d.get("result",""))[:100]
    except Exception as e:
        return False, "error", str(e)[:100]

tests = [
    ("搜索-趋势", "帮我搜索一下2026年AI发展趋势"),
    ("搜索-新闻", "搜索今天科技热点新闻"),
    ("搜索-技术", "Python 3.14新特性"),
    ("总结-长文", "总结：AI在医疗诊断准确率95%+，金融算法交易占60%+，制造业24小时无人化，自动驾驶L2→L4，教育个性化导师，农业精准喷洒。这些带来效率提升也引发就业/隐私/伦理讨论。"),
    ("总结-数据", "总结分析：1月1000用户，2月1500，3月2200，4月3200，5月4800，6月7000，预测趋势"),
    ("屏幕-截图", "帮我截个屏幕截图"),
    ("屏幕-打开", "帮我打开计算器"),
    ("屏幕-文件", "找一下D盘最近3天的文件"),
    ("工具-GitHub", "GitHub上stars最多的Python项目"),
    ("工具-系统", "我的电脑有多少内存"),
    ("工具-脚本", "写一个bat脚本定时备份D盘"),
    ("决策-对比", "对比MacBook Pro和Windows笔记本"),
    ("决策-推荐", "推荐3个团队项目管理工具"),
    ("决策-分析", "分析新能源汽车行业2026年投资前景"),
    ("多语言-日语", "日本語で自己紹介"),
    ("多语言-法语", "Parle-moi de l'IA en français"),
    ("智能体-协作", "团队讨论如何制定项目计划"),
    ("智能体-角色", "作为资深架构师，评估微服务架构优缺点"),
]
print(f"{'='*60}\n  AUTO-EVO-AI 深度能力测试 — {len(tests)}项\n  {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")
ok=fail=0
for i,(cat,msg) in enumerate(tests,1):
    print(f"  [{i:2d}/{len(tests)}] {cat}... ", end="", flush=True)
    s,mode,re = t(msg)
    r="✅" if s else "❌"
    if s: ok+=1
    else: fail+=1
    print(f"{r} [{mode}] {re[:40]}")
    time.sleep(0.8)
print(f"\n{'='*60}\n  ✅{ok} ❌{fail} 总计{ok+fail} | {'🏆 ALL PASS' if fail==0 else '⚠️ 有失败'}\n{'='*60}")
