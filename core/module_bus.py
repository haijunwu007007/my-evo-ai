"""
AUTO-EVO-AI V0.1 — ModuleBus: 统一模块注册/发现/调用总线
解耦模块间直接import，所有模块通过总线通信
"""
import logging
logger = logging.getLogger("module_bus")

class ModuleBus:
    _instance = None
    _modules = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, name, instance, meta=None):
        self._modules[name] = {"instance": instance, "meta": meta or {}}
        logger.debug(f"ModuleBus: 注册 {name}")

    def get(self, name):
        m = self._modules.get(name)
        if m:
            return m["instance"]
        return None

    def call(self, name, action="status", params=None):
        m = self.get(name)
        if not m:
            return {"success": False, "error": f"模块 {name} 未注册"}
        if hasattr(m, "execute"):
            try:
                return m.execute(action, params or {})
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"模块 {name} 无 execute 方法"}

    def list_modules(self):
        return {k: v.get("meta", {}) for k, v in self._modules.items()}

    def count(self):
        return len(self._modules)

module_bus = ModuleBus()
