"""
Browser-Use 集成模块
提供AI浏览器自动化能力：自动登录、填表、抓取、发帖
依赖: pip install browser-use playwright
"""

import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Browser-Use 可选依赖
try:
    from browser_use import Agent, Browser, ChatBrowserUse
    from browser_use.browser import BrowserConfig
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    logger.warning("browser-use not installed. Run: pip install browser-use playwright")


class BrowserUseIntegration:
    """Browser-Use 浏览器自动化集成"""

    def __init__(self, llm_provider: str = "auto"):
        self.llm_provider = llm_provider
        self.browser = None
        self.agent = None

    async def _get_llm(self):
        """获取LLM实例"""
        if not BROWSER_USE_AVAILABLE:
            return None

        try:
            # 优先使用 Browser-Use 官方优化模型
            return ChatBrowserUse()
        except Exception:
            # 降级到通用LLM
            try:
                import os
                api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")
                if api_key:
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI(api_key=api_key, model="glm-4-flash")
            except Exception:
                pass
        return None

    async def run_task(self, task: str, use_cloud: bool = False) -> Dict[str, Any]:
        """
        执行浏览器自动化任务

        Args:
            task: 自然语言任务描述，如"登录GitHub并查看我的仓库"
            use_cloud: 是否使用云端浏览器（需要API Key）

        Returns:
            {"success": bool, "result": str, "steps": list}
        """
        if not BROWSER_USE_AVAILABLE:
            return {
                "success": False,
                "error": "browser-use not installed. Run: pip install browser-use playwright && playwright install chromium"
            }

        try:
            llm = await self._get_llm()
            if not llm:
                return {"success": False, "error": "No LLM available for browser automation"}

            # 初始化浏览器
            browser_config = BrowserConfig(use_cloud=use_cloud) if use_cloud else None
            self.browser = Browser(config=browser_config) if browser_config else Browser()

            # 创建Agent
            self.agent = Agent(
                task=task,
                llm=llm,
                browser=self.browser,
            )

            # 执行任务
            history = await self.agent.run()

            # 获取结果
            result = history.final_result() if hasattr(history, 'final_result') else str(history)
            steps = history.steps if hasattr(history, 'steps') else []

            return {
                "success": True,
                "result": result,
                "steps": len(steps),
                "task": task
            }

        except Exception as e:
            logger.error(f"Browser-Use task failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # 关闭浏览器
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass

    async def screenshot(self, url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        截图指定URL

        Args:
            url: 目标网址
            save_path: 保存路径（可选）
        """
        if not BROWSER_USE_AVAILABLE:
            return {"success": False, "error": "browser-use not installed"}

        try:
            self.browser = Browser()
            page = await self.browser.new_page()
            await page.goto(url, wait_until="networkidle")

            if save_path:
                await page.screenshot(path=save_path, full_page=True)
                return {"success": True, "path": save_path}
            else:
                screenshot_bytes = await page.screenshot(full_page=True)
                return {"success": True, "screenshot": screenshot_bytes}

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if self.browser:
                await self.browser.close()

    async def extract_content(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """
        提取网页内容

        Args:
            url: 目标网址
            selector: CSS选择器（可选，不指定则提取全部文本）
        """
        if not BROWSER_USE_AVAILABLE:
            return {"success": False, "error": "browser-use not installed"}

        try:
            self.browser = Browser()
            page = await self.browser.new_page()
            await page.goto(url, wait_until="networkidle")

            if selector:
                content = await page.query_selector(selector)
                text = await content.inner_text() if content else ""
            else:
                text = await page.inner_text("body")

            return {"success": True, "content": text, "url": url}

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if self.browser:
                await self.browser.close()


# 同步包装器
def run_browser_task(task: str, use_cloud: bool = False) -> Dict[str, Any]:
    """同步版本：执行浏览器任务"""
    integration = BrowserUseIntegration()
    return asyncio.run(integration.run_task(task, use_cloud))


def screenshot_url(url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
    """同步版本：截图"""
    integration = BrowserUseIntegration()
    return asyncio.run(integration.screenshot(url, save_path))


def extract_web_content(url: str, selector: Optional[str] = None) -> Dict[str, Any]:
    """同步版本：提取内容"""
    integration = BrowserUseIntegration()
    return asyncio.run(integration.extract_content(url, selector))


# 工具函数：检查安装状态
def check_browser_use_status() -> Dict[str, Any]:
    """检查Browser-Use安装状态"""
    status = {
        "available": BROWSER_USE_AVAILABLE,
        "install_command": "pip install browser-use playwright && playwright install chromium",
        "python_version_ok": True,
        "capabilities": []
    }

    if BROWSER_USE_AVAILABLE:
        status["capabilities"] = [
            "自动登录网站",
            "自动填写表单",
            "网页数据抓取",
            "网页截图",
            "社交媒体自动发帖",
            "电商自动操作",
            "验证码自动处理（需云端）"
        ]

    return status


if __name__ == "__main__":
    # 测试
    print("Browser-Use Integration Module")
    print("=" * 50)
    status = check_browser_use_status()
    print(f"Available: {status['available']}")
    if not status['available']:
        print(f"Install: {status['install_command']}")
    else:
        print("Capabilities:")
        for cap in status['capabilities']:
            print(f"  - {cap}")
