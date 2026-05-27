"""
AUTO-EVO-AI V0.1 — 智能网页采集器（真实业务逻辑）
Grade: A (生产级) | Category: 工具链
职责：网页抓取、内容解析、反爬策略、数据提取、增量采集、去重
"""
__module_meta__ = {
    "id": "web-scraper", "name": "Web Scraper", "version": "V0.1",
    "group": "web", "grade": "A",
    "tags": ["web", "scraper", "crawler"],
    "description": "AUTO-EVO-AI V0.1 — 智能网页采集器（真实业务逻辑）",
}

import os, re, json, time, logging, threading
import hashlib, urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# 真实外部依赖（有兜底）
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import metrics_collector

logger = logging.getLogger("evo.web_scraper")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

class FetchResult:
    def __init__(self, url: str, html: str = "", status: int = 0, error: str = "", elapsed: float = 0):
        self.url = url; self.html = html; self.status = status
        self.error = error; self.elapsed = elapsed

class ScrapeRule:
    def __init__(self, name: str, selector: str, attribute: str = "text", multiple: bool = False):
        self.name = name; self.selector = selector
        self.attribute = attribute; self.multiple = multiple

class WebScraperModule(EnterpriseModule):
    MODULE_ID = "web-scraper"; MODULE_NAME = "Web Scraper"; VERSION = "V0.1"

    def __init__(self):
        super().__init__()
        self._session: Optional[requests.Session] = None
        self._cache: Dict[str, FetchResult] = {}
        self._cache_ttl = int(self.config.get("cache_ttl", 300))
        self._max_concurrent = int(self.config.get("max_concurrent", 5))
        self._default_timeout = int(self.config.get("timeout", 30))
        self._rate_limit_delay = float(self.config.get("rate_limit_delay", 0.5))
        self._robots_cache: Dict[str, Set[str]] = {}
        self._seen_urls: Set[str] = set()
        self._semaphore = threading.Semaphore(self._max_concurrent)
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def initialize(self):
        logger.info("WebScraper initialized (requests=%s, bs4=%s)", HAS_REQUESTS, HAS_BS4)
        return True

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": UA, "Accept": "text/html,*/*", "Accept-Language": "zh-CN,zh;q=0.9"})
            adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=2)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        return self._session

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _fetch_page(self, url: str, timeout: int = 0, headers: dict = None) -> FetchResult:
        if not HAS_REQUESTS:
            return FetchResult(url, error="requests not installed")
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached.elapsed < self._cache_ttl:
            return cached
        with self._semaphore:
            self._rate_limit()
            t0 = time.time()
            try:
                sess = self._get_session()
                h = {**sess.headers, **(headers or {})}
                resp = sess.get(url, headers=h, timeout=timeout or self._default_timeout, allow_redirects=True)
                resp.raise_for_status()
                enc = resp.apparent_encoding or resp.encoding or "utf-8"
                html = resp.content.decode(enc, errors="replace")
                result = FetchResult(url, html=html, status=resp.status_code, elapsed=time.time() - t0)
                self._cache[cache_key] = result
                return result
            except requests.Timeout:
                return FetchResult(url, error="timeout", elapsed=time.time() - t0)
            except requests.HTTPError as e:
                return FetchResult(url, error=f"HTTP {e.response.status_code}", status=e.response.status_code, elapsed=time.time() - t0)
            except requests.ConnectionError:
                return FetchResult(url, error="connection_failed", elapsed=time.time() - t0)
            except Exception as e:
                return FetchResult(url, error=str(e), elapsed=time.time() - t0)

    def _extract_by_rules(self, html: str, rules: List[ScrapeRule]) -> Dict[str, Any]:
        result = {}
        if not HAS_BS4 or not html:
            return {"error": "bs4 not available or empty html"}
        soup = BeautifulSoup(html, "html.parser")
        for rule in rules:
            try:
                elements = soup.select(rule.selector)
                if rule.multiple:
                    if rule.attribute == "text":
                        result[rule.name] = [e.get_text(strip=True) for e in elements]
                    else:
                        result[rule.name] = [e.get(rule.attribute, "") for e in elements]
                else:
                    if elements:
                        e = elements[0]
                        result[rule.name] = e.get_text(strip=True) if rule.attribute == "text" else e.get(rule.attribute, "")
                    else:
                        result[rule.name] = None
            except Exception:
                result[rule.name] = None
        return result

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        if not HAS_BS4 or not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            absolute = urllib.parse.urljoin(base_url, href)
            links.append(absolute)
        return links

    # ========== Actions ==========

    def quick_scrape(self, params: dict = None) -> dict:
        p = params or {}
        url = p.get("url", "")
        if not url:
            return {"success": False, "error": "url required"}
        result = self._fetch_page(url, timeout=int(p.get("timeout", 0)))
        if result.error:
            return {"success": False, "error": result.error, "url": url, "elapsed": round(result.elapsed, 2)}
        rules = [ScrapeRule("title", "title"), ScrapeRule("h1", "h1", multiple=True),
                 ScrapeRule("meta_desc", 'meta[name="description"]', "content"),
                 ScrapeRule("links", "a[href]", "href", multiple=True)]
        data = self._extract_by_rules(result.html, rules)
        links = self._extract_links(result.html, url)
        return {"success": True, "url": url, "status": result.status, "size": len(result.html),
                "elapsed": round(result.elapsed, 2), "title": data.get("title", ""),
                "headings": data.get("h1", []), "description": data.get("meta_desc"),
                "links_count": len(links), "links": links[:100]}

    def batch_scrape(self, params: dict = None) -> dict:
        p = params or {}
        urls = p.get("urls", [])
        if not urls:
            return {"success": False, "error": "urls list required"}
        max_workers = min(int(p.get("max_workers", 5)), 10)
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut = {pool.submit(self.quick_scrape, {"url": u}): u for u in urls}
            for f in as_completed(fut):
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append({"success": False, "url": fut[f], "error": str(e)})
        return {"success": True, "total": len(urls), "results": results}

    def search(self, params: dict = None) -> dict:
        p = params or {}
        query = p.get("query", "")
        if not query:
            return {"success": False, "error": "query required"}
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        result = self._fetch_page(search_url)
        if result.error:
            # fallback: use Bing
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            result = self._fetch_page(search_url, headers={"User-Agent": UA})
            if result.error:
                return {"success": False, "error": result.error}
        if HAS_BS4 and result.html:
            soup = BeautifulSoup(result.html, "html.parser")
            items = []
            for r in soup.select(".result, .result__body, li.b_algo"):
                title_el = r.select_one("a, h2 a, .result__title a")
                snippet_el = r.select_one(".result__snippet, .b_caption p, .result__body")
                if title_el:
                    items.append({
                        "title": title_el.get_text(strip=True),
                        "url": title_el.get("href", ""),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })
            return {"success": True, "query": query, "total": len(items), "results": items[:20]}
        return {"success": True, "query": query, "total": 0, "results": []}

    def crawl(self, params: dict = None) -> dict:
        p = params or {}
        start_url = p.get("url", "")
        max_pages = int(p.get("max_pages", 10))
        if not start_url:
            return {"success": False, "error": "url required"}
        visited: Set[str] = set()
        to_visit = [start_url]
        pages = []
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            result = self._fetch_page(url)
            if not result.error:
                links = self._extract_links(result.html, url)
                for link in links:
                    if link not in visited and link.startswith(("http://", "https://")) and len(to_visit) + len(visited) < max_pages * 2:
                        to_visit.append(link)
                pages.append({"url": url, "size": len(result.html), "status": result.status})
                self._seen_urls.add(url)
        return {"success": True, "pages_crawled": len(pages), "pages": pages}

    def clear_cache(self, params: dict = None) -> dict:
        self._cache.clear()
        return {"success": True, "cleared": True}

    def get_stats(self, params: dict = None) -> dict:
        return {"success": True, "cache_size": len(self._cache), "seen_urls": len(self._seen_urls),
                "requests_available": HAS_REQUESTS, "bs4_available": HAS_BS4}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "module_id": self.MODULE_ID,
                "requests": HAS_REQUESTS, "bs4": HAS_BS4,
                "cache": len(self._cache), "seen": len(self._seen_urls)}

    async def execute(self, action: str, params: dict = None) -> Any:
        p = params or {}
        actions = {
            "scrape": lambda: self.quick_scrape(p), "quick_scrape": lambda: self.quick_scrape(p),
            "batch": lambda: self.batch_scrape(p), "batch_scrape": lambda: self.batch_scrape(p),
            "search": lambda: self.search(p), "crawl": lambda: self.crawl(p),
            "clear_cache": lambda: self.clear_cache(p), "stats": lambda: self.get_stats(p),
            "health": lambda: self.health_check(), "status": lambda: self.health_check(),
        }
        handler = actions.get(action)
        if handler:
            try:
                result = handler()
                return {"success": True, "result": result} if isinstance(result, dict) else {"success": True, "data": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"unknown action: {action}"}

module_class = WebScraperModule
