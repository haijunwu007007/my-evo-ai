"""
管线引擎 — 模块自动串联执行 + 失败回滚
A.execute() → B.execute() → C.execute()
"""
import logging, json, traceback, datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PipelineEngine:
    def __init__(self):
        self._history: List[dict] = []
        self._max_history = 100

    async def run(self, chain: List[str], initial_params: dict = None) -> dict:
        """
        执行模块链
        chain: ["module_a", "module_b", "module_c"]
        initial_params: 传给第一个模块的参数
        """
        pipeline_id = f"pipe_{datetime.datetime.now().strftime('%H%M%S')}_{len(self._history)}"
        results = []
        rollback_stack = []
        params = initial_params or {}
        success = True
        error = None

        logger.info("[PIPELINE] %s 开始执行 %d 个模块", pipeline_id, len(chain))

        for idx, module_name in enumerate(chain):
            step_result = {
                "step": idx + 1,
                "module": module_name,
                "status": "pending",
                "input": dict(params) if params else {},
                "output": None,
                "error": None,
            }

            try:
                mod = self._load_module(module_name)
                output = await mod.execute(params)
                step_result["output"] = output
                step_result["status"] = "success"

                # Pass output to next module
                if isinstance(output, dict):
                    for k, v in output.items():
                        if k not in ("success", "error"):
                            params[k] = v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)

                rollback_stack.append((module_name, step_result.copy()))
                logger.info("[PIPELINE] %s 步骤%d %s ✅", pipeline_id, idx + 1, module_name)

            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                error = str(e)
                success = False
                logger.error("[PIPELINE] %s 步骤%d %s ❌ %s", pipeline_id, idx + 1, module_name, e)

                # Rollback: undo completed steps
                logger.info("[PIPELINE] %s 开始回滚 %d 个步骤", pipeline_id, len(rollback_stack))
                for rollback_mod, rollback_result in reversed(rollback_stack):
                    try:
                        mod = self._load_module(rollback_mod)
                        if hasattr(mod, "rollback"):
                            await mod.rollback(rollback_result.get("output", {}))
                        logger.info("[PIPELINE] %s 回滚 %s ✅", pipeline_id, rollback_mod)
                    except Exception as rb_e:
                        logger.warning("[PIPELINE] %s 回滚 %s 失败: %s", pipeline_id, rollback_mod, rb_e)

                results.append(step_result)
                break

            results.append(step_result)

        pipeline_record = {
            "id": pipeline_id,
            "chain": chain,
            "steps": len(chain),
            "completed": sum(1 for r in results if r.get("status") == "success"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "success": success,
            "error": error,
            "results": results,
            "final_params": params,
        }

        self._history.append(pipeline_record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return pipeline_record

    def _load_module(self, name: str):
        """动态加载模块"""
        import importlib
        mod_path = f"modules.{name}"
        try:
            mod = importlib.import_module(mod_path)
        except ImportError:
            mod = importlib.import_module(f"D:/AUTO-EVO-AI-V0.1.modules.{name}")
        # Find the class
        for attr_name in dir(mod):
            if attr_name.lower() == name.replace('-', '_').lower():
                cls = getattr(mod, attr_name)
                if isinstance(cls, type):
                    return cls()
        return mod

    def get_history(self, limit: int = 10) -> List[dict]:
        return self._history[-limit:]

    def get_stats(self) -> dict:
        total = len(self._history)
        success = sum(1 for h in self._history if h.get("success"))
        failed = total - success
        total_steps = sum(h.get("steps", 0) for h in self._history)
        return {
            "total_pipelines": total,
            "success": success,
            "failed": failed,
            "total_steps": total_steps,
            "avg_steps": round(total_steps / total, 1) if total else 0,
        }


_engine = None
_pipeline_store = None

def get_pipeline() -> PipelineEngine:
    global _engine
    if _engine is None:
        _engine = PipelineEngine()
    return _engine

def get_pipeline_engine():
    """旧版兼容别名"""
    return get_pipeline()

def get_pipeline_store():
    """旧版兼容：存储层"""
    global _pipeline_store
    if _pipeline_store is None:
        class PipelineStore:
            def get_execution_stats(self):
                e = get_pipeline()
                stats = e.get_stats()
                stats["running"] = 0
                stats["completed"] = stats["success"]
                return stats
            def list_executions(self, pipeline_id="", limit=10, offset=0):
                e = get_pipeline()
                return e.get_history(limit)
            def get_execution(self, exec_id):
                e = get_pipeline()
                for h in e._history:
                    if h.get("id") == exec_id:
                        return h
                return None
            def list_pipelines(self, tag="", active_only=False):
                return []
            def get_pipeline(self, pipeline_id):
                return None
            def get_pipeline_versions(self, pipeline_id):
                return []
            def delete_pipeline(self, pipeline_id):
                return True
        _pipeline_store = PipelineStore()
    return _pipeline_store

def reset_pipeline_engine():
    """旧版兼容：重置引擎"""
    global _engine
    _engine = PipelineEngine()
