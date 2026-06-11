"""智能体 — 工具执行（画图/文件/搜索/模块）"""
import os, json, time, urllib.request, httpx, re
from pathlib import Path

def exec_tool(name, args, BASE, OUT, _LAST, _GENERATED_TOOLS):
    """执行内置工具，返回 {"ok":bool, "data":str}"""
    # 保证BASE/OUT是Path对象
    if isinstance(BASE, str): BASE = Path(BASE)
    if isinstance(OUT, str): OUT = Path(OUT)
    try:
        if name == "read_file":
            fp = str(BASE / args.get("path",""))
            return {"ok":True,"data":Path(fp).read_text(encoding='utf-8',errors='replace')[:3000]}
        if name == "list_modules":
            mdir = BASE / "modules"
            if mdir.exists():
                cats = {}
                for f in sorted(mdir.iterdir()):
                    if f.is_dir(): cats[f.name] = len(list(f.glob("*.py")))
                    elif f.suffix==".py": cats["_root"] = cats.get("_root",0)+1
                summary = f"系统共有{sum(cats.values())}个模块\n" + "\n".join(f"- {k}: {v}个" for k,v in sorted(cats.items()))
                return {"ok":True,"data":summary}
            return {"ok":True,"data":"系统模块目录不存在"}
        if name == "search_modules":
            kw = args.get("keyword","").lower()
            mdir = BASE / "modules"
            if not mdir.exists(): return {"ok":True,"data":"无模块"}
            results = []
            for f in mdir.rglob("*.py"):
                if kw in f.stem.lower() or kw in str(f.parent.name).lower():
                    size = f.stat().st_size
                    has_exec = "execute" in f.read_text(encoding='utf-8',errors='replace')
                    quality = "🟢真实" if size > 2048 and has_exec else "🟡桩"
                    doc = f.read_text(encoding='utf-8',errors='replace')[:200]
                    doc_line = [l.strip() for l in doc.split("\n") if l.strip().startswith(('"""',"'''","#"))][:3]
                    desc = "; ".join(doc_line)[:100] if doc_line else "无描述"
                    results.append(f"{quality} {f.relative_to(mdir)} ({size//1024}KB): {desc}")
            if not results: return {"ok":True,"data":f"未找到含'{kw}'的模块"}
            return {"ok":True,"data":"\n".join(results[:10])}
        if name == "module_info":
            mod = args.get("module","")
            mdir = BASE / "modules"
            for f in mdir.rglob("*.py"):
                if mod in f.stem or mod in str(f.relative_to(mdir)):
                    content = f.read_text(encoding='utf-8',errors='replace')[:1500]
                    funcs = re.findall(r'def (\w+)\(', content)
                    classes = re.findall(r'class (\w+)', content)
                    return {"ok":True,"data":f"{f.relative_to(mdir)}\n类: {', '.join(classes[:10]) if classes else '无'}\n方法: {', '.join(funcs[:20]) if funcs else '无'}\n\n{content[:800]}"}
            return {"ok":True,"data":"未找到模块"}
        if name == "execute_module":
            from api.infra import registry, _execute_module_internal
            loop = __import__('asyncio').new_event_loop()
            r = loop.run_until_complete(_execute_module_internal(args.get("module",""), args.get("action","status"), json.loads(args.get("params","{}"))))
            loop.close()
            if isinstance(r, dict):
                suc = r.get("success", r.get("result",{}).get("success", True))
                body = str(r.get("result", r.get("data", r.get("error", r))))[:2000]
                return {"ok":bool(suc),"data":f"[{'成功' if suc else '失败'}] {body}"}
            return {"ok":True,"data":str(r)[:2000]}
        if name == "file_write":
            n=args.get("name","文件");code=args.get("content","");t=args.get("type","html")
            if t=="html" or n.endswith(".html"):
                if len(code.strip()) < 200:
                    return {"ok":False,"data":f"代码太短（{len(code.strip())}字符）"}
                fn=f"app_{int(time.time())}.html";fp=str(OUT/"apps"/fn);Path(fp).parent.mkdir(exist_ok=True)
                Path(fp).write_text(code,encoding='utf-8')
                _LAST["url"]=f"/output/apps/{fn}";_LAST["time"]=time.time();_LAST["name"]=n
                return {"ok":True,"data":f"✅ **{n}**\n[📄 打开]({_LAST['url']})"}
            if t in ("python","tool") or n.endswith(".py"):
                fn=f"tool_{int(time.time())}.py";fp=str(TOOLS_DIR/fn);Path(fp).parent.mkdir(exist_ok=True)
                Path(fp).write_text(code,encoding='utf-8')
                return {"ok":True,"data":f"✅ 脚本已保存 /output/tools/{fn}"}
            fn=f"file_{int(time.time())}.txt";fp=str(OUT/fn);Path(fp).write_text(code,encoding='utf-8')
            return {"ok":True,"data":f"✅ 已保存\n[📄 查看](/output/{fn})"}
        if name == "register_tool":
            nm=args.get("name","");fp=args.get("filepath","")
            fp2=str(OUT/fp.lstrip("/output/"))
            if not Path(fp2).exists(): return {"ok":False,"data":"文件不存在"}
            spec=_iu.spec_from_file_location(nm,fp2);mod=_iu.module_from_spec(spec)
            spec.loader.exec_module(mod);_GENERATED_TOOLS[nm]=mod
            return {"ok":True,"data":f"工具 {nm} 已注册"}
        if name == "get_module_demo":
            mod = args.get("module","")
            mdir = BASE / "modules"
            if not mdir.exists(): return {"ok":True,"data":"无模块目录"}
            for f in mdir.rglob("*.py"):
                if mod in f.stem or mod in str(f.relative_to(mdir)):
                    content = f.read_text(encoding='utf-8',errors='replace')
                    classes = re.findall(r'class (\w+)', content)
                    funcs = re.findall(r'def (\w+)\(', content)
                    has_execute = "def execute(" in content or "async def execute(" in content
                    params_hint = ""
                    if has_execute:
                        exec_match = re.search(r'(async )?def execute\([^)]*\)', content)
                        if exec_match: params_hint = exec_match.group()
                    demo_lines = [
                        f"模块: {f.relative_to(mdir)}",
                        f"类: {', '.join(classes[:5]) if classes else '无'}",
                        f"方法: {', '.join(funcs[:10]) if funcs else '无'}",
                        f"支持execute: {'✅' if has_execute else '❌'}",
                        "",
                        "【调用示例】",
                        f"# 查看状态",
                        f'execute_module(module="{f.stem}", action="status")',
                        "",
                        f"# 执行任务",
                        f'execute_module(module="{f.stem}", action="execute", params=\'{{"key":"value"}}\')',
                    ]
                    if params_hint:
                        demo_lines.insert(4, f"execute签名: {params_hint}")
                    return {"ok":True,"data":"\n".join(demo_lines)}
            return {"ok":True,"data":f"未找到模块 '{mod}'，请用 search_modules 搜索"}
        if name == "list_tools":
            return {"ok":True,"data":f"内置: read_file/list_modules/search_modules/module_info/get_module_demo/execute_module/file_write/register_tool/create_task/list_tools/draw_image/web_search\n自定义: {', '.join(_GENERATED_TOOLS.keys()) if _GENERATED_TOOLS else '无'}"}
        if name == "create_task":
            n2=args.get("name","task");sch=args.get("schedule","0 * * * *");act=args.get("action","");params=args.get("params","{}")
            task_db=str(BASE/"_data"/"cron"/"tasks.json");Path(task_db).parent.mkdir(exist_ok=True)
            tasks=json.loads(Path(task_db).read_text()) if Path(task_db).exists() else {}
            tasks[n2]={"schedule":sch,"action":act,"params":params,"created":time.time()}
            Path(task_db).write_text(json.dumps(tasks,ensure_ascii=False))
            return {"ok":True,"data":f"✅ 任务 {n2} 已创建: {sch} 执行 {act}"}
        if name == "draw_image":
            p=args.get("prompt","");fn=f"img_{int(time.time())}.png";fp=str(OUT/fn)
            try:
                k=os.environ.get("ZHIPU_API_KEY","")
                if k:
                    r=httpx.post("https://open.bigmodel.cn/api/paas/v4/images/generations",headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"cogview-3","prompt":p},timeout=60)
                    if r.status_code==200 and r.json().get("data",[{}])[0].get("url",""):
                        urllib.request.urlretrieve(r.json()["data"][0]["url"],fp)
                        return {"ok":True,"data":f"![图](/output/{fn})","type":"image"}
            except Exception:
                pass
            try:
                k=os.environ.get("STABILITY_API_KEY","")
                if k:
                    r=httpx.post(f"https://api.stability.ai/v2beta/stable-image/generate/core",headers={"authorization":f"Bearer {k}","accept":"image/*"},data={"prompt":p,"output_format":"png"},timeout=60)
                    if r.status_code==200: Path(fp).write_bytes(r.content);return {"ok":True,"data":f"![图](/output/{fn})","type":"image"}
            except Exception:
                    pass
            return {"ok":False,"data":"画图失败：需要配置ZHIPU_API_KEY或STABILITY_API_KEY"}
        if name == "web_search":
            q=args.get("query","")
            # 搜索多源兜底：Bing(中国可用) → GitHub → 简单WebFetch
            try:
                # 源1: Bing HTML搜索（中国可用）
                headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                r=httpx.get(f"https://www.bing.com/search?q={urllib.parse.quote_plus(q)}", headers=headers, timeout=10)
                if r.status_code==200:
                    items=re.findall(r'<h2[^>]*><a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:5]
                    if items:
                        results=[f"- {re.sub(r'<[^>]+>','',t).strip()}: {u}" for u,t in items if u.startswith("http")]
                        if results: return {"ok":True,"data":"搜索结果:\n"+"\n".join(results)}
            except Exception:
                    pass
            try:
                # 源2: GitHub API
                r=httpx.get(f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=5",timeout=10)
                if r.status_code==200:
                    items=r.json().get("items",[]);lines=["GitHub搜索结果:"]+[f"- {i['name']}: {(i.get('description','') or '')[:80]}" for i in items[:5]]
                    return {"ok":True,"data":"\n".join(lines)}
            except Exception:
                    pass
            try:
                # 源3: 简单请求获取（兜底）
                r=httpx.get(f"https://api.bing.microsoft.com/v7.0/search?q={urllib.parse.quote(q)}&count=5&mkt=zh-CN",
                    headers={"Ocp-Apim-Subscription-Key": os.environ.get("BING_API_KEY","")}, timeout=10)
                if r.status_code==200:
                    items=r.json().get("webPages",{}).get("value",[])
                    if items: return {"ok":True,"data":"搜索结果:\n"+("\n".join(f"- {i['name']}: {i['url']}" for i in items))}
            except Exception:
                    pass
            return {"ok":True,"data":f"关于「{q}」的实时搜索结果暂时不可用，请直接提问或稍后重试"}
        # ========== 9个原有集成工具 ==========
        if name == "browser_use_task":
            try:
                from api.agents.agent_browser_use import run_browser_task
                result = run_browser_task(args.get("task",""))
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e: return {"ok":False,"data":f"浏览器失败: {e}"}
        if name == "gpt_research":
            try:
                from api.agents.agent_gpt_researcher import quick_research
                result = quick_research(args.get("query",""))
                return {"ok":result.get("success",False),"data":result.get("report",result.get("error","未知错误"))}
            except Exception as e: return {"ok":False,"data":f"研究失败: {e}"}
        if name == "openhands_generate":
            try:
                from api.agents.agent_openhands import generate_project
                result = generate_project(args.get("description",""), args.get("project_type","fullstack"))
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e: return {"ok":False,"data":f"项目失败: {e}"}
        if name == "letta_message":
            try:
                from api.agents.agent_letta import send_message_to_letta
                result = send_message_to_letta(args.get("message",""))
                return {"ok":result.get("success",False),"data":result.get("response",result.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"Letta失败: {e}"}
        if name == "composio_execute":
            try:
                from api.agents.agent_composio import execute_composio_action, init_composio
                init_composio()
                result = execute_composio_action(args.get("app_name",""), args.get("action_name",""), args.get("params",{}))
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e: return {"ok":False,"data":f"Composio失败: {e}"}
        if name == "self_evolving_analyze":
            try:
                from api.agents.agent_self_evolving import analyze_codebase
                result = analyze_codebase(args.get("repo_path","."))
                return {"ok":result.get("success",False),"data":result.get("summary",result.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"分析失败: {e}"}
        if name == "moltron_learn":
            try:
                from api.agents.agent_moltron import learn_skill
                result = learn_skill(args.get("skill_name",""), args.get("skill_description",""))
                return {"ok":result.get("success",False),"data":result.get("message",result.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"Moltron失败: {e}"}
        if name == "accomplish_desktop":
            try:
                from api.agents.agent_accomplish import execute_workflow
                wf = args.get("workflow","[]")
                if isinstance(wf, str): import json as _j; wf = _j.loads(wf)
                if not wf: return {"ok":False,"data":"缺少workflow"}
                result = execute_workflow(wf)
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e: return {"ok":False,"data":f"桌面失败: {e}"}
        if name == "toolbench_discover":
            try:
                from api.agents.agent_toolbench import toolbench_discover as _tb
                result = _tb(query=args.get("query",""), category=args.get("category",""), action=args.get("action","search"), api_name=args.get("api_name",""))
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e: return {"ok":False,"data":f"ToolBench失败: {e}"}
        # ========== 2026-06-09 新增16个集成工具 ==========
        if name == "markitdown_convert":
            try:
                from api.agents.agent_markitdown import convert_to_markdown
                r = convert_to_markdown(file_path=args.get("file_path",""), text=args.get("text",""), file_type=args.get("file_type","auto"))
                return {"ok":r.get("success",False),"data":r.get("markdown",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"文档转换失败: {e}"}
        if name == "scrapegraphai_scrape":
            try:
                from api.agents.agent_scrapegraphai import ai_scrape
                r = ai_scrape(url=args.get("url",""), prompt=args.get("prompt","提取页面上所有有用信息"))
                return {"ok":r.get("success",False),"data":json.dumps(r.get("data",r.get("error","")),ensure_ascii=False)[:3000]}
            except Exception as e: return {"ok":False,"data":f"智能爬虫失败: {e}"}
        if name == "interpreter_execute":
            try:
                from api.agents.agent_interpreter import interpreter_execute
                r = interpreter_execute(command=args.get("command",""), language=args.get("language","python"))
                return {"ok":r.get("success",False),"data":r.get("output",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"电脑控制失败: {e}"}
        if name == "s2c_generate":
            try:
                from api.agents.agent_s2c import screenshot_to_code
                r = screenshot_to_code(image_path=args.get("image_path",""), image_url=args.get("image_url",""), stack=args.get("stack","html_tailwind"))
                s = r.get("summary",r.get("error",""))
                if r.get("preview_url"): s += "\n预览: " + r["preview_url"]
                return {"ok":r.get("success",False),"data":s}
            except Exception as e: return {"ok":False,"data":f"截图转代码失败: {e}"}
        if name == "pra_review":
            try:
                from api.agents.agent_pra import review_pull_request
                r = review_pull_request(pr_url=args.get("pr_url",""), repo=args.get("repo",""), pr_number=args.get("pr_number",0))
                return {"ok":r.get("success",False),"data":json.dumps({"summary":r.get("summary",""),"issues":len(r.get("issues",[])),"suggestions":len(r.get("suggestions",[]))},ensure_ascii=False)}
            except Exception as e: return {"ok":False,"data":f"PR审查失败: {e}"}
        if name == "qodo_testgen":
            try:
                from api.agents.agent_qodo import generate_tests
                r = generate_tests(source_path=args.get("source_path",""), source_code=args.get("source_code",""), framework=args.get("framework","pytest"))
                return {"ok":r.get("success",False),"data":r.get("summary",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"测试生成失败: {e}"}
        if name == "aider_edit":
            try:
                from api.agents.agent_aider import aider_edit
                r = aider_edit(file_path=args.get("file_path",""), instruction=args.get("instruction",""))
                return {"ok":r.get("success",False),"data":r.get("diff",r.get("error",""))[:2000]}
            except Exception as e: return {"ok":False,"data":f"Aider编辑失败: {e}"}
        if name == "openclaw_connect":
            try:
                from api.agents.agent_openclaw import openclaw_connect
                r = openclaw_connect(platform=args.get("platform",""), bot_token=args.get("bot_token",""))
                return {"ok":r.get("success",False),"data":r.get("message",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"OpenClaw连接失败: {e}"}
        if name == "openclaw_send":
            try:
                from api.agents.agent_openclaw import openclaw_send
                r = openclaw_send(platform=args.get("platform",""), recipient=args.get("recipient",""), message=args.get("message",""))
                return {"ok":r.get("success",False),"data":r.get("message_id",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"OpenClaw发送失败: {e}"}
        if name == "tts_speak":
            try:
                from api.agents.agent_tts import text_to_speech
                r = text_to_speech(text=args.get("text",""), voice=args.get("voice","default"), emotion=args.get("emotion","neutral"))
                fn = r.get("audio_file","")
                return {"ok":r.get("success",False),"data":f"音频: {fn}" if fn else r.get("error","")}
            except Exception as e: return {"ok":False,"data":f"语音合成失败: {e}"}
        if name == "chatdev_run":
            try:
                from api.agents.agent_chatdev import chatdev_run
                r = chatdev_run(task=args.get("task",""))
                return {"ok":r.get("success",False),"data":r.get("summary",r.get("result",r.get("error","")))}
            except Exception as e: return {"ok":False,"data":f"ChatDev失败: {e}"}
        if name == "openmanus_run":
            try:
                from api.agents.agent_openmanus import openmanus_run
                r = openmanus_run(task=args.get("task",""))
                return {"ok":r.get("success",False),"data":str(r.get("result",r.get("error","")))[:2000]}
            except Exception as e: return {"ok":False,"data":f"OpenManus失败: {e}"}
        if name == "autogpt_run":
            try:
                from api.agents.agent_autogpt import autogpt_run
                r = autogpt_run(goal=args.get("goal",""), max_steps=args.get("max_steps",10))
                return {"ok":r.get("success",False),"data":r.get("summary",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"AutoGPT失败: {e}"}
        if name == "agenteval_benchmark":
            try:
                from api.agents.agent_agenteval import agenteval_benchmark
                r = agenteval_benchmark()
                return {"ok":r.get("success",False),"data":json.dumps(r.get("summary",{}),ensure_ascii=False)}
            except Exception as e: return {"ok":False,"data":f"Agent评测失败: {e}"}
        if name == "swe_fix":
            try:
                from api.agents.agent_swe import swe_fix_issue
                r = swe_fix_issue(repo=args.get("repo",""), issue_number=args.get("issue_number",0))
                return {"ok":r.get("success",False),"data":r.get("analysis",r.get("error",""))[:1000]}
            except Exception as e: return {"ok":False,"data":f"SWE修复失败: {e}"}
        if name == "gptpilot_build":
            try:
                from api.agents.agent_gptpilot import gptpilot_build
                r = gptpilot_build(description=args.get("description",""))
                return {"ok":r.get("success",False),"data":r.get("summary",r.get("error",""))}
            except Exception as e: return {"ok":False,"data":f"GPT-Pilot失败: {e}"}
        if name == "text2sql_query":
            try:
                from api.agents.agent_chat2db import text2sql_query
                r = text2sql_query(question=args.get("question",""), connection=args.get("connection",""))
                s = f"SQL: {r.get('sql','')}\n结果: {json.dumps(r.get('result',[]),ensure_ascii=False)[:2000]}"
                return {"ok":r.get("success",False),"data":s}
            except Exception as e: return {"ok":False,"data":f"数据库查询失败: {e}"}
        if name == "bolt_generate":
            try:
                from api.agents.agent_bolt import bolt_generate
                r = bolt_generate(prompt=args.get("prompt",""), framework=args.get("framework","vue"))
                s = r.get("summary","")
                if r.get("preview_url"): s += "\n预览: " + r["preview_url"]
                return {"ok":r.get("success",False),"data":s}
            except Exception as e: return {"ok":False,"data":f"Bolt生成失败: {e}"}
        if name == "agentk8s_deploy":
            try:
                from api.agents.agent_agentk8s import agentk8s_deploy
                r = agentk8s_deploy(agent_name=args.get("agent_name","evo-agent"))
                return {"ok":r.get("success",False),"data":f"YAML: {r.get('yaml_path','')}\n部署: {r.get('next_step','')}"}
            except Exception as e: return {"ok":False,"data":f"K8s部署失败: {e}"}
        # ===== 2026-06-09 第3轮22个新工具 =====
        if name == "openmontage_generate_script":
            try:
                from api.agents.agent_openmontage import openmontage_generate_script
                r = openmontage_generate_script(topic=args.get("topic",""), style=args.get("style","documentary"), duration=args.get("duration",60))
                return {"ok":r.get("success",False),"data":json.dumps(r.get("data",{}),ensure_ascii=False)}
            except Exception as e: return {"ok":False,"data":f"视频脚本生成失败: {e}"}
        if name == "openmontage_search_materials":
            try:
                from api.agents.agent_openmontage import openmontage_search_materials
                r = openmontage_search_materials(keywords=args.get("keywords",""))
                return {"ok":r.get("success",False),"data":json.dumps(r.get("data",{}),ensure_ascii=False)}
            except Exception as e: return {"ok":False,"data":f"素材搜索失败: {e}"}
        if name == "lida_visualize":
            try:
                from api.agents.agent_lida import lida_visualize
                r = lida_visualize(data_description=args.get("data_description",""), goal=args.get("goal",""), chart_type=args.get("chart_type",""))
                return {"ok":r.get("success",False),"data":f"生成了{r.get('total',0)}个图表"}
            except Exception as e: return {"ok":False,"data":f"可视化失败: {e}"}
        if name == "lida_explore":
            try:
                from api.agents.agent_lida import lida_explore
                r = lida_explore(data_file_path=args.get("data_file_path",""))
                return {"ok":r.get("success",False),"data":f"探索完成: {r.get('charts_count',0)}个图表"}
            except Exception as e: return {"ok":False,"data":f"探索失败: {e}"}
        if name == "paddleocr_image":
            try:
                from api.agents.agent_paddleocr import paddleocr_image
                r = paddleocr_image(image_path=args.get("image_path",""), lang=args.get("lang","ch"))
                return {"ok":r.get("success",False),"data":r.get("text",r.get("error",""))[:2000]}
            except Exception as e: return {"ok":False,"data":f"OCR失败: {e}"}
        if name == "paddleocr_pdf":
            try:
                from api.agents.agent_paddleocr import paddleocr_pdf
                r = paddleocr_pdf(pdf_path=args.get("pdf_path",""))
                return {"ok":r.get("success",False),"data":f"识别了{r.get('total_pages',0)}页"}
            except Exception as e: return {"ok":False,"data":f"PDF OCR失败: {e}"}
        if name == "zen_scan":
            try:
                from api.agents.agent_zen import zen_scan
                r = zen_scan(target=args.get("target",""), scan_type=args.get("scan_type","quick"))
                return {"ok":r.get("success",False),"data":f"发现{r.get('data',{}).get('total',0)}个风险"}
            except Exception as e: return {"ok":False,"data":f"安全扫描失败: {e}"}
        if name == "zen_report":
            try:
                from api.agents.agent_zen import zen_report
                r = zen_report(target=args.get("target",""))
                return {"ok":r.get("success",False),"data":r.get('data',{}).get('summary','')}
            except Exception as e: return {"ok":False,"data":f"安全报告失败: {e}"}
        if name == "shannon_audit":
            try:
                from api.agents.agent_shannon import shannon_audit
                r = shannon_audit(source_path=args.get("source_path",""))
                return {"ok":r.get("success",False),"data":f"发现{r.get('total',0)}个问题"}
            except Exception as e: return {"ok":False,"data":f"代码审计失败: {e}"}
        if name == "openant_scan":
            try:
                from api.agents.agent_openant import openant_scan
                r = openant_scan(target=args.get("target",""))
                return {"ok":r.get("success",False),"data":f"发现{r.get('total',0)}个漏洞"}
            except Exception as e: return {"ok":False,"data":f"漏洞扫描失败: {e}"}
        if name == "legal_review_contract":
            try:
                from api.agents.agent_legal import legal_review_contract
                r = legal_review_contract(contract_text=args.get("contract_text",""))
                return {"ok":r.get("success",False),"data":f"发现{r.get('data',{}).get('total_issues',0)}个关注点"}
            except Exception as e: return {"ok":False,"data":f"合同审查失败: {e}"}
        if name == "legal_analyze_compliance":
            try:
                from api.agents.agent_legal import legal_analyze_compliance
                r = legal_analyze_compliance(document_text=args.get("document_text",""))
                return {"ok":r.get("success",False),"data":f"合规度:{'合规' if r.get('data',{}).get('compliant') else '不合规'}, 缺口:{r.get('data',{}).get('total_gaps',0)}"}
            except Exception as e: return {"ok":False,"data":f"合规分析失败: {e}"}
        if name == "twenty_create_contact":
            try:
                from api.agents.agent_twenty import twenty_create_contact
                r = twenty_create_contact(name=args.get("name",""), email=args.get("email",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"创建联系人失败: {e}"}
        if name == "twenty_create_deal":
            try:
                from api.agents.agent_twenty import twenty_create_deal
                r = twenty_create_deal(name=args.get("name",""), amount=args.get("amount",0))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"创建交易失败: {e}"}
        if name == "frappe_hr_employee":
            try:
                from api.agents.agent_frappehr import frappe_hr_employee_info
                r = frappe_hr_employee_info(employee_id=args.get("employee_id",""))
                return {"ok":r.get("success",False),"data":json.dumps(r.get("data",{}),ensure_ascii=False)}
            except Exception as e: return {"ok":False,"data":f"HR查询失败: {e}"}
        if name == "frappe_hr_leave":
            try:
                from api.agents.agent_frappehr import frappe_hr_leave_request
                r = frappe_hr_leave_request(employee_id=args.get("employee_id",""), start_date=args.get("start_date",""), end_date=args.get("end_date",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"请假提交失败: {e}"}
        if name == "invoice_create":
            try:
                from api.agents.agent_invoice import invoice_create
                r = invoice_create(client=args.get("client",""), amount=args.get("amount",0))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"发票创建失败: {e}"}
        if name == "invoice_track_expense":
            try:
                from api.agents.agent_invoice import invoice_track_expense
                r = invoice_track_expense(description=args.get("description",""), amount=args.get("amount",0))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"费用记录失败: {e}"}
        if name == "chatwoot_create_ticket":
            try:
                from api.agents.agent_chatwoot import chatwoot_create_ticket
                r = chatwoot_create_ticket(subject=args.get("subject",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"工单创建失败: {e}"}
        if name == "chatwoot_reply_ticket":
            try:
                from api.agents.agent_chatwoot import chatwoot_reply_ticket
                r = chatwoot_reply_ticket(ticket_id=args.get("ticket_id",""), message=args.get("message",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"工单回复失败: {e}"}
        if name == "postiz_create_post":
            try:
                from api.agents.agent_postiz import postiz_create_post
                r = postiz_create_post(content=args.get("content",""), platforms=args.get("platforms",["twitter"]))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"发帖失败: {e}"}
        if name == "mautic_send_email":
            try:
                from api.agents.agent_mautic import mautic_send_email
                r = mautic_send_email(subject=args.get("subject",""), content=args.get("content",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"邮件发送失败: {e}"}
        if name == "superset_create_chart":
            try:
                from api.agents.agent_superset import superset_create_chart
                r = superset_create_chart(dataset=args.get("dataset",""), chart_type=args.get("chart_type","bar"))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"图表创建失败: {e}"}
        if name == "dataease_create_dashboard":
            try:
                from api.agents.agent_dataease import dataease_create_dashboard
                r = dataease_create_dashboard(name=args.get("name",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"仪表盘创建失败: {e}"}
        if name == "heyform_create_survey":
            try:
                from api.agents.agent_heyform import heyform_create_survey
                r = heyform_create_survey(title=args.get("title",""))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"问卷创建失败: {e}"}
        if name == "docetl_extract":
            try:
                from api.agents.agent_docetl import docetl_extract_documents
                r = docetl_extract_documents(file_paths=args.get("file_paths",[]))
                return {"ok":r.get("success",False),"data":f"处理{r.get('total',0)}个文件"}
            except Exception as e: return {"ok":False,"data":f"文档提取失败: {e}"}
        if name == "accord_create_contract":
            try:
                from api.agents.agent_accord import accord_create_contract
                r = accord_create_contract(template=args.get("template","generic"))
                return {"ok":r.get("success",False),"data":r.get("message","")}
            except Exception as e: return {"ok":False,"data":f"合同创建失败: {e}"}
        if name == "claude_code_generate":
            try:
                from api.agents.agent_claude import claude_code_generate
                r = claude_code_generate(prompt=args.get("prompt",""), language=args.get("language","python"))
                return {"ok":r.get("success",False),"data":f"生成了{r.get('length',0)}字符代码"}
            except Exception as e: return {"ok":False,"data":f"代码生成失败: {e}"}
        if name == "plane_project":
            try:
                from api.agents.agent_plane import plane_project
                r = plane_project(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"plane_project执行失败: {e}"}
        if name == "openproject_mgmt":
            try:
                from api.agents.agent_openproject import openproject_mgmt
                r = openproject_mgmt(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"openproject_mgmt执行失败: {e}"}
        if name == "cal_schedule":
            try:
                from api.agents.agent_cal import cal_schedule
                r = cal_schedule(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"cal_schedule执行失败: {e}"}
        if name == "novu_notify":
            try:
                from api.agents.agent_novu import novu_notify
                r = novu_notify(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"novu_notify执行失败: {e}"}
        if name == "keycloak_auth":
            try:
                from api.agents.agent_keycloak import keycloak_auth
                r = keycloak_auth(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"keycloak_auth执行失败: {e}"}
        if name == "meilisearch_search":
            try:
                from api.agents.agent_meilisearch import meilisearch_search
                r = meilisearch_search(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"meilisearch_search执行失败: {e}"}
        if name == "minio_storage":
            try:
                from api.agents.agent_minio import minio_storage
                r = minio_storage(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"minio_storage执行失败: {e}"}
        if name == "opentofu_apply":
            try:
                from api.agents.agent_opentofu import opentofu_apply
                r = opentofu_apply(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"opentofu_apply执行失败: {e}"}
        if name == "ansible_run":
            try:
                from api.agents.agent_ansible import ansible_run
                r = ansible_run(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"ansible_run执行失败: {e}"}
        if name == "strapi_cms":
            try:
                from api.agents.agent_strapi import strapi_cms
                r = strapi_cms(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"strapi_cms执行失败: {e}"}
        if name == "directus_api":
            try:
                from api.agents.agent_directus import directus_api
                r = directus_api(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"directus_api执行失败: {e}"}
        if name == "uptime_kuma":
            try:
                from api.agents.agent_uptime import uptime_kuma
                r = uptime_kuma(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"uptime_kuma执行失败: {e}"}
        if name == "oneuptime_monitor":
            try:
                from api.agents.agent_oneuptime import oneuptime_monitor
                r = oneuptime_monitor(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"oneuptime_monitor执行失败: {e}"}
        if name == "signoz_apm":
            try:
                from api.agents.agent_signoz import signoz_apm
                r = signoz_apm(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"signoz_apm执行失败: {e}"}
        if name == "wazuh_siem":
            try:
                from api.agents.agent_wazuh import wazuh_siem
                r = wazuh_siem(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"wazuh_siem执行失败: {e}"}
        if name == "nats_mq":
            try:
                from api.agents.agent_nats import nats_mq
                r = nats_mq(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"nats_mq执行失败: {e}"}
        if name == "rabbitmq_broker":
            try:
                from api.agents.agent_rabbitmq import rabbitmq_broker
                r = rabbitmq_broker(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"rabbitmq_broker执行失败: {e}"}
        if name == "gitea_git":
            try:
                from api.agents.agent_gitea import gitea_git
                r = gitea_git(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"gitea_git执行失败: {e}"}
        if name == "wikijs_wiki":
            try:
                from api.agents.agent_wikijs import wikijs_wiki
                r = wikijs_wiki(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"wikijs_wiki执行失败: {e}"}
        if name == "bookstack_wiki":
            try:
                from api.agents.agent_bookstack import bookstack_wiki
                r = bookstack_wiki(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"bookstack_wiki执行失败: {e}"}
        if name == "projectsend_files":
            try:
                from api.agents.agent_projectsend import projectsend_files
                r = projectsend_files(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"projectsend_files执行失败: {e}"}
        if name == "odoo_manage":
            try:
                from api.agents.agent_odoo import odoo_manage
                r = odoo_manage(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"odoo_manage执行失败: {e}"}
        if name == "erpclaw_manage":
            try:
                from api.agents.agent_erpclaw import erpclaw_manage
                r = erpclaw_manage(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"erpclaw_manage执行失败: {e}"}
        if name == "coolify_deploy":
            try:
                from api.agents.agent_coolify import coolify_deploy
                r = coolify_deploy(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"coolify_deploy执行失败: {e}"}
        if name == "rustdesk_connect":
            try:
                from api.agents.agent_rustdesk import rustdesk_connect
                r = rustdesk_connect(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"rustdesk_connect执行失败: {e}"}
        if name == "docuseal_sign":
            try:
                from api.agents.agent_docuseal import docuseal_sign
                r = docuseal_sign(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"docuseal_sign执行失败: {e}"}
        if name == "homeassistant_control":
            try:
                from api.agents.agent_homeassistant import homeassistant_control
                r = homeassistant_control(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"homeassistant_control执行失败: {e}"}
        if name == "vaultwarden_manage":
            try:
                from api.agents.agent_vaultwarden import vaultwarden_manage
                r = vaultwarden_manage(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"vaultwarden_manage执行失败: {e}"}
        if name == "nocodb_manage":
            try:
                from api.agents.agent_nocodb import nocodb_manage
                r = nocodb_manage(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"nocodb_manage执行失败: {e}"}
        if name == "appsmith_build":
            try:
                from api.agents.agent_appsmith import appsmith_build
                r = appsmith_build(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"appsmith_build执行失败: {e}"}
        if name == "airbyte_sync":
            try:
                from api.agents.agent_airbyte import airbyte_sync
                r = airbyte_sync(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"airbyte_sync执行失败: {e}"}
        if name == "mlflow_track":
            try:
                from api.agents.agent_mlflow import mlflow_track
                r = mlflow_track(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"mlflow_track执行失败: {e}"}
        if name == "langfuse_observe":
            try:
                from api.agents.agent_langfuse import langfuse_observe
                r = langfuse_observe(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"langfuse_observe执行失败: {e}"}
        if name == "hoppscotch_test":
            try:
                from api.agents.agent_hoppscotch import hoppscotch_test
                r = hoppscotch_test(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"hoppscotch_test执行失败: {e}"}
        if name == "grist_analyze":
            try:
                from api.agents.agent_grist import grist_analyze
                r = grist_analyze(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"grist_analyze执行失败: {e}"}
        if name == "freshrss_read":
            try:
                from api.agents.agent_freshrss import freshrss_read
                r = freshrss_read(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"freshrss_read执行失败: {e}"}
        if name == "listmonk_send":
            try:
                from api.agents.agent_listmonk import listmonk_send
                r = listmonk_send(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"listmonk_send执行失败: {e}"}
        if name == "mermaid_chart":
            try:
                from api.agents.agent_mermaid import mermaid_chart
                r = mermaid_chart(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"mermaid_chart执行失败: {e}"}
        if name == "nocobase_build":
            try:
                from api.agents.agent_nocobase import nocobase_build
                r = nocobase_build(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"nocobase_build执行失败: {e}"}
        if name == "scriberr_transcribe":
            try:
                from api.agents.agent_scriberr import scriberr_transcribe
                r = scriberr_transcribe(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"scriberr_transcribe执行失败: {e}"}
        if name == "keploy_test":
            try:
                from api.agents.agent_keploy import keploy_test
                r = keploy_test(**args)
                return {"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}
            except Exception as e:
                return {"ok": False, "data": f"keploy_test执行失败: {e}"}
        # ===== 并发多Agent =====
        if name == "concurrent_run":
            try:
                from api.agents.agent_concurrent import run_team
                r = run_team(
                    task_name=args.get("task_name", "任务"),
                    msg=args.get("details", ""),
                    BASE=BASE, OUT=OUT, _LAST=_LAST, _GENERATED_TOOLS=_GENERATED_TOOLS
                )
                res = r.get("final_result") or r.get("analysis", "")[:300]
                return {"ok": True, "data": res}
            except Exception as e:
                return {"ok": False, "data": f"并发执行失败: {e}"}
        # ===== YoYo-Evolve自进化 =====
        if name == "yoyo_scan":
            try:
                from api.agents.yoyo_evolve import auto_scan, auto_evolve
                scope = args.get("scope", "auto")
                if scope == "auto":
                    r = auto_evolve(BASE)
                else:
                    r = auto_scan(BASE)
                if isinstance(r, dict):
                    summary = r.get("analysis") or r.get("message", "")
                    details = r.get("details", [])
                    return {"ok": True, "data": f"{summary}\n详情报{len(details)}条"}
                return {"ok": True, "data": str(r)[:500]}
            except Exception as e:
                return {"ok": False, "data": f"自进化扫描失败: {e}"}
        if name == "yoyo_history":
            try:
                from api.agents.yoyo_evolve import get_evolution_history
                history = get_evolution_history(limit=args.get("limit", 10))
                if not history:
                    return {"ok": True, "data": "暂无自进化记录"}
                lines = []
                for h in history:
                    lines.append(f"[{h['time'][:16]}] {h['target'][:30]} → {h['status']}")
                return {"ok": True, "data": "\n".join(lines)}
            except Exception as e:
                return {"ok": False, "data": f"查询历史失败: {e}"}
    except Exception as e:
        return {"ok":False,"data":f"执行出错: {e}"}
