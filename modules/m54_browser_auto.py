"""AUTO-EVO-AI V0.1 — 浏览器自动化引擎（上市公司级）
# Grade: A

基于 Playwright 的浏览器 RPA 引擎，支持导航/截图/点击/文本提取/
表单填写/Cookie 管理/会话管理/PDF 导出/等待策略。
"""
__module_meta__ = {
    "id": "m54-browser-auto",
    "name": "Browser Automation Engine",
    "version": "V0.1",
    "group": "automation",
    "grade": "A",
    "tags": ["browser", "automation", "rpa", "scraping", "playwright"],
    "description": "企业级浏览器自动化引擎 — 导航/截图/点击/表单/会话/导出",
}
import time, uuid, logging, os, base64, asyncio
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (
    EnterpriseModule, ModuleStatus, HealthReport,
    CircuitBreakerMixin, RateLimiterMixin,
)

logger = logging.getLogger("evo.browser-auto")

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("[BrowserAuto] playwright 未安装，使用回退模式")
    # 尝试用 seleniumwire 或 requests-html 回退
    try:
        import requests
        FALLBACK_HTTP = True
    except ImportError:
        FALLBACK_HTTP = False


class BrowserAutomationEngine(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """企业级浏览器自动化引擎"""

    MODULE_ID = "m54-browser-auto"
    MODULE_NAME = "浏览器自动化引擎"
    VERSION = "v3.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._sessions: dict[str, dict] = {}
        self._default_timeout = int(config.get("timeout", 30000)) if config else 30000
        self._headless = bool(config.get("headless", True)) if config else True
        self._stats = {
            "pages_opened": 0,
            "screenshots": 0,
            "errors": 0,
            "started_at": time.time(),
        }

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        mode = "Playwright" if PLAYWRIGHT_AVAILABLE else "HTTP回退"
        logger.info("[BrowserAuto] 引擎就绪, 驱动=%s, timeout=%dms", mode, self._default_timeout)

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value,
            healthy=True,
            module_id=self.MODULE_ID,
            checks={
                "driver": "playwright" if PLAYWRIGHT_AVAILABLE else "http_fallback",
                "sessions": len(self._sessions),
                "pages_opened": self._stats["pages_opened"],
                "errors": self._stats["errors"],
            },
        )

    async def execute(self, action=None, params=None):
        if params is None:
            params = {}
        return await self._safe_execute(action, params, handler=self._dispatch_async)

    # ─── Playwright 浏览器管理 ──────────────────────────
    async def _ensure_browser(self) -> bool:
        """确保浏览器已启动"""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser and self._context:
            try:
                # 快速检测浏览器是否存活
                pages = self._context.pages
                _ = len(pages)
                return True
            except Exception:
                pass
        try:
            p = await async_playwright().start()
            self._browser = await p.chromium.launch(headless=self._headless, timeout=15000)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            logger.info("[BrowserAuto] 浏览器已启动 (headless=%s)", self._headless)
            return True
        except Exception as e:
            logger.error("[BrowserAuto] 启动浏览器失败: %s", e)
            self._stats["errors"] += 1
            return False

    async def _navigate_playwright(self, url: str, wait_until: str = "domcontentloaded",
                                    timeout: int = 0) -> dict:
        """Playwright 导航"""
        if not await self._ensure_browser():
            return {"success": False, "error": "浏览器不可用"}
        try:
            page = await self._context.new_page()
            to = timeout or self._default_timeout
            await page.goto(url, wait_until=wait_until, timeout=to)
            title = await page.title()
            session_id = uuid.uuid4().hex[:8]
            self._sessions[session_id] = {
                "url": url,
                "title": title,
                "page": page,
                "created_at": time.time(),
            }
            self._stats["pages_opened"] += 1
            logger.info("[BrowserAuto] 导航: %s → %s", url, title)
            return {
                "success": True,
                "session_id": session_id,
                "url": url,
                "title": title,
                "status_code": 200,
            }
        except Exception as e:
            self._stats["errors"] += 1
            return {"success": False, "error": f"导航失败: {e}"}

    # ─── HTTP 回退导航 ─────────────────────────────────
    def _navigate_http(self, url: str) -> dict:
        """HTTP 回退：用 requests 获取页面"""
        if not FALLBACK_HTTP:
            return {"success": False, "error": "无可用 HTTP 后端"}
        try:
            import requests
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"),
            })
            sid = uuid.uuid4().hex[:8]
            self._sessions[sid] = {
                "url": url,
                "status_code": resp.status_code,
                "html": resp.text[:50000],
                "created_at": time.time(),
            }
            return {
                "success": True,
                "session_id": sid,
                "url": url,
                "title": _extract_title(resp.text),
                "status_code": resp.status_code,
                "fallback": True,
            }
        except Exception as e:
            return {"success": False, "error": f"HTTP请求失败: {e}"}

    # ─── 分发器（异步） ─────────────────────────────────
    async def _dispatch_async(self, p: dict) -> dict:
        a = p.get("action", "status")

        try:
            # ─── 导航 ───
            if a == "navigate":
                url = p.get("url", "")
                if not url:
                    return {"success": False, "error": "url 必填"}
                if PLAYWRIGHT_AVAILABLE:
                    return await self._navigate_playwright(
                        url, p.get("wait_until", "domcontentloaded"), p.get("timeout", 0)
                    )
                return self._navigate_http(url)

            # ─── 截图 ───
            if a == "screenshot":
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid:
                    return {"success": False, "error": "无可用会话"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}

                if PLAYWRIGHT_AVAILABLE and "page" in sess:
                    try:
                        page: Page = sess["page"]
                        full = p.get("full_page", False)
                        img_bytes = await page.screenshot(full_page=full, type="png")
                        b64 = base64.b64encode(img_bytes).decode()
                        self._stats["screenshots"] += 1
                        return {
                            "success": True,
                            "screenshot": b64,
                            "format": "png",
                            "size_bytes": len(img_bytes),
                            "session_id": sid,
                        }
                    except Exception as e:
                        return {"success": False, "error": f"截图失败: {e}"}
                else:
                    # HTTP 回退：无法截图
                    return {"success": False, "error": "HTTP 回退模式不支持截图"}

            # ─── 点击 ───
            if a == "click":
                selector = p.get("selector", "")
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid:
                    return {"success": False, "error": "无可用会话"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}

                if PLAYWRIGHT_AVAILABLE and "page" in sess:
                    try:
                        page: Page = sess["page"]
                        await page.click(selector, timeout=self._default_timeout)
                        return {"success": True, "clicked": selector, "session_id": sid}
                    except Exception as e:
                        return {"success": False, "error": f"点击失败: {e}"}
                return {"success": False, "error": "HTTP 回退不支持点击"}

            # ─── 获取文本 ───
            if a == "get_text":
                selector = p.get("selector", "")
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid:
                    return {"success": False, "error": "无可用会话"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}

                if PLAYWRIGHT_AVAILABLE and "page" in sess:
                    try:
                        page: Page = sess["page"]
                        if selector:
                            elem = await page.query_selector(selector)
                            text = await elem.inner_text() if elem else ""
                        else:
                            text = await page.content()
                        return {"success": True, "text": text[:100000], "selector": selector,
                                "session_id": sid}
                    except Exception as e:
                        return {"success": False, "error": f"获取文本失败: {e}"}
                # HTTP 回退
                html = sess.get("html", "")
                if selector:
                    text = _extract_html_text(html, selector)
                else:
                    text = html[:100000]
                return {"success": True, "text": text, "selector": selector, "session_id": sid,
                        "fallback": True}

            # ─── 表单填写 ───
            if a == "fill":
                selector = p.get("selector", "")
                value = p.get("value", "")
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid or not selector:
                    return {"success": False, "error": "session_id 和 selector 必填"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}
                if not (PLAYWRIGHT_AVAILABLE and "page" in sess):
                    return {"success": False, "error": "Playwright 填表需要浏览器"}

                try:
                    page: Page = sess["page"]
                    await page.fill(selector, value, timeout=self._default_timeout)
                    return {"success": True, "filled": selector, "session_id": sid}
                except Exception as e:
                    return {"success": False, "error": f"填写失败: {e}"}

            # ─── 等待 ───
            if a == "wait":
                ms = p.get("ms", 1000)
                await asyncio.sleep(ms / 1000)
                return {"success": True, "waited_ms": ms}

            # ─── 获取页面标题 ───
            if a == "title":
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid:
                    return {"success": False, "error": "无可用会话"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}
                if PLAYWRIGHT_AVAILABLE and "page" in sess:
                    title = await sess["page"].title()
                else:
                    title = sess.get("title", "(unknown)")
                return {"success": True, "title": title, "session_id": sid}

            # ─── 会话管理 ───
            if a == "sessions":
                return {
                    "success": True,
                    "sessions": [
                        {"id": k, "url": v.get("url", ""), "title": v.get("title", ""),
                         "age": round(time.time() - v.get("created_at", time.time()), 1)}
                        for k, v in self._sessions.items()
                    ],
                }

            if a == "close_session":
                sid = p.get("session_id", "")
                if sid in self._sessions:
                    sess = self._sessions.pop(sid)
                    if PLAYWRIGHT_AVAILABLE and "page" in sess:
                        try:
                            await sess["page"].close()
                        except Exception:
                            pass
                    logger.info("[BrowserAuto] 关闭会话: %s", sid)
                    return {"success": True, "closed": sid}
                return {"success": False, "error": f"会话不存在: {sid}"}

            if a == "close_all":
                count = len(self._sessions)
                for sid, sess in list(self._sessions.items()):
                    if PLAYWRIGHT_AVAILABLE and "page" in sess:
                        try:
                            await sess["page"].close()
                        except Exception:
                            pass
                self._sessions.clear()
                logger.info("[BrowserAuto] 关闭所有会话: %d", count)
                return {"success": True, "closed_count": count}

            # ─── 状态 ───
            if a == "status":
                return {
                    "success": True,
                    "driver": "playwright" if PLAYWRIGHT_AVAILABLE else "http_fallback",
                    "sessions": len(self._sessions),
                    "pages_opened": self._stats["pages_opened"],
                    "screenshots": self._stats["screenshots"],
                    "errors": self._stats["errors"],
                    "uptime": round(time.time() - self._stats["started_at"], 1),
                }

            # ─── 截取完整页面（PDF） ───
            if a == "pdf":
                session_id = p.get("session_id", "")
                sid = session_id or (list(self._sessions.keys())[-1] if self._sessions else "")
                if not sid:
                    return {"success": False, "error": "无可用会话"}
                sess = self._sessions.get(sid)
                if not sess:
                    return {"success": False, "error": f"会话不存在: {sid}"}
                if not (PLAYWRIGHT_AVAILABLE and "page" in sess):
                    return {"success": False, "error": "Playwright 模式才支持 PDF"}

                try:
                    from playwright.async_api import Page
                    page: Page = sess["page"]
                    pdf_bytes = await page.pdf(format="A4")
                    b64 = base64.b64encode(pdf_bytes).decode()
                    return {"success": True, "pdf_base64": b64, "size_bytes": len(pdf_bytes),
                            "session_id": sid}
                except Exception as e:
                    return {"success": False, "error": f"PDF生成失败: {e}"}

            return {"success": False, "error": f"unknown_action: {a}"}

        except Exception as e:
            logger.error("[BrowserAuto] %s 失败: %s", a, e, exc_info=True)
            self._stats["errors"] += 1
            return {"success": False, "error": str(e)}

    async def shutdown(self) -> None:
        """关闭浏览器引擎，释放资源"""
        # 关闭所有页面
        for sid, sess in list(self._sessions.items()):
            if PLAYWRIGHT_AVAILABLE and "page" in sess:
                try:
                    await sess["page"].close()
                except Exception:
                    pass
        self._sessions.clear()

        # 关闭浏览器
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        self.status = ModuleStatus.STOPPED
        logger.info("[BrowserAuto] 引擎已关闭")


def _extract_title(html: str) -> str:
    """从 HTML 中提取标题"""
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else "(no title)"


def _extract_html_text(html: str, selector: str) -> str:
    """简易 HTML 文本提取（不使用浏览器时）"""
    import re
    if not html:
        return ""
    # 如果 selector 是标签名
    tag = selector.strip(".#[] ")
    pattern = f"<{tag}[^>]*>(.*?)</{tag}>"
    texts = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    if texts:
        return re.sub(r"<[^>]+>", "", texts[0]).strip()
    return html[:100000]


module_class = BrowserAutomationEngine
