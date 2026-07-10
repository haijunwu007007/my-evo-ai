"""智能体 — 核心引擎（记忆+工具+并发+规格+记忆系统）"""
import logging
logger = logging.getLogger("evo.agent_core")

import os, json, time, re, sqlite3, threading, importlib
from pathlib import Path
try:
    from api.agent_tools import exec_tool
except ImportError:
    import sys; sys.path.insert(0, '.')
    from agent_llm import call_llm
    from agent_tools import exec_tool

# ===== MemOS 记忆系统（开机即用）=====
try:
    from api.agents.agent_memos import MemOSMemory, get_memory
    _memos = get_memory()
except: _memos = None

# ===== 并发多Agent引擎（开机加载）=====
try:
    from api.agents.agent_concurrent import run_concurrent, run_team
    _CONCURRENT_READY = True
except Exception:
    _CONCURRENT_READY = False

# ===== YoYo-Evolve 自进化系统（开机加载）=====
try:
    from api.agents.yoyo_evolve import auto_evolve as yoyo_evolve, auto_scan, get_evolution_history
    _YOYO_READY = True
except Exception:
    _YOYO_READY = False

_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取Key，不硬编码
_FALLBACK = {
    "可以做那些事情": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统(说'开发xxx')\n- 🎨 画图(说'画xxx')\n- 🔍 搜索信息(说'搜索xxx')\n- 📊 做PPT(说'做一份PPT')\n- 🎮 玩游戏(说'游戏')\n- 📦 调模块(说'调xxx模块')\n- ⚡ 查状态(说'系统怎么样')",
    "你能做什么": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统\n- 🎨 画图\n- 🔍 搜索信息\n- 📊 做PPT\n- 📦 调模块\n- ⚡ 查状态",
    "你会做什么": "AUTO-EVO-AI 能做的事:\n- 💻 开发网页/系统\n- 🎨 画图\n- 🔍 搜索信息\n- 📊 做PPT\n- 📦 调模块\n- ⚡ 查状态",
    "功能": "AUTO-EVO-AI 功能列表:\n- 93个智能体工具\n- 网页开发(输入'开发xxx')\n- AI画图(多引擎自动切换)\n- 93个工具快捷按钮\n- 6个智能体团队协作\n- 165个技能自动化",
    "帮助": "AUTO-EVO-AI 使用帮助:\n1. 在设置中配置API Key后使用全部功能\n2. 点击快捷按钮或输入描述即可调用工具\n3. 支持93种不同工具和165个技能\n4. 需要更多功能？说具体需求即可",
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
    except Exception as _e:
        logger.warning(f"error: {_e}")
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
                except Exception as _e:
                    logger.warning(f"error: {_e}")
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
        except Exception as _e:
            logger.warning(f"error: {_e}")
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

    def _inline_call_llm(messages, key=""):
        """内联 call_llm — 统一走 LLMPool（自动故障转移/多Provider支持）"""
        from api.agent_llm import call_llm as _pool_call
        if not messages:
            return (None, None)
        try:
            # 提取最后一条用户消息
            user_msg = ""
            for m in reversed(messages):
                if isinstance(m, dict) and m.get("role") == "user":
                    user_msg = m.get("content", "")
                    break
            if not user_msg:
                user_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""
            if not user_msg:
                # 拼接所有消息
                parts = []
                for m in messages:
                    if isinstance(m, dict):
                        c = m.get("content", "")
                        if c:
                            parts.append(f"{m.get('role','')}: {c}")
                user_msg = "\n".join(parts)

            # 当前版本 LLMPool.chat_sync 不支持 tools 参数，只返回纯文本
            content, _ = _pool_call(messages, key=key)
            if content:
                return (content, None)
        except Exception as _e:
            logger.warning(f"error: {_e}")
        return (None, None)

    def get_tools():
        """返回工具列表（112+内置工具 + 动态生成的自定义工具）"""
        from api.agent_tools_defs import BUILTIN_TOOLS
        bt = list(BUILTIN_TOOLS)
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
                # 自进化：使用YoYo-Evolve系统每30分钟分析一次
                if int(now) % 1800 < 10:
                    try:
                        from api.agents.yoyo_evolve import auto_evolve
                        auto_evolve(BASE, _memos)
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
                # A2A: 清理过期会话
                try:
                    a2a_module = importlib.import_module("api.agent_a2a")
                    if hasattr(a2a_module, 'cleanup'):
                        a2a_module.cleanup()
                except Exception as _e:
                    logger.warning(f"error: {_e}")
                # 健康检查
                from api.infra import registry
                health = registry.get_all_health() if hasattr(registry,'get_all_health') else {}
                issues = [f"{m}: {h.get('status')}" for m, h in health.items() if h.get("status","") in ("error","timeout")]
                if issues: _remember(f"_auto_{int(now)}", f"发现 {len(issues)} 个问题", ok=False, kh="system")
            except Exception as _e:
                logger.warning(f"error: {_e}")
            _t.sleep(30)
    threading.Thread(target=auto_global_background, daemon=True).start()

    def process(msg, key="", lang="zh-CN", context=None):
        kh = key[:20] if key else "auto"
        # 自动注入默认Key
        if not key:
            key = os.environ.get("DEEPSEEK_API_KEY") or _DEFAULT_KEY
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
            except Exception as _e:
                logger.warning(f"error: {_e}")

        # ===== 开发任务：Spec-Kit + 并发 =====
        if is_dev:
            try:
                title = msg[:30]
                # 步骤1: 用 Spec-Kit 生成规格（新版call_llm直接调用）
                spec_md = ""
                try:
                    from api.agents.agent_spec import run_spec_driven
                    spec_r = run_spec_driven(msg, key, BASE, OUT, _LAST, _GENERATED_TOOLS)
                    if spec_r and isinstance(spec_r, dict) and spec_r.get("spec"):
                        spec_md = f"| 规格: {spec_r.get('spec','')} |"
                except Exception as _e:
                    logger.warning(f"error: {_e}")

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
                            except Exception as _e:
                                logger.warning(f"error: {_e}")
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
                        except Exception as _e:
                            logger.warning(f"error: {_e}")
                
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
                        except Exception as _e:
                            logger.warning(f"error: {_e}")

                        result = f"✅ **{title}**\n[📄 打开]({_LAST['url']})\n| 并发:分析+开发 | 迭代:{iterations}轮 | 模块:{', '.join(matched_modules[:3]) if matched_modules else '直接生成'} | {spec_md if spec_md else ''} |"
                        _remember(msg, result, kh=kh)
                        # MemOS积累经验
                        if _memos:
                            try: _memos.save_experience(msg[:50], f"生成成功:{_LAST['url']}")
                            except Exception as _e:
                                logger.warning(f"error: {_e}")
                        return {"success":True,"result":result,"mode":"agent"}
            except Exception as _e:
                logger.warning(f"error: {_e}")
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

【2026-06-09 新增16个集成工具】
10. 📄 markitdown_convert - 文档转Markdown：PDF/Word/Excel/PPT/图片→Markdown格式
    示例: markitdown_convert(file_path="report.pdf")
11. 🕷️ scrapegraphai_scrape - AI智能爬虫：一句话爬取网页结构化数据
    示例: scrapegraphai_scrape(url="https://example.com", prompt="提取所有产品名称和价格")
12. 💻 interpreter_execute - 电脑控制：自然语言控制电脑（读写文件/运行代码）
    示例: interpreter_execute(command="帮我分析这个CSV文件")
13. 🎨 s2c_generate - 截图转代码：上传截图直接生成前端代码
    示例: s2c_generate(image_path="screenshot.png", stack="html_tailwind")
14. 🔍 pra_review - PR代码审查：AI自动审查GitHub PR
    示例: pra_review(pr_url="https://github.com/user/repo/pull/1")
15. 🧪 qodo_testgen - 自动生成测试：给源码自动生成单元测试
    示例: qodo_testgen(source_path="app.py", framework="pytest")
16. ✏️ aider_edit - AI代码编辑：自然语言描述→自动修改代码文件
    示例: aider_edit(file_path="main.py", instruction="添加错误处理")
17. 📱 openclaw_connect - 连接OpenClaw到消息平台
    示例: openclaw_connect(platform="telegram", bot_token="xxx")
18. 🔊 tts_speak - 语音合成：文本转语音
    示例: tts_speak(text="你好，世界", voice="female")
19. 🤖 chatdev_run - ChatDev多智能体团队协作
    示例: chatdev_run(task="开发一个博客系统")
20. 🦾 openmanus_run - OpenManus通用Agent
    示例: openmanus_run(task="搜索最新AI新闻并总结")
21. 🧠 autogpt_run - AutoGPT长期自主任务
    示例: autogpt_run(goal="创建并部署一个网站", max_steps=10)
22. 📊 agenteval_benchmark - Agent性能评测
    示例: agenteval_benchmark()
23. 🛠️ swe_fix - 自动分析修复GitHub Issue
    示例: swe_fix(repo="user/repo", issue_number=42)
24. 🏗️ gptpilot_build - 从需求生成完整项目
    示例: gptpilot_build(description="一个电商网站后端")
25. 🗃️ text2sql_query - 自然语言查数据库
    示例: text2sql_query(question="哪个用户消费最多")
26. ⚡ bolt_generate - 一句话生成Web应用
    示例: bolt_generate(prompt="一个待办事项管理应用")
27. ☸️ agentk8s_deploy - 生成K8s部署清单
    示例: agentk8s_deploy(agent_name="my-agent")

【2026-06-09 第3轮 22个集成工具】
28. 🎬 openmontage_generate_script - 视频脚本生成：为视频创作生成脚本大纲
    示例: openmontage_generate_script(topic="产品介绍", style="promotion")
29. 🎞️ openmontage_search_materials - 搜索可用视频素材
    示例: openmontage_search_materials(keywords="科技,产品")
30. 📈 lida_visualize - 数据可视化：自然语言生成图表
    示例: lida_visualize(data_description="月份,销售额", goal="展示月度销售趋势")
31. 🔬 lida_explore - 探索性数据分析：自动分析CSV出多角度图表
    示例: lida_explore(data_file_path="sales.csv")
32. 📝 paddleocr_image - OCR图片文字识别：从图片提取文字
    示例: paddleocr_image(image_path="invoice.jpg")
33. 📄 paddleocr_pdf - OCR PDF识别：从PDF提取文字
    示例: paddleocr_pdf(pdf_path="contract.pdf")
34. 🔒 zen_scan - 安全漏洞扫描：扫描Web安全风险
    示例: zen_scan(target="example.com")
35. 🔐 shannon_audit - 代码安全审计：审计源码漏洞
    示例: shannon_audit(source_path="/path/to/code")
36. 🛡️ openant_scan - LLM驱动Web安全扫描
    示例: openant_scan(target="https://example.com")
37. ⚖️ legal_review_contract - 合同条款审查：AI审查法律风险
    示例: legal_review_contract(contract_text="本合同约定...")
38. 📜 legal_analyze_compliance - 合规性分析：对照法规检查合规
    示例: legal_analyze_compliance(document_text="我们收集用户数据...")
39. 👤 twenty_create_contact - CRM创建联系人
    示例: twenty_create_contact(name="张三", email="zhang@example.com")
40. 💰 twenty_create_deal - CRM创建交易
    示例: twenty_create_deal(name="大客户项目", amount=100000)
41. 🏢 frappe_hr_employee - HR员工查询
    示例: frappe_hr_employee(employee_id="EMP001")
42. 🧾 invoice_create - 创建发票
    示例: invoice_create(client="客户A", amount=5000)
43. 💳 invoice_track_expense - 记录费用
    示例: invoice_track_expense(description="办公用品", amount=200)
44. 🎫 chatwoot_create_ticket - 创建客服工单
    示例: chatwoot_create_ticket(subject="登录问题", customer_email="user@test.com")
45. 📱 postiz_create_post - 社交媒体发帖
    示例: postiz_create_post(content="新产品发布!", platforms=["twitter","discord"])
46. 📧 mautic_send_email - 营销邮件发送
    示例: mautic_send_email(subject="促销活动", content="全场5折...")
47. 📊 superset_create_chart - Superset图表创建
    示例: superset_create_chart(dataset="sales_data", chart_type="bar")
48. 📉 dataease_create_dashboard - DataEase仪表盘创建
    示例: dataease_create_dashboard(name="销售看板")
49. 📋 heyform_create_survey - 创建问卷调查
    示例: heyform_create_survey(title="客户满意度调查")
50. 📂 docetl_extract - 文档ETL提取
    示例: docetl_extract(file_paths=["/path/to/doc1.pdf","/path/to/doc2.docx"])
51. 📝 accord_create_contract - 创建法律协议/合同
    示例: accord_create_contract(template="nda")
52. 💻 claude_code_generate - Claude Code代码生成
    示例: claude_code_generate(prompt="创建一个REST API", language="python")

【2026-06-09 第4轮 21个基础设施工具】
53. 📋 plane_project - 项目管理：创建/管理项目（开源Jira替代）
    示例: plane_project(name="新项目", description="项目管理")
54. 📋 openproject_mgmt - 企业项目管理：甘特图/成本/工时管理
    示例: openproject_mgmt(name="企业项目")
55. 📅 cal_schedule - 日程调度：自动安排会议/预订
    示例: cal_schedule(title="产品评审会", duration=30)
56. 📢 novu_notify - 统一通知：Email/SMS/推送
    示例: novu_notify(channel="email", to="user@test.com", content="通知内容")
57. 🔐 keycloak_auth - 身份认证：SSO登录/用户管理
    示例: keycloak_auth(username="admin", password="***")
58. 🔍 meilisearch_search - 全文搜索：毫秒级搜索
    示例: meilisearch_search(query="搜索词")
59. 💾 minio_storage - 对象存储：S3文件管理
    示例: minio_storage(action="upload", bucket="my-bucket", file_path="file.pdf")
60. 🏗️ opentofu_apply - IaC基础设施：声明式云资源管理
    示例: opentofu_apply(config='{{"provider":"aws","resources":[]}}')
61. ⚙️ ansible_run - 配置管理：Playbook自动化运维
    示例: ansible_run(playbook="安装nginx", inventory="web-servers")
62. 📄 strapi_cms - CMS内容管理：Headless CMS
    示例: strapi_cms(content_type="article", data='{{"title":"新文章"}}')
63. 🗄️ directus_api - 数据平台：SQL数据库自动生成API
    示例: directus_api(collection="products")
64. 📊 uptime_kuma - 站点监控：80+协议监控
    示例: uptime_kuma(target="https://example.com", type="http")
65. 📊 oneuptime_monitor - 一体化可观测：监控+告警+事件
    示例: oneuptime_monitor(monitor_type="website")
66. 📊 signoz_apm - APM性能监控：追踪+指标+日志
    示例: signoz_apm(service="my-app")
67. 🛡️ wazuh_siem - 安全监控：SIEM/XDR入侵检测
    示例: wazuh_siem(action="scan")
68. 🔄 nats_mq - 消息队列：轻量级事件总线
    示例: nats_mq(subject="events", message="data")
69. 🔄 rabbitmq_broker - 消息代理：AMQP企业级消息
    示例: rabbitmq_broker(action="create_queue", queue="tasks")
70. 📦 gitea_git - Git仓库管理：自托管Git/PR/CI/CD
    示例: gitea_git(action="create_repo", repo="my-project")
71. 📚 wikijs_wiki - Wiki知识管理
    示例: wikijs_wiki(title="开发指南", content="内容")
72. 📚 bookstack_wiki - 文档系统：书架→章节→页面
    示例: bookstack_wiki(action="create_book", name="技术手册")
73. 📁 projectsend_files - 安全文件共享
    示例: projectsend_files(action="upload", file_path="/path/to/file")

【2026-06-09 第5轮 20个企业纵深自动化工具】
74. 🏢 odoo_manage - Odoo ERP：管理会计/库存/采购/销售/制造/HR
    示例: odoo_manage(module="accounting", action="list")
75. 🏭 erpclaw_manage - ERPClaw AI原生ERP：14行业46模块
    示例: erpclaw_manage(industry="manufacturing", module="inventory")
76. 🚀 coolify_deploy - Coolify PaaS：自托管部署应用和数据库
    示例: coolify_deploy(app_name="my-app", action="deploy")
77. 🖥️ rustdesk_connect - RustDesk远程桌面：远程控制电脑
    示例: rustdesk_connect(target="server-01", action="connect")
78. ✍️ docuseal_sign - DocuSeal电子签名：在线文档签署
    示例: docuseal_sign(document="contract.pdf", signers="张三,李四")
79. 🏠 homeassistant_control - 智能家居：控制IoT设备/灯光/传感器
    示例: homeassistant_control(device="living_room_light", action="turn_on")
80. 🔐 vaultwarden_manage - 密码管理：安全存储和检索密码凭证
    示例: vaultwarden_manage(action="list", site="github.com")
81. 📊 nocodb_manage - NocoDB数据表：数据库→电子表格可视化管理
    示例: nocodb_manage(table="customers", action="list")
82. 🛠️ appsmith_build - Appsmith低代码：拖拽式构建内部管理工具
    示例: appsmith_build(app_name="CRM", action="create")
83. 🔄 airbyte_sync - Airbyte ETL：数据采集/清洗/同步管道
    示例: airbyte_sync(source="postgres", destination="snowflake", action="sync")
84. 📈 mlflow_track - MLflow MLOps：AI模型训练/部署/追踪
    示例: mlflow_track(experiment="bert-finetune", action="log")
85. 👁️ langfuse_observe - Langfuse LLM可观测：Prompt管理/评估/追踪
    示例: langfuse_observe(action="trace", project="chatbot")
86. 🧪 hoppscotch_test - Hoppscotch API测试：API调试/Mock/回归
    示例: hoppscotch_test(endpoint="/api/users", method="GET")
87. 📋 grist_analyze - Grist电子表格：关系型数据分析/Python公式
    示例: grist_analyze(table="sales", action="analyze")
88. 📰 freshrss_read - FreshRSS聚合：RSS订阅/信息采集/资讯监控
    示例: freshrss_read(action="read", feed="tech_news")
89. 📧 listmonk_send - Listmonk邮件：邮件列表/Newsletter/营销
    示例: listmonk_send(action="send", list_id="1")
90. 🗺️ mermaid_chart - Mermaid图表：文本→流程图/架构图/时序图
    示例: mermaid_chart(chart_type="flow", description="用户登录流程")
91. 🏗️ nocobase_build - NocoBase低代码：AI+低代码构建业务应用
    示例: nocobase_build(app_name="订单管理", action="create")
92. 🎤 scriberr_transcribe - 音频转录：AI将音频/会议转录为文字
    示例: scriberr_transcribe(audio_path="meeting.mp3", action="transcribe")
93. 🧪 keploy_test - Keploy AI测试：自动生成API回归测试
    示例: keploy_test(action="record", endpoint="/api/orders")

【2026-06-11 新增 并发多Agent + 自进化】
94. 🧵 concurrent_run - 并发多Agent：多Agent并行协作（分析师+开发者+审查者）
    示例: concurrent_run(task_name="开发记账应用", details="需用户登录和账单管理", mode="team")
95. 🧬 yoyo_scan - 自进化扫描：自动检测代码库问题并生成优化建议
    示例: yoyo_scan(scope="auto")
96. 📊 yoyo_history - 查看自进化历史记录
    示例: yoyo_history(limit=10)

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
        # 检查精确匹配的fallback（仅在无key且匹配特定问题时）
        if not key:
            for q, a in _FALLBACK.items():
                if q in msg: return {"success":True,"result":a,"mode":"direct"}
        messages = []
        if context:
            for c in context[-6:]:
                if isinstance(c, dict): messages.append(c)
        messages.append({"role":"system","content":SP})
        messages.append({"role":"user","content":msg})

        tool_rounds = 0
        for rd in range(8):
            # 直接内联 call_llm 逻辑，避免模块缓存问题
            content, tc = _inline_call_llm(messages, key)
            if content is None and tc is None: continue
            # 纯文本响应（无工具调用），直接返回
            if content:
                _remember(msg, content, kh=kh)
                return {"success": True, "result": content, "mode": "llm"}
            if tc:
                tool_rounds += 1
                # 执行工具
                tool_results = []
                for t in tc:
                    func = t.get("function",{}); nm = func.get("name",""); a = {}
                    try: a = json.loads(func.get("arguments","{}"))
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
                    result = exec_tool(nm, a, BASE, OUT, _LAST, _GENERATED_TOOLS)
                    tool_results.append((t, result))
                # 最多3轮工具调用，之后强制LLM总结
                if tool_rounds >= 3:
                    # 先添加所有工具结果，再强制总结
                    for t, result in tool_results:
                        messages.append({"role":"assistant","content":None,"tool_calls":[t]})
                        messages.append({"role":"tool","tool_call_id":t.get("id",""),"content":json.dumps(result,ensure_ascii=False)})
                    messages.append({"role":"user","content":"请基于已有结果直接回答用户问题，不要再调用任何工具。用中文简洁回答。"})
                    content2, tc2 = call_llm(messages, [], key)
                    if content2:
                        _remember(msg, content2, kh=kh)
                        return {"success":True,"result":content2,"mode":"llm"}
                    break
                for t, result in tool_results:
                    messages.append({"role":"assistant","content":None,"tool_calls":[t]})
                    messages.append({"role":"tool","tool_call_id":t.get("id",""),"content":json.dumps(result,ensure_ascii=False)})
                continue
            if _LAST.get("time",0) > time.time()-120 and _LAST.get("url",""):
                final = f"✅ **{_LAST.get('name','')}**\n[📄 打开]({_LAST['url']})"
                if _memos:
                    try: _memos.save_experience(msg[:50], f"工具执行成功:{_LAST.get('url','')}")
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
                _remember(msg, final, kh=kh)
                return {"success":True,"result":final,"mode":"agent"}
            if content and '/output/' in content:
                _remember(msg, content, kh=kh)
                return {"success":True,"result":content,"mode":"bot"}
            # LLM纯文本响应（非文件生成），直接返回实际内容
            if content:
                _remember(msg, content, kh=kh)
                return {"success":True,"result":content,"mode":"llm"}
            return {"success":True,"result":_FALLBACK.get("可以做那些事情","AUTO-EVO-AI已就绪"),"mode":"direct"}
        # 全部尝试失败，检查是否有可用的 API Key
        _any_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY","ZHIPU_API_KEY","DEEPSEEK_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY"))
        if not _any_key:
            return {"success":True,"result":"⚠️ **LLM API Key 未配置**，系统处于离线模式。请配置 API Key 后重启服务。","mode":"no_key"}
        return {"success":True,"result":"请求超时，请检查 LLM API Key 是否有效或网络是否可达","mode":"timeout"}
    return process
