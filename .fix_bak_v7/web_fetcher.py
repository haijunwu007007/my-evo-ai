"""网页内容自动抓取+提炼"""
from __future__ import annotations
import re, httpx, html as _html

async def fetch(url: str, timeout: int = 10) -> dict:
    """抓取网页并提取正文, 返回 {title, text, url}"""
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False,
                                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"} if not url.startswith("https://top.baidu.com") else None) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return {"title": "", "text": f"请求失败: HTTP {r.status_code}", "url": url}
            raw = r.text
            # 提取 title
            title = ""
            mt = re.search(r'<title[^>]*>([^<]+)', raw, re.I)
            if mt: title = mt.group(1).strip()
            # 移除 script/style
            cleaned = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', raw, flags=re.I|re.S)
            # 提取正文
            bodies = ['<div class="c-single-text-ellipsis', '<article', '<div class="content"', '<div id="content"', '<div class="main"']
            text = ""
            for b_tag in bodies:
                idx = cleaned.find(b_tag)
                if idx >= 0:
                    end = cleaned.find('</div>', idx)
                    if end < 0: end = min(idx + 3000, len(cleaned))
                    snippet = cleaned[idx:end+6]
                    text = re.sub(r'<[^>]+>', ' ', snippet)
                    text = _html.unescape(re.sub(r'\s+', ' ', text)).strip()
                    break
            if not text or len(text) < 20:
                # Fallback: grab all text from body
                body_match = re.search(r'<body[^>]*>(.*?)</body>', cleaned, re.I|re.S)
                if body_match:
                    text = re.sub(r'<[^>]+>', ' ', body_match.group(1))
                    text = _html.unescape(re.sub(r'\s+', ' ', text)).strip()[:2000]
            if not text:
                text = raw[:500]
            lines = [l.strip() for l in text.split('
') if l.strip() and len(l.strip()) > 2]
            text = '
'.join(lines[:50])
            return {"title": title[:200], "text": text[:3000], "url": url}
    except Exception as e:
        return {"title": "", "text": f"抓取失败: {e}", "url": url}

async def search_and_fetch(query: str, count: int = 3) -> str:
    """搜索+自动抓取第一条结果, 返回内容摘要"""
    from api.routes.routes_smart_chat import _execute_search
    result = await _execute_search(query, count)
    if not result:
        return ""
    # 从搜索结果中提取URL
    urls = re.findall(r'https?://[^\s\)]+', result)
    if not urls:
        return result[:500]
    # 抓取第一个有效URL
    texts = []
    for url in urls[:3]:
        if any(ext in url for ext in ['.jpg', '.png', '.gif', '.pdf', '.mp4']):
            continue
        r = await fetch(url)
        if r.get("text") and len(r["text"]) > 50:
            texts.append(f"📰 {r['title']}
{r['text'][:800]}")
            if texts: break
    if texts:
        return "📊 **搜索结果摘要**

" + "

---

".join(texts[:2])
    return result[:500]
