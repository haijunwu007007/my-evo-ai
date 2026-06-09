"""AUTO-EVO-AI V0.1 — browser-use (93k⭐) AI浏览器自动化
Grade: A (生产级) | Category: AI集成
使用 browser-use SDK 实现 AI 驱动的网页自动化操作"""
import asyncio, json, time, logging, os, base64
logger = logging.getLogger("evo.browser_use")
VERSION = "V0.1"
__module_meta__ = {"id": "browser-use", "name": "Browser Use Enhanced", "version": VERSION, "group": "browser"}

try:
    from browser_use import Agent, Browser, BrowserConfig
    HAS_BROWSER_USE = True
except ImportError:
    HAS_BROWSER_USE = False

_BROWSER = None
_HISTORY = []

async def _get_browser():
    global _BROWSER
    if _BROWSER is None:
        _BROWSER = Browser(config=BrowserConfig(headless=True))
    return _BROWSER

async def _execute_task(task: str, headless: bool = True, max_steps: int = 20) -> dict:
    if not HAS_BROWSER_USE:
        return {"success": False, "error": "browser-use not installed. Run: pip install browser-use playwright && playwright install chromium"}
    try:
        browser = await _get_browser()
        agent = Agent(task=task, browser=browser, max_steps=max_steps)
        result = await agent.run()

        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "task": task[:100],
            "success": result.is_successful() if hasattr(result, 'is_successful') else bool(result),
            "actions": result.action_count() if hasattr(result, 'action_count') else 0,
            "summary": str(result)[:200] if result else "No result",
        }
        _HISTORY.append(entry)
        if len(_HISTORY) > 50:
            _HISTORY.pop(0)
        return {"success": True, "result": str(result)[:2000], "actions": entry["actions"], "summary": entry["summary"]}
    except Exception as e:
        logger.error(f"browser-use task failed: {e}")
        return {"success": False, "error": str(e)}

async def execute(action: str = "", params: dict = None) -> dict:
    p = params or {}
    if action in ("status", "info", "ping"):
        return {"success": True, "status": "running", "available": HAS_BROWSER_USE, "version": "0.12.6", "installed": HAS_BROWSER_USE}
    if action == "health_check":
        if not HAS_BROWSER_USE:
            return {"success": False, "error": "not installed"}
        return {"success": True, "status": "healthy", "version": "0.12.6"}
    if action == "execute" or action == "run":
        task = p.get("task", p.get("instruction", ""))
        if not task:
            return {"success": False, "error": "task is required"}
        return await _execute_task(task, p.get("headless", True), p.get("max_steps", 20))
    if action == "history":
        return {"success": True, "history": _HISTORY[-20:]}
    if action == "cleanup":
        global _BROWSER
        if _BROWSER:
            await _BROWSER.close()
            _BROWSER = None
        _HISTORY.clear()
        return {"success": True, "message": "Browser closed, history cleared"}
    return {"success": False, "error": f"Unknown action: {action}"}

async def shutdown():
    global _BROWSER
    if _BROWSER:
        await _BROWSER.close()
        _BROWSER = None
