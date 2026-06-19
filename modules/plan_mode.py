"""
Grade: A
AUTO-EVO-AI V0.1 — 计划模式 (Plan Mode)
先输出架构/方案→用户审批→再执行，拒绝试错
"""
from __future__ import annotations

__module_meta__ = {
    "id": "plan-mode",
    "name": "计划模式",
    "version": "V0.1",
    "group": "developer",
    "grade": "A",
    "description": "先输出架构/方案→用户审批→再执行，拒绝试错式开发",
    "tags": ["plan", "mode", "developer"],
}

import json, time, uuid
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from modules._base import Result
from modules._base.enterprise_module import EnterpriseModule


@dataclass
class PlanRecord:
    id: str = ""
    title: str = ""
    description: str = ""
    plan_type: str = "architecture"  # architecture / refactor / fix / optimize / integrate
    status: str = "pending"  # pending / approved / rejected / executed
    content: str = ""
    files_affected: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    created_at: str = ""
    approved_at: str = ""
    executed_at: str = ""
    feedback: str = ""


class PlanMode:
    """计划模式引擎"""

    def __init__(self):
        self._active = False
        self._current_plan: Optional[PlanRecord] = None
        self._history: list[PlanRecord] = []
        self._db_path = Path(__file__).parent.parent / ".evo_data" / "plans.json"
        self._load()

    def _load(self):
        if self._db_path.exists():
            try:
                raw = json.loads(self._db_path.read_text(encoding="utf-8"))
                self._history = [PlanRecord(**r) for r in raw[-100:]]
            except Exception:
                self._history = []

    def _save(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path.write_text(
            json.dumps([asdict(r) for r in self._history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def active(self) -> bool:
        return self._active

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def create_plan(self, title: str, description: str, plan_type: str = "architecture",
                    content: str = "", files: list[str] | None = None,
                    steps: list[dict] | None = None) -> PlanRecord:
        """创建新计划"""
        record = PlanRecord(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            plan_type=plan_type,
            content=content,
            files_affected=files or [],
            steps=steps or [],
            created_at=datetime.now().isoformat(),
        )
        self._current_plan = record
        self._history.append(record)
        self._save()
        return record

    def approve(self, feedback: str = "") -> Optional[PlanRecord]:
        """审批通过当前计划"""
        if not self._current_plan:
            return None
        self._current_plan.status = "approved"
        self._current_plan.approved_at = datetime.now().isoformat()
        self._current_plan.feedback = feedback
        self._save()
        return self._current_plan

    def reject(self, feedback: str = "") -> Optional[PlanRecord]:
        """驳回当前计划"""
        if not self._current_plan:
            return None
        self._current_plan.status = "rejected"
        self._current_plan.feedback = feedback
        self._save()
        return self._current_plan

    def mark_executed(self) -> Optional[PlanRecord]:
        """标记当前计划已执行"""
        if not self._current_plan:
            return None
        self._current_plan.status = "executed"
        self._current_plan.executed_at = datetime.now().isoformat()
        self._save()
        return self._current_plan

    def get_current(self) -> Optional[dict]:
        if self._current_plan:
            return asdict(self._current_plan)
        return None

    def get_history(self, limit: int = 50) -> list[dict]:
        return [asdict(r) for r in self._history[-limit:]]

    def get_status(self) -> dict:
        return {
            "active": self._active,
            "current_plan": self.get_current(),
            "total_plans": len(self._history),
        }


_planner = PlanMode()


def get_planner() -> PlanMode:
    return _planner


# ==== EnterpriseModule 包装 ====
class PlanModeModule(EnterpriseModule):
    def __init__(self):
        super().__init__(module_id="plan-mode", name="计划模式引擎")

    async def initialize(self):
        self._status = "ready"
        return Result(success=True, message="Plan Mode 就绪")

    async def execute(self, action: str, **params) -> Result:
        p = get_planner()
        try:
            if action == "activate":
                p.activate()
                return Result(success=True, data={"active": True})
            elif action == "deactivate":
                p.deactivate()
                return Result(success=True, data={"active": False})
            elif action == "create":
                r = p.create_plan(
                    params.get("title", "未命名计划"),
                    params.get("description", ""),
                    params.get("plan_type", "architecture"),
                    params.get("content", ""),
                    params.get("files"),
                    params.get("steps"),
                )
                return Result(success=True, data=asdict(r))
            elif action == "approve":
                r = p.approve(params.get("feedback", ""))
                return Result(success=True, data=asdict(r) if r else {})
            elif action == "reject":
                r = p.reject(params.get("feedback", ""))
                return Result(success=True, data=asdict(r) if r else {})
            elif action == "status":
                return Result(success=True, data=p.get_status())
            elif action == "history":
                return Result(success=True, data={"plans": p.get_history()})
            return Result(success=False, error=f"未知动作: {action}")
        except Exception as e:
            return Result(success=False, error=str(e))

    async def health_check(self):
        return Result(success=True, data={"status": self._status})
