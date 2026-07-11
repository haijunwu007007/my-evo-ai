from modules._base.enterprise_module import EnterpriseModule
"""
AUTO-EVO-AI V0.1 — 自主决策引擎 模块
基于规则和优先级的轻量级决策引擎，用于任务分级、路由选择和自动升级
"""
import json, logging, os, time
from pathlib import Path

logger = logging.getLogger("autonomous_decision_engine")

__module_meta__ = {
    "id": "autonomous_decision_engine",
    "name": "自主决策引擎",
    "version": "V0.1",
    "group": "ai",
    "grade": "A"
}

_BASE = Path(__file__).resolve().parent.parent
_DECISIONS_FILE = _BASE / "data" / "decisions.json"

class AutonomousDecisionEngine(EnterpriseModule):
    def __init__(self):
        self._name = "自主决策引擎"
        self._ready = True
        self._decisions = self._load()

    def _load(self) -> list:
        try:
            if _DECISIONS_FILE.exists():
                return json.loads(_DECISIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save(self):
        try:
            _DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            _DECISIONS_FILE.write_text(json.dumps(self._decisions[-100:], ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[ADE] save error: {e}")

    def decide(self, context: dict) -> dict:
        priority = context.get("priority", "normal")
        task_type = context.get("type", "general")
        urgency = context.get("urgency", 0)
        now = time.time()

        if priority == "critical" or urgency > 8:
            decision = {"decision": "escalate", "reason": "高优先级或紧急性任务需人工介入", "suggested_action": "通知管理员"}
        elif priority == "high" or urgency > 5:
            decision = {"decision": "semi_auto", "reason": "建议半自动处理", "auto_first": True}
        elif task_type == "monitor":
            decision = {"decision": "auto_process", "confidence": 0.95, "action": "自动处理监控事件"}
        elif task_type == "data":
            decision = {"decision": "auto_process", "confidence": 0.90, "action": "自动执行数据分析"}
        else:
            decision = {"decision": "auto_process", "confidence": 0.87, "action": "常规自动处理"}

        record = {"time": now, "context": context, "decision": decision}
        self._decisions.append(record)
        self._save()
        return decision

    def execute(self, action="status", params=None):
        params = params or {}
        if action == "decide":
            return self.decide(params.get("context", {}))
        if action == "history":
            return {"success": True, "total": len(self._decisions), "records": self._decisions[-20:]}
        return self.get_status()

    def get_status(self):
        return {"success": True, "module": "decision_engine", "version": "V0.1",
                "total_decisions": len(self._decisions), "ready": self._ready}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": getattr(self, "name", self.__class__.__name__)}

    def initialize(self) -> dict:
        self._initialized = True
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    def shutdown(self) -> dict:
        self._initialized = False
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    async def status(self) -> dict:
        return {"name": getattr(self, "name", self.__class__.__name__), "status": "ok", "initialized": getattr(self, "_initialized", False)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        try:
            if action in ("status", "info", "stats"):
                return self.health_check()
            elif action == "help":
                return {"actions": ["status", "help"], "module": getattr(self, "name", self.__class__.__name__)}
            return {"success": True, "action": action, "module": getattr(self, "name", self.__class__.__name__)}
        except Exception as e:
            return {"success": False, "error": str(e)}
