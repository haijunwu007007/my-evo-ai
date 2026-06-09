"""📦 Sample Plugin — PluginBase 使用示范

用法:
    python -c "from modules._base.plugin_manager import plugin_manager; 
               plugin_manager.scan_directory('modules'); 
               print(plugin_manager.count, 'plugins loaded')"
"""
from modules._base.plugin_base import PluginBase
from typing import Any, Dict, List, Optional


class HelloPlugin(PluginBase):
    """示范 Plugin — 展示 6 大 Hook 的用法"""

    plugin_id = "sample-hello"
    plugin_name = "Hello World 示范"
    plugin_version = "V0.1"
    plugin_group = "demo"

    def initialize(self) -> Dict[str, Any]:
        self.info("HelloPlugin 已启动！")
        return {"success": True, "message": "Hello from Plugin!"}

    def shutdown(self) -> None:
        self.info("HelloPlugin 已关闭")

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "healthy": True, "plugin": self.plugin_id}

    def on_startup(self) -> Dict[str, Any]:
        """Hook: 服务启动时执行"""
        self.info("[on_startup] 系统启动了！")
        return {"action": "logged_startup"}

    def on_shutdown(self) -> Dict[str, Any]:
        self.info("[on_shutdown] 系统关闭中...")
        return {"action": "logged_shutdown"}

    def on_menu(self) -> List[Dict[str, str]]:
        """Hook: 提供侧边栏菜单"""
        return [{
            "title": "Hello 示例",
            "path": "/hello-plugin",
            "icon": "Smile",
        }]

    def on_widget(self) -> Dict[str, Any]:
        """Hook: 提供 Dashboard 组件"""
        return {
            "type": "stat",
            "title": "Hello Plugin",
            "value": "✅ 运行中",
            "color": "#10b981",
        }

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        if action == "greet":
            name = (params or {}).get("name", "World")
            return {"success": True, "message": f"Hello, {name}!"}
        return {"success": True, "status": "running", "version": "0.1"}


module_class = HelloPlugin
