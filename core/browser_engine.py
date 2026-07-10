"""
AUTO-EVO-AI V0.1 — 浏览器自动化引擎
====================================
上市公司生产级设计：

核心能力:
  1. Playwright主引擎 — Chromium/Firefox/WebKit三引擎
  2. Selenium备用引擎 — 兼容老项目
  3. 页面截图 — 全页/元素/视口
  4. 元素操作 — 点击/输入/选择/悬停/拖拽
  5. 表单填充 — 智能识别并填写表单
  6. 页面导航 — 前进/后退/刷新/等待
  7. 数据提取 — 文本/表格/链接/图片/属性
  8. JavaScript执行 — 注入自定义脚本
  9. 网络拦截 — 请求/响应监控与修改
  10. Cookie管理 — 导入/导出/清除
  11. 文件下载 — 自动管理下载目录
  12. 任务编排 — 多步骤自动化脚本

使用方式:
  from core.browser_engine import BrowserEngine

  engine = BrowserEngine()
  await engine.launch()
  page = await engine.goto("https://example.com")
  await engine.screenshot(page, "example.png")
  await engine.click(page, "#submit-btn")
  await engine.fill(page, "#name", "Hello")
  data = await engine.extract(page, "table")
  await engine.close()

依赖: playwright (pip install playwright && playwright install chromium)
     selenium (pip install selenium, 可选备用)
"""

import os
import re
import json
import time
import asyncio
from core.logging_config import get_logger
import hashlib
import tempfile
import base64
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = get_logger("evo.browser_engine")


# ═══════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════

class BrowserType(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    SELENIUM_CHROME = "selenium_chrome"


class EngineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class BrowserTask:
    """自动化任务"""
    id: str
    name: str
    steps: list[dict] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"
    result: Any = None
    error: str = ""
    created_at: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class ExtractedData:
    """页面提取结果"""
    url: str = ""
    title: str = ""
    text: str = ""
    links: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ScreenshotResult:
    """截图结果"""
    path: str = ""
    base64: str = ""
    width: int = 0
    height: int = 0
    element_rect: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════
# Playwright引擎
# ═══════════════════════════════════════════════════

class PlaywrightEngine:
    """Playwright浏览器自动化引擎"""

    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self.headless = headless
        self.browser_type = browser_type
        self.status = EngineStatus.CLOSED
        self._downloads_dir = tempfile.mkdtemp(prefix="evo_browser_dl_")
        self._network_log: list[dict] = []
        self._screenshot_dir = tempfile.mkdtemp(prefix="evo_browser_ss_")

    async def launch(self) -> dict:
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()

            launcher = {
                "chromium": self._playwright.chromium,
                "firefox": self._playwright.firefox,
                "webkit": self._playwright.webkit,
            }.get(self.browser_type, self._playwright.chromium)

            self._browser = await launcher.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )

            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                accept_downloads=True,
            )

            self._page = await self._context.new_page()

            # 网络监控
            self._page.on("response", self._on_response)

            self.status = EngineStatus.RUNNING
            return {"success": True, "browser": self.browser_type, "headless": self.headless}

        except ImportError:
            return {"success": False, "error": "playwright未安装: pip install playwright && playwright install chromium"}
        except Exception as e:
            self.status = EngineStatus.ERROR
            return {"success": False, "error": str(e)}

    def _on_response(self, response):
        """网络响应监控"""
        try:
            self._network_log.append({
                "url": response.url[:200],
                "status": response.status,
                "timestamp": time.time(),
            })
            if len(self._network_log) > 1000:
                self._network_log = self._network_log[-500:]
        except Exception as _e:
            logger.warning(f"error: {_e}")

    async def close(self):
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as _e:
            logger.warning(f"error: {_e}")
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self.status = EngineStatus.CLOSED

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> dict:
        """导航到URL"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            response = await self._page.goto(url, wait_until=wait_until, timeout=timeout)
            title = await self._page.title()
            return {
                "success": True,
                "url": self._page.url,
                "title": title,
                "status": response.status if response else 0,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self, selector: str = "", full_page: bool = False,
                          path: str = "") -> ScreenshotResult:
        """截图"""
        if not self._page:
            return ScreenshotResult()

        try:
            if selector:
                element = await self._page.wait_for_selector(selector, timeout=5000)
                if not element:
                    return ScreenshotResult()
                buf = await element.screenshot()
                rect = await element.bounding_box()
                result = ScreenshotResult(
                    base64=base64.b64encode(buf).decode(),
                    element_rect=rect or {},
                    width=rect["width"] if rect else 0,
                    height=rect["height"] if rect else 0,
                )
            else:
                buf = await self._page.screenshot(full_page=full_page)
                result = ScreenshotResult(
                    base64=base64.b64encode(buf).decode(),
                    width=1920,
                    height=1080,
                )

            if path:
                full_path = os.path.join(self._screenshot_dir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                actual_path = full_path if not os.path.isdir(os.path.dirname(full_path) or full_path) else os.path.join(full_path, f"ss_{int(time.time())}.png")
                with open(actual_path, "wb") as f:
                    f.write(buf)
                result.path = actual_path

            return result
        except Exception as e:
            logger.error(f"[Browser] 截图失败: {e}")
            return ScreenshotResult()

    async def click(self, selector: str, timeout: int = 5000) -> dict:
        """点击元素"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._page.click(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": f"点击 {selector} 失败: {e}"}

    async def fill(self, selector: str, value: str, timeout: int = 5000) -> dict:
        """填写输入框"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._page.fill(selector, value, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": f"填写 {selector} 失败: {e}"}

    async def self_healing_click(self, text: str, timeout: int = 15000) -> dict:
        """自愈点击 — 语义匹配代替CSS选择器（页面结构变化仍可工作）"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        strategies = [
            f'text="{text}"', f'[aria-label="{text}"]', f'[placeholder="{text}"]',
            f'button:has-text("{text}")', f'a:has-text("{text}")',
            f'//*[contains(text(), "{text}")]',
        ]
        for sel in strategies:
            try:
                el = await self._page.wait_for_selector(sel, timeout=3000)
                if el: await el.click(); return {"success":True,"action":"heal_click","match":sel[:40],"text":text}
            except: pass
        return {"success":False,"error":f"自愈点击失败: {text}"}

    async def self_healing_fill(self, label: str, value: str) -> dict:
        """自愈填表 — 通过label/placeholder匹配输入框"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        strategies = [
            f'input[aria-label="{label}"]', f'input[placeholder="{label}"]',
            f'textarea[aria-label="{label}"]', f'textarea[placeholder="{label}"]',
            f'label:has-text("{label}") > input',
            f'//label[contains(text(), "{label}")]/following::input[1]',
        ]
        for sel in strategies:
            try:
                el = await self._page.wait_for_selector(sel, timeout=2000)
                if el: await el.fill(value); return {"success":True,"action":"heal_fill","match":sel[:40],"label":label}
            except: pass
        return {"success":False,"error":f"自愈填表失败: {label}"}

    async def type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        """模拟键盘输入（逐字符）"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._page.type(selector, text, delay=delay)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def select_option(self, selector: str, value: str = None, label: str = None) -> dict:
        """选择下拉选项"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            kwargs = {}
            if value:
                kwargs["value"] = value
            if label:
                kwargs["label"] = label
            await self._page.select_option(selector, **kwargs)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def hover(self, selector: str) -> dict:
        """悬停"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._page.hover(selector)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str = "Enter") -> dict:
        """按键"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._page.keyboard.press(key)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> dict:
        """等待元素出现"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            el = await self._page.wait_for_selector(selector, timeout=timeout)
            return {"success": bool(el), "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def evaluate(self, script: str) -> Any:
        """执行JavaScript"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            result = await self._page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_content(self) -> dict:
        """获取页面内容"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            title = await self._page.title()
            url = self._page.url
            content = await self._page.content()
            text = await self._page.inner_text("body")
            return {
                "success": True,
                "url": url,
                "title": title,
                "text": text[:50000],  # 截断
                "html_length": len(content),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_tables(self) -> list[list[list[str]]]:
        """提取页面所有表格"""
        if not self._page:
            return []
        try:
            return await self._page.evaluate("""() => {
                const tables = [];
                document.querySelectorAll('table').forEach(table => {
                    const rows = [];
                    table.querySelectorAll('tr').forEach(tr => {
                        const cells = [];
                        tr.querySelectorAll('th, td').forEach(cell => {
                            cells.push(cell.textContent.trim());
                        });
                        if (cells.length > 0) rows.push(cells);
                    });
                    if (rows.length > 0) tables.push(rows);
                });
                return tables;
            }""")
        except Exception:
            return []

    async def extract_links(self) -> list[dict]:
        """提取页面所有链接"""
        if not self._page:
            return []
        try:
            return await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent.trim().substring(0, 100),
                    href: a.href,
                })).filter(l => l.href && !l.href.startsWith('javascript:'));
            }""")
        except Exception:
            return []

    async def extract_images(self) -> list[dict]:
        """提取页面所有图片"""
        if not self._page:
            return []
        try:
            return await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('img')).map(img => ({
                    src: img.src,
                    alt: (img.alt || '').substring(0, 100),
                    width: img.naturalWidth || 0,
                    height: img.naturalHeight || 0,
                })).filter(i => i.src);
            }""")
        except Exception:
            return []

    async def extract_forms(self) -> list[dict]:
        """提取页面表单结构"""
        if not self._page:
            return []
        try:
            return await self._page.evaluate("""() => {
                const forms = [];
                document.querySelectorAll('form').forEach((form, i) => {
                    const fields = [];
                    form.querySelectorAll('input, textarea, select').forEach(el => {
                        fields.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || '',
                            name: el.name || '',
                            id: el.id || '',
                            placeholder: el.placeholder || '',
                        });
                    });
                    forms.push({
                        index: i,
                        action: form.action || '',
                        method: (form.method || 'GET').toUpperCase(),
                        fields: fields,
                    });
                });
                return forms;
            }""")
        except Exception:
            return []

    async def auto_fill_form(self, form_index: int = 0, data: dict[str, str] = None) -> dict:
        """自动填写表单"""
        if not self._page or not data:
            return {"success": False, "error": "参数无效"}
        try:
            filled = 0
            skipped = 0
            for field_name, value in data.items():
                # 尝试多种选择器
                selectors = [
                    f"form:nth-of-type({form_index + 1}) [name='{field_name}']",
                    f"form:nth-of-type({form_index + 1}) #{field_name}",
                    f"[name='{field_name}']",
                    f"#{field_name}",
                    f"[placeholder*='{field_name}']",
                ]
                filled_field = False
                for sel in selectors:
                    try:
                        el = await self._page.query_selector(sel)
                        if el:
                            tag = await el.evaluate("el => el.tagName.toLowerCase()")
                            el_type = await el.evaluate("el => el.type || ''")
                            if tag == "select":
                                await self._page.select_option(sel, label=value)
                            elif el_type == "checkbox":
                                if value.lower() in ("true", "1", "yes"):
                                    await el.check()
                            elif el_type == "radio":
                                await self._page.click(f"{sel}[value='{value}']")
                            else:
                                await self._page.fill(sel, str(value))
                            filled += 1
                            filled_field = True
                            break
                    except Exception:
                        continue
                if not filled_field:
                    skipped += 1
            return {"success": True, "filled": filled, "skipped": skipped}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_cookies(self) -> list[dict]:
        """获取当前Cookie"""
        if not self._context:
            return []
        try:
            return await self._context.cookies()
        except Exception:
            return []

    async def set_cookies(self, cookies: list[dict]) -> dict:
        """设置Cookie"""
        if not self._context:
            return {"success": False, "error": "浏览器未启动"}
        try:
            await self._context.add_cookies(cookies)
            return {"success": True, "count": len(cookies)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def network_log(self) -> list[dict]:
        """获取网络请求日志"""
        return self._network_log[-100:]

    async def scroll_to(self, position: str = "bottom", selector: str = "") -> dict:
        """滚动页面"""
        if not self._page:
            return {"success": False, "error": "浏览器未启动"}
        try:
            if selector:
                await self._page.evaluate(f"""
                    document.querySelector('{selector}').scrollIntoView({{behavior: 'smooth', block: 'center'}});
                """)
            elif position == "bottom":
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif position == "top":
                await self._page.evaluate("window.scrollTo(0, 0)")
            else:
                await self._page.evaluate(f"window.scrollBy(0, {position})")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_info(self) -> dict:
        """获取当前页面状态"""
        if not self._page:
            return {"status": "closed"}
        try:
            title = await self._page.title()
            url = self._page.url
            return {
                "status": self.status.value,
                "url": url,
                "title": title,
                "browser": self.browser_type,
                "headless": self.headless,
            }
        except Exception:
            return {"status": self.status.value}


# ═══════════════════════════════════════════════════
# Selenium备用引擎
# ═══════════════════════════════════════════════════

class SeleniumEngine:
    """Selenium浏览器引擎 — 备用"""

    def __init__(self, headless: bool = True):
        self._driver = None
        self.headless = headless
        self.status = EngineStatus.CLOSED
        self._screenshot_dir = tempfile.mkdtemp(prefix="evo_browser_ss_")

    def launch(self) -> dict:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            if self.headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")

            self._driver = webdriver.Chrome(options=opts)
            self.status = EngineStatus.RUNNING
            return {"success": True, "browser": "selenium_chrome", "headless": self.headless}
        except ImportError:
            return {"success": False, "error": "selenium未安装"}
        except Exception as e:
            self.status = EngineStatus.ERROR
            return {"success": False, "error": str(e)}

    def close(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception as _e:
                logger.warning(f"error: {_e}")
        self._driver = None
        self.status = EngineStatus.CLOSED

    def goto(self, url: str, timeout: int = 30) -> dict:
        if not self._driver:
            return {"success": False, "error": "浏览器未启动"}
        try:
            self._driver.set_page_load_timeout(timeout)
            self._driver.get(url)
            return {"success": True, "url": self._driver.current_url, "title": self._driver.title}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def screenshot(self, path: str = "") -> ScreenshotResult:
        if not self._driver:
            return ScreenshotResult()
        try:
            buf = self._driver.get_screenshot_as_png()
            result = ScreenshotResult(
                base64=base64.b64encode(buf).decode(),
                width=1920,
                height=1080,
            )
            if path:
                full_path = os.path.join(self._screenshot_dir, path)
                os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(buf)
                result.path = full_path
            return result
        except Exception as e:
            return ScreenshotResult()

    def click(self, selector: str) -> dict:
        if not self._driver:
            return {"success": False, "error": "浏览器未启动"}
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            el = WebDriverWait(self._driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            el.click()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fill(self, selector: str, value: str) -> dict:
        if not self._driver:
            return {"success": False, "error": "浏览器未启动"}
        try:
            from selenium.webdriver.common.by import By
            el = self._driver.find_element(By.CSS_SELECTOR, selector)
            el.clear()
            el.send_keys(value)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_content(self) -> dict:
        if not self._driver:
            return {"success": False, "error": "浏览器未启动"}
        try:
            return {
                "success": True,
                "url": self._driver.current_url,
                "title": self._driver.title,
                "text": (self._driver.find_element("tag name", "body").text or "")[:50000],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
# 浏览器引擎管理器
# ═══════════════════════════════════════════════════

class BrowserEngine:
    """
    浏览器自动化统一入口

    支持两种后端:
    - Playwright (推荐, 异步, 功能全)
    - Selenium (备用, 同步, 兼容性好)

    使用:
        engine = BrowserEngine()
        await engine.launch()  # 自动选Playwright, 不可用则Selenium
        await engine.goto("https://example.com")
        ss = await engine.screenshot()
        await engine.close()
    """

    def __init__(self, engine_type: str = "auto", headless: bool = True):
        self._engine = None
        self._engine_type = engine_type
        self._headless = headless
        self._tasks: dict[str, BrowserTask] = {}

    async def launch(self, engine_type: str = "", headless: bool = None) -> dict:
        """启动浏览器引擎"""
        engine_type = engine_type or self._engine_type
        headless = headless if headless is not None else self._headless

        if engine_type == "auto":
            # 优先Playwright, 不可用回退Selenium
            try:
                import playwright.async_api
                engine_type = "playwright"
            except ImportError:
                try:
                    import selenium
                    engine_type = "selenium"
                except ImportError:
                    return {"success": False, "error": "无可用浏览器引擎: pip install playwright selenium"}

        if engine_type == "playwright":
            self._engine = PlaywrightEngine(headless=headless)
            result = await self._engine.launch()
        elif engine_type == "selenium":
            self._engine = SeleniumEngine(headless=headless)
            result = self._engine.launch()
        else:
            return {"success": False, "error": f"未知引擎类型: {engine_type}"}

        if result.get("success"):
            self._engine_type = engine_type
            logger.info(f"[Browser] {engine_type} 引擎启动成功")
        return result

    async def close(self):
        """关闭浏览器"""
        if self._engine:
            if isinstance(self._engine, PlaywrightEngine):
                await self._engine.close()
            else:
                self._engine.close()
        self._engine = None

    async def _not_launched(self, *args, **kwargs):
        return {"success": False, "error": "浏览器未启动，请先调用 POST /api/browser/launch"}

    def __getattr__(self, name):
        """代理所有方法到当前引擎"""
        if name.startswith("_"):
            raise AttributeError(name)
        if self._engine and hasattr(self._engine, name):
            attr = getattr(self._engine, name)
            if callable(attr):
                return attr
            return attr
        # 引擎未启动时返回友好错误而不是抛异常
        return self._not_launched

    async def execute_task(self, task: BrowserTask) -> BrowserTask:
        """执行自动化任务脚本"""
        task.status = "running"
        task.started_at = time.time()
        results = []

        for i, step in enumerate(task.steps):
            task.current_step = i
            action = step.get("action", "")
            params = step.get("params", {})
            step_result = {"step": i, "action": action}

            try:
                if action == "goto":
                    r = await self.goto(params.get("url", ""), timeout=params.get("timeout", 30000))
                    step_result.update(r)
                elif action == "screenshot":
                    r = await self.screenshot(selector=params.get("selector", ""), full_page=params.get("full_page", False))
                    step_result["base64_length"] = len(r.base64) if r.base64 else 0
                    step_result["success"] = bool(r.base64)
                elif action == "click":
                    r = await self.click(params.get("selector", ""))
                    step_result.update(r)
                elif action == "fill":
                    r = await self.fill(params.get("selector", ""), params.get("value", ""))
                    step_result.update(r)
                elif action == "wait":
                    r = await self.wait_for_selector(params.get("selector", ""), timeout=params.get("timeout", 10000))
                    step_result.update(r)
                elif action == "evaluate":
                    r = await self.evaluate(params.get("script", ""))
                    step_result.update(r)
                elif action == "scroll":
                    r = await self.scroll_to(params.get("position", "bottom"))
                    step_result.update(r)
                elif action == "press":
                    r = await self.press_key(params.get("key", "Enter"))
                    step_result.update(r)
                elif action == "hover":
                    r = await self.hover(params.get("selector", ""))
                    step_result.update(r)
                elif action == "extract_tables":
                    tables = await self.extract_tables()
                    step_result["tables_count"] = len(tables)
                    step_result["success"] = True
                elif action == "sleep":
                    await asyncio.sleep(params.get("seconds", 1))
                    step_result["success"] = True
                elif action == "auto_fill":
                    r = await self.auto_fill_form(params.get("form_index", 0), params.get("data", {}))
                    step_result.update(r)
                else:
                    step_result["success"] = False
                    step_result["error"] = f"未知action: {action}"

                results.append(step_result)

                # 如果某步失败，可配置是否继续
                if not step_result.get("success") and not step.get("continue_on_error", True):
                    task.status = "failed"
                    task.error = step_result.get("error", "步骤失败")
                    task.result = results
                    task.finished_at = time.time()
                    return task

            except Exception as e:
                step_result["success"] = False
                step_result["error"] = str(e)
                results.append(step_result)
                task.status = "failed"
                task.error = str(e)
                task.result = results
                task.finished_at = time.time()
                return task

        task.status = "completed"
        task.result = results
        task.finished_at = time.time()
        return task

    async def get_status(self) -> dict:
        """获取引擎状态"""
        if not self._engine:
            return {"status": "closed", "engine": "none"}
        info = await self._engine.get_page_info() if hasattr(self._engine, "get_page_info") else {}
        return {
            "status": info.get("status", self._engine.status.value if hasattr(self._engine, "status") else "unknown"),
            "engine": self._engine_type,
            **info,
        }


# ═══════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════

_browser_engine: BrowserEngine | None = None


async def get_browser_engine() -> BrowserEngine:
    """获取全局浏览器引擎单例"""
    global _browser_engine
    if _browser_engine is None:
        _browser_engine = BrowserEngine()
    return _browser_engine


async def launch_browser(headless: bool = True) -> dict:
    """快速启动浏览器"""
    engine = await get_browser_engine()
    return await engine.launch(headless=headless)


async def close_browser():
    """关闭全局浏览器"""
    global _browser_engine
    if _browser_engine:
        await _browser_engine.close()
        _browser_engine = None
