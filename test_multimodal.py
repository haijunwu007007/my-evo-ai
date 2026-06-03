# -*- coding: utf-8 -*-
"""AUTO-EVO-AI 多模态能力全面测试 — 文本/代码/视频/多模态"""
import json, urllib.request, time, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8765"

def test_api(msg, timeout=90):
    body = json.dumps({"message": msg, "lang": "zh-CN"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/api/v1/smart", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode("utf-8"))
        r = str(data.get("result",""))[:120]
        m = data.get("mode","?")
        return data.get("success"), m, r
    except Exception as e:
        return False, "error", str(e)[:120]

TESTS = [
    # ── 文本能力 (14项) ──
    ("📝 文本-写作", "帮我写一份创业计划书", "商业文案"),
    ("📝 文本-翻译", "翻译成英文：请确认明天下午三点的会议", "中译英"),
    ("📝 文本-翻译反", "Translate to Chinese: The meeting is postponed to next Monday", "英译中"),
    ("📝 文本-总结", "帮我总结一下：人工智能正在改变各个行业，从制造业到医疗业，从金融到教育。大模型技术使得AI能够理解自然语言、生成代码、创作内容。未来五年，AI将渗透到90%的企业工作流程中。", "文本总结"),
    ("📝 文本-改写", "请把这段话改写得更加正式：这个项目搞砸了，我们得想办法补救", "文本改写"),
    ("📝 文本-分析", "分析这句话的情感倾向：这家餐厅的服务太差了，等了半小时才上菜", "情感分析"),
    ("📝 文本-问答", "什么是量子计算？它和传统计算有什么区别？", "知识问答"),
    ("📝 文本-对比", "比较一下Python和JavaScript的优缺点", "对比分析"),
    ("📝 文本-规划", "帮我制定一个为期三个月的英语学习计划", "学习规划"),
    ("📝 文本-创意", "帮我写一首关于人工智能的七言诗", "创意写作"),
    ("📝 文本-合同", "帮我写一份技术开发合同，开发一个电商App", "合同写作"),
    ("📝 文本-方案", "帮我写一份数字化转型方案", "方案写作"),
    ("📝 文本-报告", "帮我写一份季度工作总结报告", "报告写作"),
    ("📝 文本-通知", "帮我写一份放假通知", "通知写作"),

    # ── 代码能力 (8项) ──
    ("💻 代码-生成", "帮我写一个Python函数，计算斐波那契数列", "代码生成"),
    ("💻 代码-解释", "解释一下这段代码：def decorator(func): def wrapper(*args): return func(*args); return wrapper", "代码解释"),
    ("💻 代码-优化", "如何优化这段代码的性能：for i in range(len(list)): print(list[i])", "代码优化"),
    ("💻 代码-调试", "为什么这段代码报错：x = 10; y = '5'; print(x + y)", "代码调试"),
    ("💻 代码-正则", "写一个正则表达式匹配中国大陆手机号", "正则"),
    ("💻 代码-API", "用FastAPI写一个RESTful API的示例", "API开发"),
    ("💻 代码-测试", "帮我写一个pytest单元测试示例", "测试代码"),
    ("💻 代码-数据库", "写一个SQL查询：查询每个部门的员工数量和平均薪资", "SQL"),

    # ── 视频能力 (4项) ──
    ("🎬 视频-生成", "帮我生成一个关于AI发展的视频", "视频生成"),
    ("🎬 视频-脚本", "帮我写一个产品介绍视频脚本", "视频脚本"),
    ("🎬 视频-剪辑", "如何将多个视频片段合并成一个", "视频剪辑"),
    ("🎬 视频-特效", "视频转场特效有哪些推荐", "视频特效"),

    # ── 多模态文件 (8项) ──
    ("📊 文件-PPT", "帮我做一个五页的电动汽车行业介绍PPT", "PPT生成"),
    ("📊 文件-Word", "生成一份技术方案Word文档", "Word生成"),
    ("📊 文件-Excel", "帮我创建一个Excel表格，包含产品销量数据", "Excel创建"),
    ("📊 文件-图片", "帮我描述一下如何设计一个公司Logo", "图片设计"),
    ("📊 文件-数据", "分析一下用户增长趋势：1月1000,2月1500,3月2200,4月3100", "数据分析"),
    ("📊 文件-数据2", "帮我计算一下投资回报率：投资50万，年收益8万，持有3年", "金融计算"),
    ("📊 文件-格式", "帮我用Markdown写一份README文档", "格式转换"),
    ("📊 文件-综合", "帮我做一份项目验收报告", "报告生成"),

    # ── 系统能力 (6项) ──
    ("⚙️ 系统-状态", "系统状态怎么样", "系统监控"),
    ("⚙️ 系统-GitHub", "GitHub今天热门项目", "外部数据"),
    ("⚙️ 系统-定时", "每天下午5点备份数据库", "任务调度"),
    ("⚙️ 系统-团队", "团队讨论如何提高代码质量", "团队协作"),
    ("⚙️ 系统-多语言", "How to use this system?", "多语言"),
    ("⚙️ 系统-帮助", "你会什么", "帮助"),
]

print(f"{'='*70}")
print(f"  AUTO-EVO-AI 多模态能力全面测试 — {len(TESTS)} 项")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}")

passed=failed=0; results=[]
for i,(cat,msg,desc) in enumerate(TESTS,1):
    print(f"  [{i}/{len(TESTS)}] {cat} | {desc[:20]}... ", end="", flush=True)
    ok,mode,re=test_api(msg)
    r='✅' if ok else '❌'
    if ok: passed+=1
    else: failed+=1
    results.append((r,cat,desc,mode,re[:60]))
    print(f"{r} [{mode}] {re[:40]}")
    time.sleep(0.5)

print(f"\n{'='*70}")
print(f"  📊 多模态能力测试报告")
print(f"{'='*70}")
print(f"  ✅ {passed} 通过 | ❌ {failed} 失败 | 总计 {passed+failed}")
print(f"  通过率: {passed*100//(passed+failed)}%")
print()

categories = {}
for r,cat,desc,mode,re in results:
    g = cat.split('-')[0]
    categories.setdefault(g, {"ok":0,"fail":0,"total":0})
    if r=='✅': categories[g]["ok"]+=1
    else: categories[g]["fail"]+=1
    categories[g]["total"]+=1

for g, v in categories.items():
    print(f"  {g}: ✅{v['ok']}/{v['total']} ", end="")
    if v['fail']==0: print("🏆", end="")
    print()

print(f"\n  详细结果:")
for r,cat,desc,mode,re in results:
    print(f"  {r} {cat} {desc}: mode={mode} | {re[:50]}")

print(f"\n  等级: ", end="")
r=passed/(passed+failed)*100 if (passed+failed) else 0
if r>=95: print("🏆 ALL PASS")
elif r>=80: print("👍 大部分正常")
elif r>=60: print("⚠️ 部分需要修复")
else: print("🔴 需要大修")
print(f"{'='*70}")
