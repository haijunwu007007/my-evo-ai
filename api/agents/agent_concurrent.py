"""并发多Agent执行引擎 — 多Agent并行协作，协调输出"""

import json, time, re, concurrent.futures, threading
from pathlib import Path
from typing import Optional

_local = threading.local()

def get_llm():
    """获取LLM调用函数（延迟导入避免循环依赖）"""
    from api.agent_llm import call_llm
    return call_llm

def get_exec_tool():
    """获取工具执行函数"""
    from api.agent_tools import exec_tool
    return exec_tool

def run_concurrent(tasks: list, max_workers: int = 3, timeout: int = 120) -> dict:
    """并发执行多个Agent任务
    
    Args:
        tasks: 任务列表，每项为 {"name": str, "prompt": str, "role": str, "tools": bool}
        max_workers: 最大并发数
        timeout: 超时秒数
    
    Returns:
        {"success": bool, "results": {name: result}, "errors": {name: error}}
    """
    call_llm = get_llm()
    results = {}
    errors = {}
    
    def _run_single(task: dict):
        name = task.get("name", "unknown")
        prompt = task.get("prompt", "")
        role = task.get("role", "助手")
        use_tools = task.get("tools", False)
        try:
            msgs = [{"role":"system", "content":f"你是{role}，请专业完成任务。"}, {"role":"user", "content":prompt[:500]}]
            r, tcs = call_llm(msgs, None, "")
            if not r:
                r = f"({name}空响应)"
            if use_tools and tcs:
                exec_tool = get_exec_tool()
                for tc in tcs[:2]:
                    func = tc.get("function", {})
                    nm = func.get("name", "")
                    args = {}
                    try: args = json.loads(func.get("arguments", "{}"))
                    except: pass
                    tr = exec_tool(nm, args, None, None, {}, {})
                    if tr and tr.get("data"):
                        r = tr["data"][:300]
            results[name] = r
        except Exception as e:
            errors[name] = str(e)[:100]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(_run_single, t): t.get("name", f"task_{i}") for i, t in enumerate(tasks)}
        done, _ = concurrent.futures.wait(futs, timeout=timeout)
        for f in done:
            try: f.result()
            except Exception as e:
                nm = futs[f]
                errors[nm] = str(e)[:100]
    
    return {"success": len(errors) < len(tasks), "results": results, "errors": errors}

def run_team(task_name: str, spec: str = "", msg: str = "", key: str = "", 
             BASE=None, OUT=None, _LAST=None, _GENERATED_TOOLS=None) -> dict:
    """团队协作模式：分析师+开发者+审查者 三条并发管线
    
    Returns:
        {"spec": str, "analysis": str, "code_path": str, "iterations": int, "final_result": str}
    """
    from api.agent_llm import call_llm
    call_llm = get_llm()
    
    if OUT is None: from api.infra import OUT as _o; OUT = _o
    
    result = {
        "spec": spec,
        "analysis": "",
        "code_path": "",
        "iterations": 0,
        "final_result": ""
    }
    
    # 分析师 + 开发者 并行
    tasks = [
        {"name": "分析师", "prompt": f"分析任务：{task_name[:100]}\n需求详情：{msg[:200]}\n输出JSON分析结果。", "role": "系统分析师"},
        {"name": "开发者", "prompt": f"开发任务：{task_name[:100]}\n生成完整HTML/CSS/JS。输出放在```html```中。", "role": "前端开发者"},
    ]
    cr = run_concurrent(tasks, max_workers=2, timeout=120)
    result["analysis"] = list(cr["results"].values())[0] if cr["results"] else ""
    code = list(cr["results"].values())[1] if len(cr["results"]) > 1 else ""
    
    # 提取代码
    html_code = None
    m = re.search(r'```html\s*(.*?)\s*```', code, re.DOTALL)
    if m: html_code = m.group(1)
    else:
        m2 = re.search(r'```\s*(.*?)\s*```', code, re.DOTALL)
        if m2: html_code = m2.group(1)
        else: html_code = code if len(code) > 200 else None
    
    if html_code and len(html_code) > 200:
        html_code = re.sub(r'```\w*', '', html_code).strip()
        fn = f"app_{int(time.time())}.html"
        fp = str(OUT / "apps" / fn)
        Path(fp).parent.mkdir(exist_ok=True)
        Path(fp).write_text(html_code, encoding='utf-8')
        
        if _LAST is not None:
            _LAST["url"] = f"/output/apps/{fn}"
            _LAST["time"] = time.time()
            _LAST["name"] = task_name
        result["code_path"] = fp
        
        # 审查者自我迭代（最多2轮）
        iterations = 1
        for _ in range(2):
            review_prompt = f"审查以下代码。需求：{task_name[:50]}\n代码前300字:\n{html_code[:500]}...\n回复：通过/不通过+修复建议。"
            r_msgs = [{"role":"system","content":"严格代码审查专家。"}, {"role":"user","content":review_prompt}]
            rr, _ = call_llm(r_msgs, None, key)
            if rr and "不通过" in rr[:20]:
                fix_prompt = f"修复：{rr[:300]}\n输出完整HTML。"
                fix_msgs = [{"role":"user","content":fix_prompt}]
                fr, _ = call_llm(fix_msgs, None, key)
                if fr:
                    m3 = re.search(r'```html\s*(.*?)\s*```', fr, re.DOTALL)
                    if m3: html_code = m3.group(1); Path(fp).write_text(html_code, encoding='utf-8'); iterations += 1
                else: break
            else: break
        
        result["iterations"] = iterations
        result["final_result"] = f"✅ **{task_name}** | 团队协作:{len(cr.get('results',{}))}个Agent | 迭代:{iterations}轮"
    
    return result

def get_status() -> dict:
    """并发引擎状态"""
    return {
        "status": "ready",
        "max_workers": 3,
        "mode": "thread_pool",
        "tools": ["run_concurrent", "run_team"]
    }
