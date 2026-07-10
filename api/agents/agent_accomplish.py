"""
Accomplish 集成模块
提供桌面自动化能力：模拟键鼠、窗口操作、文件管理
参考: https://github.com/accomplish/accomplish
"""

import os
import logging
import asyncio
import platform
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# 检测操作系统
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


class AccomplishIntegration:
    """
    Accomplish 桌面自动化集成
    
    能力：
    1. 模拟键盘输入
    2. 模拟鼠标操作
    3. 窗口管理
    4. 文件操作
    5. 应用启动和切换
    """

    def __init__(self):
        self.pyautogui_available = False
        self.pywinauto_available = False
        self.apple_script_available = False

        # 检测可用库
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖库"""
        try:
            import pyautogui
            self.pyautogui_available = True
        except ImportError as _e:
            logger.warning(f"error: {_e}")

        if IS_WINDOWS:
            try:
                import pywinauto
                self.pywinauto_available = True
            except ImportError as _e:
                logger.warning(f"error: {_e}")
        elif IS_MAC:
            # macOS使用AppleScript
            self.apple_script_available = True

    async def type_text(self, text: str, interval: float = 0.01) -> Dict[str, Any]:
        """
        模拟键盘输入

        Args:
            text: 要输入的文本
            interval: 按键间隔（秒）
        """
        if not self.pyautogui_available:
            return {
                "success": False,
                "error": "pyautogui not installed. Run: pip install pyautogui"
            }

        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)

            return {
                "success": True,
                "text": text,
                "interval": interval
            }

        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return {"success": False, "error": str(e)}

    async def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """
        模拟鼠标点击

        Args:
            x: 横坐标
            y: 纵坐标
            button: 鼠标按钮 ("left" | "right" | "middle")
        """
        if not self.pyautogui_available:
            return {
                "success": False,
                "error": "pyautogui not installed. Run: pip install pyautogui"
            }

        try:
            import pyautogui
            
            # 移动鼠标
            pyautogui.moveTo(x, y, duration=0.2)
            
            # 点击
            pyautogui.click(button=button)

            return {
                "success": True,
                "x": x,
                "y": y,
                "button": button
            }

        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {"success": False, "error": str(e)}

    async def screenshot(self, region: Optional[tuple] = None) -> Dict[str, Any]:
        """
        截图

        Args:
            region: 截图区域 (x, y, width, height)，可选
        """
        if not self.pyautogui_available:
            return {
                "success": False,
                "error": "pyautogui not installed. Run: pip install pyautogui"
            }

        try:
            import pyautogui
            
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            # 保存到临时文件
            temp_path = Path("temp_screenshot.png")
            screenshot.save(str(temp_path))

            return {
                "success": True,
                "path": str(temp_path),
                "region": region
            }

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_active_window(self) -> Dict[str, Any]:
        """获取当前活动窗口信息"""
        if IS_WINDOWS and self.pywinauto_available:
            try:
                import pywinauto
                from pywinauto import Desktop

                desktop = Desktop()
                window = desktop.get_active_window()
                rect = window.rectangle()
                return {
                    "success": True,
                    "title": window.window_text(),
                    "process_id": window.process_id(),
                    "rectangle": {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom
                    }
                }

            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": False,
                "error": "Windows + pywinauto required for active window detection"
            }

    async def launch_app(self, app_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        启动应用程序

        Args:
            app_path: 应用程序路径
            args: 命令行参数（可选）
        """
        try:
            import subprocess

            if args:
                process = subprocess.Popen([app_path] + args)
            else:
                process = subprocess.Popen(app_path)

            return {
                "success": True,
                "app_path": app_path,
                "pid": process.pid
            }

        except Exception as e:
            logger.error(f"Launch app failed: {e}")
            return {"success": False, "error": str(e)}

    async def run_apple_script(self, script: str) -> Dict[str, Any]:
        """
        运行AppleScript (macOS only)

        Args:
            script: AppleScript脚本
        """
        if not IS_MAC:
            return {
                "success": False,
                "error": "AppleScript is only available on macOS"
            }

        try:
            import subprocess

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip()
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip()
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_workflow(self, workflow: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行桌面自动化工作流

        Args:
            workflow: 工作流步骤列表，每个步骤是一个dict:
                [
                    {"action": "type", "text": "Hello"},
                    {"action": "click", "x": 100, "y": 200},
                    {"action": "screenshot", "save_path": "screenshot.png"},
                    {"action": "launch", "app_path": "notepad.exe"},
                    ...
                ]
        """
        results = []

        for i, step in enumerate(workflow):
            action = step.get("action", "")

            try:
                if action == "type":
                    result = await self.type_text(step["text"])
                elif action == "click":
                    result = await self.click(step["x"], step["y"], step.get("button", "left"))
                elif action == "screenshot":
                    result = await self.screenshot(step.get("region"))
                elif action == "launch":
                    result = await self.launch_app(step["app_path"], step.get("args"))
                elif action == "sleep":
                    import asyncio
                    await asyncio.sleep(step.get("seconds", 1))
                    result = {"success": True, "action": "sleep"}
                else:
                    result = {"success": False, "error": f"Unknown action: {action}"}

                results.append({
                    "step": i + 1,
                    "action": action,
                    "result": result
                })

                # 如果步骤失败，停止工作流
                if not result.get("success", False):
                    break

            except Exception as e:
                results.append({
                    "step": i + 1,
                    "action": action,
                    "result": {"success": False, "error": str(e)}
                })
                break

        return {
            "success": all(r["result"].get("success", False) for r in results),
            "steps_executed": len(results),
            "total_steps": len(workflow),
            "results": results
        }


# 同步包装器
def type_text(text: str, interval: float = 0.01) -> Dict[str, Any]:
    """同步版本：输入文本"""
    integration = AccomplishIntegration()
    return asyncio.run(integration.type_text(text, interval))


def click(x: int, y: int, button: str = "left") -> Dict[str, Any]:
    """同步版本：点击"""
    integration = AccomplishIntegration()
    return asyncio.run(integration.click(x, y, button))


def screenshot(region: Optional[tuple] = None) -> Dict[str, Any]:
    """同步版本：截图"""
    integration = AccomplishIntegration()
    return asyncio.run(integration.screenshot(region))


def execute_workflow(workflow: List[Dict[str, Any]]) -> Dict[str, Any]:
    """同步版本：执行工作流"""
    integration = AccomplishIntegration()
    return asyncio.run(integration.execute_workflow(workflow))


# 工具函数：检查安装状态
def check_accomplish_status() -> Dict[str, Any]:
    """检查Accomplish依赖状态"""
    status = {
        "pyautogui_available": False,
        "pywinauto_available": False,
        "apple_script_available": False,
        "install_command": "",
        "capabilities": []
    }

    # 检测pyautogui
    try:
        import pyautogui
        status["pyautogui_available"] = True
    except ImportError as _e:
        logger.warning(f"error: {_e}")

    # 检测pywinauto (Windows only)
    if IS_WINDOWS:
        try:
            import pywinauto
            status["pywinauto_available"] = True
        except ImportError as _e:
            logger.warning(f"error: {_e}")

    # AppleScript (macOS only)
    if IS_MAC:
        status["apple_script_available"] = True

    # 安装命令
    if not status["pyautogui_available"]:
        status["install_command"] = "pip install pyautogui"
        if IS_WINDOWS:
            status["install_command"] += " && pip install pywinauto"

    # 能力列表
    if status["pyautogui_available"]:
        status["capabilities"].extend([
            "模拟键盘输入",
            "模拟鼠标点击",
            "屏幕截图",
            "桌面自动化工作流"
        ])

    if status["pywinauto_available"]:
        status["capabilities"].extend([
            "窗口管理（Windows）",
            "控件操作（Windows）"
        ])

    if status["apple_script_available"]:
        status["capabilities"].extend([
            "AppleScript自动化（macOS）"
        ])

    return status


if __name__ == "__main__":
    # 测试
    logger.info("Accomplish Desktop Automation Integration Module")
    logger.info("=" * 50)
    
    status = check_accomplish_status()
    logger.info(f"pyautogui available: {status['pyautogui_available']}")
    logger.info(f"pywinauto available: {status['pywinauto_available']}")
    logger.info(f"apple_script available: {status['apple_script_available']}")
    
    if not status['pyautogui_available']:
        logger.info(f"\nInstall: {status['install_command']}")
    
    logger.info("\nCapabilities:")
    for cap in status['capabilities']:
        logger.info(f"  - {cap}")
