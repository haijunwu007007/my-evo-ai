"""深度研究引擎：搜索→抓取→分析→交叉验证→生成报告"""
from __future__ import annotations
import re, json, asyncio
from core.logging_config import get_logger
logger = get_logger("evo.researcher")

async def _search_fetch(query: str) -> str:
    """搜索+抓取正文"""
    from modules.web_fetcher import search_and_fetch
    try:
        return await search_and_fetch(query, count=5)
    except Exception as e:
        return f""

async def _llm_summarize(texts: list[str], question: str) -> str:
    """用LLM综合分析"""
    from api.agent_llm import call_llm
    ctx = "\n\n".join([f"[来源{i+1}] {t[:1500]}" for i,t in enumerate(texts) if t])
    prompt = f"""基于以下资料回答用户问题。要求：1)直接回答 2)引用来源编号 3)指出信息矛盾

问题：{question}

参考资料：
{ctx}

请用中文回答，格式：
**核心结论：**
[概要]

**详细分析：**
[分点论述，标注来源编号]

**信息来源：**
{chr(10).join([f"{i+1}. 来源{i+1}" for i in range(len(texts)) if texts[i]])}"""
    try:
        r, _ = call_llm([{"role":"user","content":prompt}], timeout=30)
        return r or "分析完成，请查看搜索结果。"
    except Exception as e:
        return f"分析异常: {e}"

async def research(question: str) -> dict:
    """执行深度研究"""
    # 1. 生成多角度搜索词
    queries = [question, f"{question} 分析", f"{question} 最新进展 2026"]
    
    # 2. 并行搜索+抓取
    all_texts = []
    results = await asyncio.gather(*[_search_fetch(q) for q in queries], return_exceptions=True)
    for r in results:
        if isinstance(r, str) and r and "搜索结果摘要" in r:
            all_texts.append(r)
    
    # 3. 去重
    seen = set()
    unique = []
    for t in all_texts:
        h = hash(t[:200])
        if h not in seen:
            seen.add(h)
            unique.append(t)
    
    # 4. LLM综合分析
    summary = await _llm_summarize(unique, question)
    
    return {
        "success": True,
        "question": question,
        "sources_count": len(unique),
        "analysis": summary or "搜索结果:\n" + "\n\n".join(unique[:3])
    }
