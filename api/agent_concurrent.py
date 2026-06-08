"""智能体 — 并发多Agent（Agent-Orchestrator 风格）"""
import json, time, asyncio, threading
from pathlib import Path

def run_concurrent_agents(msg, analysis, key, BASE, OUT, _LAST, _GENERATED_TOOLS):
    """并发执行：分析师 + 开发者并行，审查者等结果"""
    import concurrent.futures
    results = {}
    
    # 1. 分析师（串行，必须先完成）
    analyst_msgs = [
        {"role":"system","content":"你是系统分析师，负责拆解用户需求为可执行步骤。"},
        {"role":"user","content":f"需求：{msg[:200]}\n请输出：1.功能列表 2.技术栈 3.文件结构"}
    ]
    from api.agent_llm import call_llm
    analysis_result, _ = call_llm(analyst_msgs, None, key)
    
    # 2. 开发者 + 备选方案（并发）
    def dev_task():
        dev_msgs = [
            {"role":"system","content":"你是高级开发者，按分析师输出生成完整代码。"},
            {"role":"user","content":f"需求：{msg[:200]}\n分析：{(analysis_result or '')[:300]}\n请生成完整HTML文件，包含CSS和JS。"}
        ]
        r, _ = call_llm(dev_msgs, None, key)
        return ("dev", r)
    
    def alt_task():
        alt_msgs = [
            {"role":"system","content":"你是备用开发者，生成简化但可用的方案。"},
            {"role":"user","content":f"需求：{msg[:200]}\n生成简化版HTML。"}
        ]
        r, _ = call_llm(alt_msgs, None, key)
        return ("alt", r)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(dev_task)
        f2 = executor.submit(alt_task())
        done, _ = concurrent.futures.wait([f1, f2], timeout=60)
        
        for f in done:
            name, result = f.result()
            results[name] = result
    
    # 3. 选最佳结果（优先dev，超200字）
    code_result = results.get("dev") or results.get("alt") or ""
    if len((code_result or "")) < 200:
        code_result = results.get("alt") or code_result
    
    # 4. 沙箱验证 + 保存
    from api.agent_sandbox import sandbox
    issues = sandbox.validate_html(code_result or "")
    
    if len((code_result or "").strip()) > 200:
        fn = f"app_{int(time.time())}.html"
        fp = str(OUT / "apps" / fn)
        Path(fp).parent.mkdir(exist_ok=True)
        Path(fp).write_text(code_result, encoding='utf-8')
        _LAST["url"] = f"/output/apps/{fn}"
        _LAST["time"] = time.time()
        _LAST["name"] = msg[:30]
        
        warn = f"\n⚠️ 代码警告: {'; '.join(issues[:3])}" if issues else ""
        return f"✅ **{msg[:30]}**\n[📄 打开]({_LAST['url']}){warn}"
    
    return f"⚠️ 生成失败，请重试。分析师输出：{(analysis_result or '')[:100]}"

def run_with_experience(msg, key, BASE, OUT, _LAST, _GENERATED_TOOLS):
    """带经验记忆的执行（MemOS风格）"""
    from api.agent_memory import AgentMemory
    mem = AgentMemory(BASE / "data" / "agent_memory.db")
    
    # 查找相似历史经验
    similar = mem.search_experience(msg, top_k=3)
    experience_hint = ""
    if similar:
        experience_hint = "\n【历史经验】\n" + "\n".join(
            f"- {s['pattern']}: {s['solution'][:100]}" for s in similar[:3]
        )
    
    # 执行
    result = run_concurrent_agents(msg, experience_hint, key, BASE, OUT, _LAST, _GENERATED_TOOLS)
    
    # 累积经验
    if _LAST.get("url"):
        mem.add_experience(msg[:50], f"成功生成：{_LAST.get('url','')}", success=True)
    
    return result
