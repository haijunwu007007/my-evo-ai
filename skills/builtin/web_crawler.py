"""网页爬虫技能 — crawl4ai 或 requests + bs4 兜底"""
import urllib.request, re
from html.parser import HTMLParser

skill_def = {
    "name": "web-crawler", "version": "1.0.0",
    "description": "AI 网页爬虫，抓取页面标题和正文",
    "author": "AUTO-EVO-AI", "category": "搜索", "icon": "🕷️",
    "tags": ["爬虫", "抓取", "网页"],
    "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}}
}

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self._skip = True
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self._skip = False
    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t: self.texts.append(t)
    def get_text(self):
        return '\n'.join(self.texts)

def execute(params, context=None):
    url = params.get("url", "")
    if not url:
        return {"title": "", "content": "", "error": "请提供网页 URL"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        title = ""
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        if m: title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        extractor = _TextExtractor()
        extractor.feed(html)
        content = extractor.get_text()[:5000]
        return {"title": title, "content": content}
    except Exception as e:
        logger = __import__('logging').getLogger('evo.crawler')
        logger.warning(f"抓取失败: {e}")
        return {"title": "", "content": "", "error": "抓取失败，请检查URL后重试"}
