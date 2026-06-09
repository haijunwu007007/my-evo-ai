"""ScrapeGraphAI — AI驱动智能爬虫（一句话爬取结构化数据）"""
import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def ai_scrape(url: str = "", prompt: str = "", source_type: str = "url") -> dict:
    """AI智能爬取网页/文档
    Args:
        url: 目标网址
        prompt: 自然语言描述要提取什么（如"提取所有产品名称和价格"）
        source_type: 数据源类型（url/html/xml/json）
    Returns:
        {"success": bool, "data": dict|list, "error": str}
    """
    try:
        from scrapegraphai.graphs import SmartScraperGraph
    except ImportError:
        return {"success": False, "error": "scrapegraphai 未安装。运行: pip install scrapegraphai"}

    if not url:
        return {"success": False, "error": "缺少 url 参数"}
    if not prompt:
        prompt = "提取页面上所有有用信息"

    # 配置 LLM (优先环境变量)
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ZHIPU_API_KEY", "")
    model = "gpt-4" if os.environ.get("OPENAI_API_KEY") else "glm-4-flash"

    graph_config = {
        "llm": {
            "model": model,
            "api_key": api_key,
            "temperature": 0.1,
        },
        "verbose": False,
        "headless": True,
    }

    try:
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=graph_config
        )
        result = scraper.run()
        return {"success": True, "data": result, "url": url, "prompt": prompt}
    except Exception as e:
        return {"success": False, "error": f"爬取失败: {e}"}

def ai_scrape_multi(urls: list, prompt: str = "") -> dict:
    """批量爬取多个页面"""
    results = []
    for url in urls:
        r = ai_scrape(url=url, prompt=prompt)
        results.append({"url": url, "ok": r["success"], "data": r.get("data", r.get("error",""))})
    return {"success": True, "total": len(results), "results": results}
