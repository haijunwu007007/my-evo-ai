"""网页搜索技能 — 多引擎实时搜索（Bing / 备用）"""
import json, re, time

skill_def = {
    "name": "search-web", "version": "2.0.0",
    "description": "多引擎实时网页搜索（Bing 主引擎，中国可访问）",
    "author": "AUTO-EVO-AI", "category": "搜索", "icon": "🔍",
    "tags": ["搜索", "网页", "新闻", "查询"],
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "count": {"type": "integer"}}},
    "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}}
}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 垃圾域名黑名单
_SPAM_DOMAINS = {"jbuox.com","yyxw.com","jintian.yyxw.com","r.bing.com"}

def _is_spam(url, title):
    """检查是否为垃圾结果"""
    for d in _SPAM_DOMAINS:
        if d in url.lower():
            return True
    # 无实际标题的结果
    if not title or len(title) < 4:
        return True
    return False

def _fetch(url, timeout=10):
    """通用HTTP GET，返回文本"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

def _clean_title(title, url=""):
    """清洗标题：去除HTML标签、多余空格、换行"""
    t = re.sub(r'<[^>]+>', '', title)
    t = re.sub(r'\s+', ' ', t).strip()
    # 截断域名前缀（Bing有时把域名加到标题前）
    t = re.sub(r'^[a-z0-9.-]+\.[a-z]{2,}\s*[-|]\s*', '', t)
    # 去掉标题中嵌入的URL（Bing经常把URL当标题）
    t = re.sub(r'https?://\S+', '', t).strip()
    # 如果清洗后太短或像域名,用URL路径补充
    if len(t) < 10 and url:
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            path = p.path.replace('/',' ').replace('-',' ').replace('_',' ').strip()
            if path:
                t = (p.netloc.replace('www.','') + ' ' + path)[:80]
        except:
            pass
    return t[:120]

def _parse_bing(html):
    """从Bing HTML提取结果"""
    results = []
    # 方法1: b_algo 类
    blocks = re.findall(r'<li[^>]*class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
    for block in blocks:
        m = re.search(r'href="(https?://[^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
        if m:
            url = m.group(1).split('?')[0]  # 去掉追踪参数
            title = _clean_title(m.group(2), url)
            if not _is_spam(url, title):
                results.append({"title": title, "url": url, "snippet": ""})
    if results:
        return results
    # 方法2: 通用a标签（兜底）
    links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
    seen = set()
    for url, title in links:
        url = url.split('?')[0]
        title = _clean_title(title, url)
        if title and len(title) > 5 and url not in seen and "bing.com" not in url and "microsoft.com" not in url and not _is_spam(url, title):
            seen.add(url)
            results.append({"title": title, "url": url, "snippet": ""})
    return results

def _parse_duckduckgo(html):
    """从DDG HTML提取结果"""
    results = []
    links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
    seen = set()
    for url, title in links:
        title = _clean_title(title, url)
        if title and len(title) > 3 and url not in seen and not _is_spam(url, title):
            seen.add(url)
            results.append({"title": title[:100], "url": url, "snippet": ""})
    return results

def execute(params, context=None):
    query = params.get("query", "")
    count = int(params.get("count", 10))
    if not query:
        return {"results": [], "error": "请提供搜索关键词（query）"}

    results = []
    engine = ""

    # 1. Bing（cn，中国可访问）
    for retry in range(2):
        try:
            url = f"https://cn.bing.com/search?q={__import__('urllib').parse.quote(query)}&count=30"
            html = _fetch(url, timeout=12)
            if html:
                results = _parse_bing(html)
                if results:
                    engine = "bing"
                    break
        except Exception:
            pass
        time.sleep(0.5)

    # 2. DuckDuckGo 兜底
    if not results:
        try:
            import urllib.parse
            url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
            html = _fetch(url, timeout=8)
            if html:
                results = _parse_duckduckgo(html)
                if results:
                    engine = "duckduckgo"
        except Exception:
            pass

    return {"results": results[:count], "engine": engine}
