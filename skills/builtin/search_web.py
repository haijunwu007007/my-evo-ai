"""网页搜索技能 — DuckDuckGo 实时搜索"""
import json, urllib.request, urllib.parse
from html.parser import HTMLParser

skill_def = {
    "name": "search-web", "version": "1.0.0",
    "description": "DuckDuckGo 实时网页搜索",
    "author": "AUTO-EVO-AI", "category": "搜索", "icon": "🔍",
    "tags": ["搜索", "网页", "新闻", "查询"],
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "count": {"type": "integer"}}},
    "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}}
}

def execute(params, context=None):
    query = params.get("query", "")
    count = int(params.get("count", 5))
    if not query:
        return {"results": [], "error": "请提供搜索关键词（query）"}

    results = []
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # 简单解析搜索结果链接
        import re
        links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>', html, re.DOTALL)
        if not links:
            links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        seen = set()
        for url, title in links:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if title and url not in seen and len(results) < count:
                seen.add(url)
                results.append({"title": title[:100], "url": url, "snippet": ""})
    except Exception as e:
        return {"results": [], "error": f"搜索失败：{e}"}

    return {"results": results}
