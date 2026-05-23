# Grade: A

"""
单模块测试工具 — 生产级A级模块
提供模块实例化、初始化、健康检查的自动化测试功能
"""

import time
from typing import Any, Dict, Optional

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus


class TestSingle(EnterpriseModule):
    """单模块测试工具"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("test_single", config=config or {})
        self._test_results: list = []
        self._last_test_time: Optional[float] = None

    def initialize(self) -> None:
        """初始化测试工具"""
        try:
            self._test_results.clear()
            self._last_test_time = None
            self._logger.info("单模块测试工具初始化完成")
        except Exception as e:
            self._logger.error(f"测试工具初始化失败: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "module": self.module_name,
            "total_tests": len(self._test_results),
            "last_test_time": self._last_test_time,
        }

    def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行测试操作"""
        params = params or {}
        try:
            if action == "run_test":
                module_name = params.get("module_name", "")
                result = self._test_module(module_name)
                return {"success": True, "result": result}
            elif action == "get_results":
                return {"success": True, "result": self._test_results}
            elif action == "clear_results":
                self._test_results.clear()
                return {"success": True}
            elif action == "status":
                return {"success": True, "status": "healthy", "total_tests": len(self._test_results)}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_module(self, module_name: str) -> Dict[str, Any]:
        """测试单个模块"""
        result = {
            "module": module_name,
            "import": False,
            "instantiate": False,
            "initialize": False,
            "health_check": False,
            "error": None,
        }
        try:
            mod = __import__(f"modules.{module_name}", fromlist=["x"])
            result["import"] = True

            M = None
            for a in dir(mod):
                obj = getattr(mod, a)
                if (
                    isinstance(obj, type)
                    and hasattr(obj, "health_check")
                    and a[0].isupper()
                    and a not in ("EnterpriseModule", "ModuleStatus")
                ):
                    M = obj
                    break
            if M is None:
                result["error"] = "未找到有效模块类"
                self._test_results.append(result)
                return result

            instance = M()
            result["instantiate"] = True

            instance.initialize()
            result["initialize"] = True

            hc = instance.health_check()
            if isinstance(hc, dict):
                ok = hc.get("healthy", False) or hc.get("status") == "healthy"
            else:
                ok = getattr(hc, "healthy", False)
            result["health_check"] = ok
            result["health_check_result"] = hc if isinstance(hc, dict) else str(hc)

        except Exception as e:
            result["error"] = str(e)[:200]

        self._last_test_time = time.time()
        self._test_results.append(result)
        return result

    def shutdown(self) -> None:
        """关闭"""
        self._test_results.clear()
        self._logger.info("测试工具已关闭")


module_class = TestSingle
