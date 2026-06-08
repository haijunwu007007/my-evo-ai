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
                    # 自动生成调用示例
                    classes = re.findall(r'class (\w+)', content)
                    funcs = re.findall(r'def (\w+)\(', content)
                    has_execute = "def execute(" in content or "async def execute(" in content
                    params_hint = ""
                    if has_execute:
                        # 提取 execute 方法的参数
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
            # CogView-3
            try:
                k=os.environ.get("ZHIPU_API_KEY","")
                if k:
                    r=httpx.post("https://open.bigmodel.cn/api/paas/v4/images/generations",headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"cogview-3","prompt":p},timeout=60)
                    if r.status_code==200 and r.json().get("data",[{}])[0].get("url",""):
                        urllib.request.urlretrieve(r.json()["data"][0]["url"],fp)
                        return {"ok":True,"data":f"![图](/output/{fn})","type":"image"}
            except: pass
            # Stability备选
            try:
                k=os.environ.get("STABILITY_API_KEY","")
                if k:
                    r=httpx.post(f"https://api.stability.ai/v2beta/stable-image/generate/core",headers={"authorization":f"Bearer {k}","accept":"image/*"},data={"prompt":p,"output_format":"png"},timeout=60)
                    if r.status_code==200: Path(fp).write_bytes(r.content);return {"ok":True,"data":f"![图](/output/{fn})","type":"image"}
            except: pass
            return {"ok":False,"data":"画图失败：需要配置ZHIPU_API_KEY或STABILITY_API_KEY"}
        if name == "web_search":
            q=args.get("query","")
            # DuckDuckGo
            try:
                r=httpx.get(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(q)}",timeout=15)
                if r.status_code==200:
                    links=re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>([^<]+)</a>',r.text)[:8]
                    results=[f"- {t.strip()}: {u}" for u,t in links if not u.startswith("http")][:5]
                    if results: return {"ok":True,"data":"搜索结果:\n"+("\n".join(results))}
            except: pass
            # GitHub备选
            try:
                r=httpx.get(f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=5",timeout=15)
                if r.status_code==200:
                    items=r.json().get("items",[]);lines=["GitHub搜索结果:"]+[f"- {i['name']}: {(i.get('description','') or '')[:80]}" for i in items[:5]]
                    return {"ok":True,"data":"\n".join(lines)}
            except: pass
            return {"ok":True,"data":"搜索暂时不可用"}
        # ========== 新集成工具 ==========
        if name == "browser_use_task":
            try:
                from api.agent_browser_use import run_browser_task
                task = args.get("task","")
                if not task: return {"ok":False,"data":"缺少task参数"}
                result = run_browser_task(task)
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e:
                return {"ok":False,"data":f"浏览器自动化失败: {e}"}
        if name == "gpt_research":
            try:
                from api.agent_gpt_researcher import quick_research
                query = args.get("query","")
                if not query: return {"ok":False,"data":"缺少query参数"}
                result = quick_research(query)
                return {"ok":result.get("success",False),"data":result.get("report",result.get("error","未知错误"))}
            except Exception as e:
                return {"ok":False,"data":f"自主研究失败: {e}"}
        if name == "openhands_generate":
            try:
                from api.agent_openhands import generate_project
                description = args.get("description","")
                project_type = args.get("project_type","fullstack")
                if not description: return {"ok":False,"data":"缺少description参数"}
                result = generate_project(description, project_type)
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e:
                return {"ok":False,"data":f"项目生成失败: {e}"}
        if name == "letta_message":
            try:
                from api.agent_letta import send_message_to_letta
                message = args.get("message","")
                if not message: return {"ok":False,"data":"缺少message参数"}
                result = send_message_to_letta(message)
                return {"ok":result.get("success",False),"data":result.get("response",result.get("error","未知错误"))}
            except Exception as e:
                return {"ok":False,"data":f"Letta记忆系统失败: {e}"}
        if name == "composio_execute":
            try:
                from api.agent_composio import execute_composio_action, init_composio
                app_name = args.get("app_name","")
                action_name = args.get("action_name","")
                params = args.get("params",{})
                if not app_name or not action_name: return {"ok":False,"data":"缺少app_name或action_name参数"}
                # 初始化（如果未初始化）
                init_composio()
                result = execute_composio_action(app_name, action_name, params)
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e:
                return {"ok":False,"data":f"Composio工具执行失败: {e}"}
        if name == "self_evolving_analyze":
            try:
                from api.agent_self_evolving import analyze_codebase
                repo_path = args.get("repo_path",".")
                result = analyze_codebase(repo_path)
                return {"ok":result.get("success",False),"data":result.get("summary",result.get("error","未知错误"))}
            except Exception as e:
                return {"ok":False,"data":f"代码分析失败: {e}"}
        if name == "moltron_learn":
            try:
                from api.agent_moltron import learn_skill
                skill_name = args.get("skill_name","")
                skill_description = args.get("skill_description","")
                if not skill_name or not skill_description: return {"ok":False,"data":"缺少skill_name或skill_description参数"}
                result = learn_skill(skill_name, skill_description)
                return {"ok":result.get("success",False),"data":result.get("message",result.get("error","未知错误"))}
            except Exception as e:
                return {"ok":False,"data":f"技能学习失败: {e}"}
        if name == "accomplish_desktop":
            try:
                from api.agent_accomplish import execute_workflow
                workflow_raw = args.get("workflow","[]")
                if isinstance(workflow_raw, str):
                    import json as _json
                    workflow = _json.loads(workflow_raw)
                else:
                    workflow = workflow_raw
                if not workflow: return {"ok":False,"data":"缺少workflow参数"}
                result = execute_workflow(workflow)
                return {"ok":result.get("success",False),"data":str(result)}
            except Exception as e:
                return {"ok":False,"data":f"桌面自动化失败: {e}"}
    except Exception as e:
        return {"ok":False,"data":f"执行出错: {e}"}
