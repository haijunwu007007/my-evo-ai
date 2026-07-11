"""网页内容自动抓取+提炼 — 输入URL或关键词→抓取网页→提取正文→LLM总结"""
from __future__ import annotations
import re, json, os, html as _html
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.web_fetcher")

_HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def _clean_html(text: str) -> str:
    """剥HTML标签，只保留可见文本"""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = _html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    # 去广告/导航常见关键词行
    lines = text.split('\n')
    _skip = {'广告','推广','导航','登录','注册','关于我们','联系我们','免责声明'}
    clean = []
    for l in lines:
        l = l.strip()
        if not l or len(l) < 6: continue
        if any(s in l for s in _skip) and len(l) < 20: continue
        clean.append(l)
    return '\n'.join(clean[:200])  # 最多200行

class WebFetcher:
    """网页抓取器 — 抓取+提炼一条龙"""
    
    def status(self) -> dict:
        import httpx
        return {"available": True, "engine": "httpx"}
    
    def execute(self, action: str, params: dict = None) -> dict:
        if action == "status":
            return self.status()
        elif action == "fetch":
            url = (params or {}).get("url", "")
            query = (params or {}).get("query", "")
            return self._fetch(url, query)
        return {"success": False, "error": f"未知动作: {action}"}
    
    def _fetch(self, url: str = "", query: str = "") -> dict:
        """抓取网页内容"""
        async def _run():
            import httpx
            try:
                async with httpx.AsyncClient(timeout=15, headers=_HEADERS, verify=False) as c:
                    # 有URL直接抓
                    if url:
                        resp = await c.get(url, follow_redirects=True)
                        if resp.status_code != 200:
                            return {"success": False, "error": f"HTTP {resp.status_code}"}
                        raw = resp.text
                    # 有关键词先搜再抓第一个结果
                    elif query:
                        sq = f"https://www.baidu.com/s?wd={query}"
                        resp = await c.get(sq, follow_redirects=True)
                        if resp.status_code != 200:
                            return {"success": False, "error": f"搜索失败 {resp.status_code}"}
                        raw = resp.text
                    else:
                        return {"success": False, "error": "需要URL或关键词"}
                    
                    title_m = re.search(r'<title>([^<]+)</title>', raw, re.IGNORECASE)
                    title = title_m.group(1).strip() if title_m else ""
                    body = _clean_html(raw)
                    
                    return {
                        "success": True,
                        "title": title,
                        "url": url or f"搜索: {query}",
                        "content": body[:8000],  # 限制8KB
                        "length": len(body),
                    }
            except Exception as e:
                logger.warning(f"[WEB_FETCH] 抓取失败: {e}")
                return {"success": False, "error": str(e)}
        
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_run())
        except Exception as e:
            logger.error(f"[WEB_FETCH] 异常: {e}")
            return {"success": False, "error": str(e)}

# 快捷函数
def register() -> dict:
    return {"name": "web_fetcher", "version": "1.0", "actions": ["status", "fetch"]}
