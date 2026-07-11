"""深度研究引擎：搜索→抓取→分析→生成报告"""
from __future__ import annotations
import re, json, asyncio
from core.logging_config import get_logger
logger = get_logger("evo.researcher")

async def research(question: str) -> dict:
    """深度研究：搜索→抓取→LLM分析"""
    # 1. 单次搜索+抓取
    from modules.web_fetcher import search_and_fetch
    texts = []
    try:
        r = await asyncio.wait_for(search_and_fetch(question, count=3), timeout=30)
        if r and len(r) > 50:
            texts.append(r)
    except Exception as e:
        logger.warning(f"[RESEARCH] search failed: {e}")
    
    # 2. 去重
    seen = set()
    unique = []
    for t in texts:
        h = hash(t[:200])
        if h not in seen:
            seen.add(h)
            unique.append(t)
    
    # 3. LLM综合
    from api.agent_llm import call_llm
    ctx = "\n\n".join([f"[来源{i+1}] {t[:1500]}" for i,t in enumerate(unique) if t])
    prompt = f"""基于以下资料回答：{question}

资料：
{ctx or '（无搜索结果，请基于你的知识回答）'}

格式：
**核心结论：**
[概要]

**详细分析：**
[分点]

**信息来源：**
[标注来源编号]"""
    try:
        summary, _ = call_llm([{"role":"user","content":prompt}], timeout=30)
    except Exception as e:
        summary = f"分析异常: {e}"
    
    return {
        "success": True,
        "question": question,
        "sources": len(unique),
        "result": summary or "搜索无结果，请换关键词重试。\n\n" + "\n".join(unique[:3])
    }
