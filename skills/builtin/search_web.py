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
    engine = ""

    # 尝试 DuckDuckGo
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
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
        if results:
            engine = "duckduckgo"
    except Exception:
        pass

    # 兜底：Bing 搜索（中国可访问）
    if not results:
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            import re
            links = re.findall(r'<li class="b_algo">.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for url, title in links:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if title and len(results) < count:
                    results.append({"title": title[:100], "url": url, "snippet": ""})
            if results:
                engine = "bing"
        except Exception:
            pass

    return {"results": results, "engine": engine}
