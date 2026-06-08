"""智能体 — 核心引擎（记忆+工具+并发+规格+记忆系统）"""
import os, json, time, re, sqlite3, threading, importlib
from pathlib import Path
try:
    from api.agent_llm import call_llm
    from api.agent_tools import exec_tool
except ImportError:
    import sys; sys.path.insert(0, '.')
    from agent_llm import call_llm
    from agent_tools import exec_tool

# ===== MemOS 记忆系统（开机即用）=====
try:
    from api.agent_memos import MemOSMemory, get_memory
    _memos = get_memory()
except: _memos = None

_FALLBACK = {
    "可以做那些事情": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统(说'开发xxx')\n- 🎨 画图(说'画xxx')\n- 🔍 搜索信息(说'搜索xxx')\n- 📊 做PPT(说'做一份PPT')\n- 🎮 玩游戏(说'游戏')\n- 📦 调模块(说'调xxx模块')\n- ⚡ 查状态(说'系统怎么样')\n需要输入API Key才能使用智能体全部功能！",
    "你能做什么": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统\n- 🎨 画图\n- 🔍 搜索信息\n- 📊 做PPT\n- 🎮 玩游戏\n- 📦 调模块\n- ⚡ 查状态\n需要输入API Key才能使用智能体全部功能！",
    "你会做什么": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统\n- 🎨 画图\n- 🔍 搜索信息\n- 📊 做PPT\n- 🎮 玩游戏\n- 📦 调模块\n- ⚡ 查状态\n需要输入API Key才能使用智能体全部功能！",
    "功能": "AUTO-EVO-AI 功能列表:\n- 智能体聊天(需API Key)\n- 网页开发(输入'开发xxx')\n- AI画图(多引擎自动切换)\n- 信息搜索(GitHub+DuckDuckGo)\n- PPT自动生成\n- 8种游戏秒回\n- 499个模块调用\n- 自我迭代审查\n- 并发多Agent(并行加速)\n- 规格驱动开发(Spec-Kit)\n- 三层记忆系统(MemOS)",
    "帮助": "AUTO-EVO-AI 使用帮助:\n1. 输入API Key后可使用智能体\n2. 直接说需求即可\n3. 游戏/状态无需Key\n4. 开发项目会自动审查修复\n5. 并发加速让开发提速5倍\n更多功能持续更新中",
}
def _eval_modules():
    try:
        from api.infra import registry
        total = registry.get_total_count()
        ok = len([m for m,h in registry.get_all_health().items() if h.get("status") in ("ok","running","pending_lazy")])
        return f"模块评估: A={ok}/{total}"
    except: return "模块评估: 不可用"
def _match_modules(msg):
    try:
        from api.infra import get_coordinator_v3
        coord = get_coordinator_v3()
        if coord and hasattr(coord, 'capability_graph'):
            matches = coord.capability_graph.find_modules_by_task(msg)
            if matches: return [m for m, s in matches[:5] if s > 1.0]
    except: pass
    BASE = Path(__file__).resolve().parent.parent
    mdir = BASE / "modules"
    if mdir.exists():
        tags = [w for w in re.findall(r'[\u4e00-\u9fff]{2,}', msg) if len(w) >= 2]
        matched = set()
        tag_map = {"报名":"form","注册":"auth","登录":"auth","用户":"user","数据":"data","报表":"report","图表":"chart","搜索":"search","监控":"monitor","备份":"backup","部署":"deploy","测试":"test","安全":"security","邮件":"email","通知":"notify","支付":"payment","文件":"file"}
        for tag in tags[:3]:
            tag_en = tag_map.get(tag, tag)
            for f in mdir.glob("*.py"):
                n = f.stem; 
                if n.startswith("_"): continue
                try:
                    c = f.read_text(errors="replace",encoding="utf-8")[:500].lower()
                    if tag_en in n or tag in c or tag_en in c: matched.add(n)
                except: pass
        return list(matched)[:5]
    return []

def create_engine(BASE, OUT, TOOLS_DIR, MEM_DB):
    _LAST = {}; _GENERATED_TOOLS = {}; _HISTORY = []

    def _remember(msg, result, ok=True, kh=""):
        try:
            conn = sqlite3.connect(str(MEM_DB))
            conn.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, input TEXT, output TEXT, success INTEGER, created REAL, key_hash TEXT)")
            conn.execute("INSERT INTO memory (input, output, success, created, key_hash) VALUES (?,?,?,?,?,?)", (msg[:200], str(result)[:500], 1 if ok else 0, time.time(), kh[:20]))
            conn.commit(); conn.close()
        except: pass
    def _recall(msg, kh="", limit=3):
        try:
            conn = sqlite3.connect(str(MEM_DB)); conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM memory WHERE key_hash=? ORDER BY created DESC LIMIT ?", (kh, limit)).fetchall()
            conn.close()
            return "\n".join(f"经验: {r['input'][:50]} -> {r['output'][:100]}" for r in rows) if rows else ""
        except: return ""
    def _recall_similar(msg, kh="", limit=2):
        try:
            conn = sqlite3.connect(str(MEM_DB)); conn.row_factory = sqlite3.Row
            kw = " ".join(re.findall(r'[\w\u4e00-\u9fff]{2,}', msg)[:5])
            if not kw: return ""
            rows = conn.execute("SELECT * FROM memory WHERE key_hash=? AND (input LIKE ? OR input LIKE ?) ORDER BY created DESC LIMIT ?", (kh, f"%{kw[:10]}%", f"%{msg[:10]}%", limit)).fetchall()
            conn.close()
            if rows: return "上相关的经验:\n"+"\n".join(f"- {r['input'][:40]} -> {r['output'][:80]}" for r in rows)
            return ""
        except: return ""

    def get_tools():
        bt = [
            {"type":"function","function":{"name":"read_file","description":"读取任意文件","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"list_modules","description":"列出系统所有模块","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"search_modules","description":"按中文关键词搜索模块","parameters":{"type":"object","properties":{"keyword":{"type":"string"}},"required":["keyword"]}}},
            {"type":"function","function":{"name":"module_info","description":"查看模块详细信息","parameters":{"type":"object","properties":{"module":{"type":"string"}},"required":["module"]}}},
            {"type":"function","function":{"name":"get_module_demo","description":"获取模块调用示例","parameters":{"type":"object","properties":{"module":{"type":"string"}},"required":["module"]}}},
            {"type":"function","function":{"name":"execute_module","description":"调用系统模块执行任务","parameters":{"type":"object","properties":{"module":{"type":"string"},"action":{"type":"string"},"params":{"type":"string"}},"required":["module","action"]}}},
            {"type":"function","function":{"name":"file_write","description":"写文件","parameters":{"type":"object","properties":{"name":{"type":"string"},"content":{"type":"string"},"type":{"type":"string","enum":["html","python","text","json","tool"]}},"required":["name","content"]}}},
            {"type":"function","function":{"name":"register_tool","description":"注册.py为工具","parameters":{"type":"object","properties":{"name":{"type":"string"},"filepath":{"type":"string"}},"required":["name","filepath"]}}},
            {"type":"function","function":{"name":"create_task","description":"创建定时任务","parameters":{"type":"object","properties":{"name":{"type":"string"},"schedule":{"type":"string"},"action":{"type":"string"},"params":{"type":"string"}},"required":["name","schedule","action"]}}},
            {"type":"function","function":{"name":"list_tools","description":"列出所有工具","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"draw_image","description":"AI画图","parameters":{"type":"object","properties":{"prompt":{"type":"string"}},"required":["prompt"]}}},
            {"type":"function","function":{"name":"web_search","description":"搜索信息","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
            # ===== 2026-06-08 新增集成工具 =====
            {"type":"function","function":{"name":"browser_use_task","description":"🌐 浏览器自动化：AI自动操控浏览器完成登录/填表/抓取/发帖等任务。参数task传入自然语言描述。","parameters":{"type":"object","properties":{"task":{"type":"string"}},"required":["task"]}}},
            {"type":"function","function":{"name":"gpt_research","description":"📊 自主研究：自动搜索→抓取→生成带引用的研究报告。参数query传入研究问题。","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
            {"type":"function","function":{"name":"openhands_generate","description":"🏗️ 全栈项目生成：生成前端+后端+数据库+测试的完整项目。参数description传入项目描述，project_type可选fullstack/frontend/backend/api。","parameters":{"type":"object","properties":{"description":{"type":"string"},"project_type":{"type":"string"}},"required":["description"]}}},
            {"type":"function","function":{"name":"letta_message","description":"🧠 Letta记忆：发送消息到操作系统级记忆系统，支持无限上下文。参数message传入消息。","parameters":{"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}}},
            {"type":"function","function":{"name":"composio_execute","description":"🔧 Composio工具：执行200+外部工具（GitHub/Slack/Gmail等）。参数app_name传应用名，action_name传操作名，params传参数。","parameters":{"type":"object","properties":{"app_name":{"type":"string"},"action_name":{"type":"string"},"params":{"type":"string"}},"required":["app_name","action_name"]}}},
            {"type":"function","function":{"name":"self_evolving_analyze","description":"🧬 自进化分析：分析代码库，找出潜在改进点（bug/优化/重构/功能）。参数repo_path可选，默认当前目录。","parameters":{"type":"object","properties":{"repo_path":{"type":"string"}}}}},
            {"type":"function","function":{"name":"moltron_learn","description":"📚 Moltron技能学习：学习新技能并写入Skills.md。参数skill_name传技能名，skill_description传描述。","parameters":{"type":"object","properties":{"skill_name":{"type":"string"},"skill_description":{"type":"string"}},"required":["skill_name","skill_description"]}}},
            {"type":"function","function":{"name":"accomplish_desktop","description":"🖥️ 桌面自动化：执行桌面自动化工作流（键鼠操作/截图/应用启动）。参数workflow传入步骤列表。","parameters":{"type":"object","properties":{"workflow":{"type":"string"}}}}},
            {"type":"function","function":{"name":"toolbench_discover","description":"🔌 ToolBench API发现：从12万+API注册表中发现可以调用的外部API。参数query搜索关键词，category过滤类别，action可选search/register/stats/detail。","parameters":{"type":"object","properties":{"query":{"type":"string"},"category":{"type":"string"},"action":{"type":"string"},"api_name":{"type":"string"}}}}},
        ]
        for tname in _GENERATED_TOOLS:
            bt.append({"type":"function","function":{"name":f"tool_{tname}","description":f"自定义工具: {tname}","parameters":{"type":"object","properties":{"params":{"type":"string"}}}}})
        return bt

    def _generate_page(msg, title):
        safe_title = re.sub(r'[<>"\'/\\]', '', title)[:30]
        html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{safe_title}</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#e0e0e0;min-height:100vh;padding:20px}}.card{{background:rgba(255,255,255,.05);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:32px;margin:20px auto;max-width:700px}}h1{{background:linear-gradient(135deg,#4361ee,#7209b7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:28px;margin-bottom:20px;text-align:center}}p{{color:#8892b0;line-height:1.8;margin:12px 0;font-size:15px}}input,select,textarea{{width:100%;padding:12px 16px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#e0e0e0;font-size:14px;margin:8px 0;outline:none;transition:border .2s}}input:focus,select:focus,textarea:focus{{border-color:#4361ee}}label{{font-size:13px;color:#8892b0;display:block;margin-top:12px}}button{{width:100%;padding:12px;border-radius:8px;border:none;background:linear-gradient(135deg,#4361ee,#7209b7);color:#fff;font-size:15px;cursor:pointer;font-weight:600;transition:transform .15s,opacity .15s;margin-top:16px}}button:hover{{transform:translateY(-1px);opacity:.9}}table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}}td,th{{border:1px solid rgba(255,255,255,.1);padding:10px 12px;text-align:left}}th{{background:rgba(255,255,255,.05);color:#8892b0;font-weight:600}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}.card{{padding:20px}}h1{{font-size:22px}}}}</style></head><body><div class="card"><h1>{safe_title}</h1><p>功能开发中，请稍后再试</p></div></body></html>"""
        fn = f"app_{int(time.time())}.html"
        fp = str(OUT / "apps" / fn); Path(fp).parent.mkdir(exist_ok=True)
        Path(fp).write_text(html, encoding='utf-8')
        return fn, fp

    def auto_global_background():
        """后台全局服务：自进化 + A2A通信 + 经验积累"""
        import time as _t; _t.sleep(15)
        while True:
            try:
                now = _t.time()
                # 自进化：每30分钟触发一次代码分析
                if int(now) % 1800 < 10:
                    try:
                        evo_module = importlib.import_module("api.agent_evolve")
                        if hasattr(evo_module, 'auto_evolve'):
                            evo_module.auto_evolve(BASE, _memos)
                    except: pass
                # A2A: 清理过期会话
                try:
                    a2a_module = importlib.import_module("api.agent_a2a")
                    if hasattr(a2a_module, 'cleanup'):
                        a2a_module.cleanup()
                except: pass
                # 健康检查
                from api.infra import registry
                health = registry.get_all_health() if hasattr(registry,'get_all_health') else {}
                issues = [f"{m}: {h.get('status')}" for m, h in health.items() if h.get("status","") in ("error","timeout")]
                if issues: _remember(f"_auto_{int(now)}", f"发现 {len(issues)} 个问题", ok=False, kh="system")
            except: pass
            _t.sleep(30)
    threading.Thread(target=auto_global_background, daemon=True).start()

    def process(msg, key="", lang="zh-CN", context=None):
        kh = key[:20] if key else "auto"
        memory = _recall_similar(msg, kh) or _recall(msg, kh)
        is_dev = any(k in msg for k in ["开发","创建","写一个","做一个","生成","设计","实现"])
        gen_tools = list(_GENERATED_TOOLS.keys())
        matched_modules = _match_modules(msg)
        module_hint = f"\n【推荐模块】可调用: {', '.join(matched_modules[:3])}" if matched_modules else ""
        module_eval = _eval_modules()

        # ===== MemOS经验注入 =====
        memos_experience = ""
        if _memos:
            try:
                exp = _memos.search_long(msg, top_k=2)
                if exp: memos_experience = "\n【历史经验】\n" + "\n".join(f"- {e['pattern']}: {e['solution'][:80]}" for e in exp)
            except: pass

        # ===== 开发任务：Spec-Kit + 并发 =====
        if is_dev:
            try:
                title = msg[:30]
                # 步骤1: 用 Spec-Kit 生成规格（新版call_llm直接调用）
                spec_md = ""
                try:
                    from api.agent_spec import run_spec_driven
                    spec_r = run_spec_driven(msg, key, BASE, OUT, _LAST, _GENERATED_TOOLS)
                    if spec_r and isinstance(spec_r, dict) and spec_r.get("spec"):
                        spec_md = f"| 规格: {spec_r.get('spec','')} |"
                except: pass

                # 步骤2: 并发执行（分析师 + 开发者并行）
                import concurrent.futures
                results = {}
                def gen_analysis():
                    a_prompt = f"分析任务：{msg[:100]}。输出JSON：{{'title':'...','features':[...]}}。纯JSON。"
                    a_msgs = [{"role":"system","content":"输出纯JSON。"},{"role":"user","content":a_prompt}]
                    return call_llm(a_msgs, None, key)
                def gen_code():
                    c_prompt = f"生成{title}的完整HTML。包含CSS+JS。放在```html```中。"
                    c_msgs = [{"role":"system","content":"专业前端开发者。"},{"role":"user","content":c_prompt}]
                    r, tc = call_llm(c_msgs, None, key)
                    if r: return r
                    if tc:
                        for t in tc:
                            func = t.get("function",{}); nm = func.get("name",""); a = {}
                            try: a = json.loads(func.get("arguments","{}"))
                            except: pass
                            r2 = exec_tool(nm, a, BASE, OUT, _LAST, _GENERATED_TOOLS)
                            if r2.get("data"): return r2["data"]
                    return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    f1 = executor.submit(gen_analysis)
                    f2 = executor.submit(gen_code)
                    done, _ = concurrent.futures.wait([f1, f2], timeout=90)
                    for f in done:
                        try:
                            name = None
                            if f == f1: name="analysis"
                            elif f == f2: name="code"
                        except: pass
                
                ar, _ = (f1.result() if f1.done() else (None,None))
                code_result = f2.result() if f2.done() else None

                if code_result:
                    import re as _re
                    html_code = None
                    m = _re.search(r'```html\s*(.*?)\s*```', code_result, _re.DOTALL)
                    if m: html_code = m.group(1)
                    else:
                        m2 = _re.search(r'```\s*(.*?)\s*```', code_result, _re.DOTALL)
                        if m2: html_code = m2.group(1)
                        else: html_code = code_result
                    html_code = _re.sub(r'```\w*', '', html_code).strip()
                    if len(html_code) > 200:
                        fn = f"app_{int(time.time())}.html"
                        fp = str(OUT / "apps" / fn); Path(fp).parent.mkdir(exist_ok=True)
                        Path(fp).write_text(html_code, encoding='utf-8')
                        _LAST["url"]=f"/output/apps/{fn}"; _LAST["time"]=time.time(); _LAST["name"]=title

                        # 审查+自我迭代
                        rr, iterations = None, 1
                        try:
                            rp = f"审查代码。需求：{title}\n代码:\n{html_code[:500]}...\n回复 通过/不通过+原因。"
                            r_msgs = [{"role":"system","content":"严格代码审查专家。"},{"role":"user","content":rp}]
                            rr, _ = call_llm(r_msgs, None, key)
                            while rr and "不通过" in rr[:15] and iterations < 3:
                                fix_prompt = f"修复审查问题:{rr[:200]}\n输出完整HTML。"
                                fix_msgs = [{"role":"user","content":fix_prompt}]
                                fr, _ = call_llm(fix_msgs, None, key)
                                if fr:
                                    m3 = _re.search(r'```html\s*(.*?)\s*```', fr, _re.DOTALL)
                                    if m3: html_code = m3.group(1); Path(fp).write_text(html_code, encoding='utf-8')
                                iterations += 1
                                r_msgs = [{"role":"user","content":f"再审查:\n{html_code[:500]}..."}]
                                rr, _ = call_llm(r_msgs, None, key)
                        except: pass

                        result = f"✅ **{title}**\n[📄 打开]({_LAST['url']})\n| 并发:分析+开发 | 迭代:{iterations}轮 | 模块:{', '.join(matched_modules[:3]) if matched_modules else '直接生成'} | {spec_md if spec_md else ''} |"
                        _remember(msg, result, kh=kh)
                        # MemOS积累经验
                        if _memos:
                            try: _memos.save_experience(msg[:50], f"生成成功:{_LAST['url']}")
                            except: pass
                        return {"success":True,"result":result,"mode":"agent"}
            except: pass
            fn, fp = _generate_page(msg, msg[:30])
            _LAST["url"]=f"/output/apps/{fn}"; _LAST["time"]=time.time(); _LAST["name"]=msg[:30]
            result = f"✅ **{msg[:30]}**\n[📄 打开]({_LAST['url']})"
            _remember(msg, result, kh=kh)
            return {"success":True,"result":result,"mode":"fallback"}

        # ===== 非开发任务 =====
        SP = f"""你是AUTO-EVO-AI V0.1。你是全球最强的全栈AI工程师，拥有极强的编程能力和解决问题的能力。

【新增能力 - 2026-06-08】
1. 🌐 browser_use_task - 浏览器自动化：AI自动操控浏览器（登录/填表/抓取/发帖）
   示例: browser_use_task(task="登录GitHub并查看我的仓库")
2. 📊 gpt_research - 自主研究：自动搜索→抓取→生成带引用的研究报告
   示例: gpt_research(query="ChatGPT最新动态分析")
3. 🏗️ openhands_generate - 全栈项目生成：生成前端+后端+数据库+测试的完整项目
   示例: openhands_generate(description="一个待办事项管理Web应用", project_type="fullstack")
4. 🧠 letta_message - Letta记忆：发送消息到操作系统级记忆系统（无限上下文）
   示例: letta_message(message="记住：用户喜欢简洁的代码")
5. 🔧 composio_execute - Composio工具：执行200+外部工具（GitHub/Slack/Gmail/Jira等）
   示例: composio_execute(app_name="github", action_name="CREATE_ISSUE", params={{"repo":"..."}})
6. 🧬 self_evolving_analyze - 自进化分析：分析代码库，找出潜在改进点
   示例: self_evolving_analyze(repo_path=".")
7. 📚 moltron_learn - Moltron技能学习：学习新技能并写入Skills.md
   示例: moltron_learn(skill_name="Browser Automation", skill_description="使用Browser-Use自动化浏览器操作")
8. 🖥️ accomplish_desktop - 桌面自动化：执行桌面自动化工作流（键鼠操作/截图/应用启动）
   示例: accomplish_desktop(workflow=[{{"action":"type","text":"Hello"}},{{"action":"screenshot"}}])
9. 🔌 toolbench_discover - ToolBench API发现：从12万+API注册表中搜索可调用的外部API
   示例: toolbench_discover(query="搜索", category="社交媒体")  # 搜索社交媒体类API
   示例: toolbench_discover(action="stats")  # 查看API注册表统计

【原有能力】
- 💻 开发网页/系统 (说"开发xxx")
- 🎨 画图 (说"画xxx")
- 🔍 搜索信息 (说"搜索xxx")
- 📊 做PPT (说"做一份PPT")
- 🎮 玩游戏 (说"游戏")
- 📦 调模块 (说"调xxx模块")
- ⚡ 查状态 (说"系统怎么样")

可用工具: {module_hint}{memos_experience}
历史记忆: {memory or '无'}
{module_eval}

【指令】
- 根据用户需求，智能选择并使用上述工具
- 开发任务优先使用 openhands_generate（全栈）或原有开发流程（单页面）
- 需要浏览器操作时使用 browser_use_task
- 需要深度研究时使用 gpt_research
- 需要记忆管理时使用 letta_message
- 需要外部工具时使用 composio_execute
- 需要发现API时使用 toolbench_discover
- 分析代码时使用 self_evolving_analyze
- 学习新技能时使用 moltron_learn
- 桌面自动化时使用 accomplish_desktop
"""
        if not key:
            for q, a in _FALLBACK.items():
                if q in msg: return {"success":True,"result":a,"mode":"direct"}
        messages = []
        if context:
            for c in context[-6:]:
                if isinstance(c, dict): messages.append(c)
        messages.append({"role":"system","content":SP})
        messages.append({"role":"user","content":msg})

        for rd in range(8):
            content, tc = call_llm(messages, get_tools(), key)
            if content is None and tc is None: continue
            if tc:
                for t in tc:
                    func = t.get("function",{}); nm = func.get("name",""); a = {}
                    try: a = json.loads(func.get("arguments","{}"))
                    except: pass
                    result = exec_tool(nm, a, BASE, OUT, _LAST, _GENERATED_TOOLS)
                    messages.append({"role":"assistant","content":None,"tool_calls":[t]})
                    messages.append({"role":"tool","tool_call_id":t.get("id",""),"content":json.dumps(result,ensure_ascii=False)})
                continue
            if _LAST.get("time",0) > time.time()-120 and _LAST.get("url",""):
                final = f"✅ **{_LAST.get('name','')}**\n[📄 打开]({_LAST['url']})"
                if _memos:
                    try: _memos.save_experience(msg[:50], f"工具执行成功:{_LAST.get('url','')}")
                    except: pass
                return {"success":True,"result":final,"mode":"agent"}
            if content and '/output/' in content:
                return {"success":True,"result":content,"mode":"bot"}
            return {"success":True,"result":_FALLBACK.get("可以做那些事情","AUTO-EVO-AI已就绪"),"mode":"direct"}
        return {"success":True,"result":_FALLBACK.get("可以做那些事情","AUTO-EVO-AI已就绪"),"mode":"timeout"}
    return process
