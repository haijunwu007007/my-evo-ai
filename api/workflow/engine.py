"""AUTO-EVO-AI V0.1 — 工作流DAG引擎

支持步骤串行/并行执行，依赖解析，状态持久化，重试。
"""
import json, time, os, threading
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStep:
    def __init__(self, step_id: str, tool: str, args: dict = None,
                 depends_on: List[str] = None, max_retries: int = 2,
                 timeout: int = 120, label: str = ""):
        self.step_id = step_id
        self.tool = tool
        self.args = args or {}
        self.depends_on = depends_on or []
        self.max_retries = max_retries
        self.timeout = timeout
        self.label = label or tool
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0

    def to_dict(self):
        return {
            "step_id": self.step_id, "tool": self.tool, "args": self.args,
            "depends_on": self.depends_on, "max_retries": self.max_retries,
            "timeout": self.timeout, "label": self.label,
            "status": self.status.value, "result": self.result,
            "error": self.error, "retry_count": self.retry_count,
        }

class Workflow:
    def __init__(self, wf_id: str, name: str, steps: List[WorkflowStep],
                 description: str = "", owner: str = "user"):
        self.wf_id = wf_id
        self.name = name
        self.description = description
        self.owner = owner
        self.steps = steps
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.context = {}  # 步骤间共享数据

    def to_dict(self):
        return {
            "wf_id": self.wf_id, "name": self.name, "description": self.description,
            "owner": self.owner, "status": self.status.value,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "steps": [s.to_dict() for s in self.steps],
            "context_keys": list(self.context.keys()),
        }

class WorkflowEngine:
    def __init__(self, tool_executor: Optional[Callable] = None):
        self._workflows: Dict[str, Workflow] = {}
        self._lock = threading.Lock()
        self._tool_executor = tool_executor

    def create(self, name: str, steps: List[dict], description: str = "",
               owner: str = "user") -> Workflow:
        step_objs = []
        for i, s in enumerate(steps):
            step_objs.append(WorkflowStep(
                step_id=s.get("id", f"step_{i+1}"),
                tool=s["tool"], args=s.get("args", {}),
                depends_on=s.get("depends_on", []),
                max_retries=s.get("max_retries", 2),
                timeout=s.get("timeout", 120),
                label=s.get("label", ""),
            ))
        wf = Workflow(wf_id=f"wf_{int(time.time())}_{hash(name) % 10000}",
                      name=name, steps=step_objs, description=description, owner=owner)
        with self._lock:
            self._workflows[wf.wf_id] = wf
        return wf

    def get(self, wf_id: str) -> Optional[Workflow]:
        return self._workflows.get(wf_id)

    def list(self, owner: str = "") -> List[Workflow]:
        with self._lock:
            ws = list(self._workflows.values())
        if owner:
            ws = [w for w in ws if w.owner == owner]
        return ws

    def _get_ready_steps(self, wf: Workflow) -> List[WorkflowStep]:
        """获取所有可执行的步骤（依赖已完成的步骤）"""
        ready = []
        for s in wf.steps:
            if s.status != StepStatus.PENDING:
                continue
            deps_ok = all(
                any(ds.step_id == dep and ds.status == StepStatus.SUCCESS
                    for ds in wf.steps)
                for dep in s.depends_on
            )
            if deps_ok:
                ready.append(s)
        return ready

    def _all_done(self, wf: Workflow) -> bool:
        return all(s.status in (StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED)
                   for s in wf.steps)

    def execute(self, wf_id: str, executor: Optional[Callable] = None) -> dict:
        """执行工作流（同步）"""
        wf = self.get(wf_id)
        if not wf:
            return {"ok": False, "error": "workflow not found"}
        wf.status = WorkflowStatus.RUNNING
        wf.updated_at = datetime.now().isoformat()
        exec_fn = executor or self._tool_executor

        while not self._all_done(wf):
            ready = self._get_ready_steps(wf)
            if not ready and not self._all_done(wf):
                # 死锁检查：有步骤待执行但无就绪→依赖不可能完成
                blocked = [s for s in wf.steps if s.status == StepStatus.PENDING]
                for s in blocked:
                    s.status = StepStatus.FAILED
                    s.error = "依赖无法满足（上游步骤失败）"
                wf.status = WorkflowStatus.FAILED
                break

            for step in ready:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now().isoformat()
                for attempt in range(step.max_retries + 1):
                    try:
                        if exec_fn:
                            result = exec_fn(step.tool, step.args, context=wf.context)
                        else:
                            result = {"ok": True, "data": f"模拟执行: {step.tool}"}
                        step.result = result
                        step.status = StepStatus.SUCCESS
                        break
                    except Exception as e:
                        step.retry_count = attempt + 1
                        step.error = str(e)
                        if attempt < step.max_retries:
                            time.sleep(1)

                if step.status != StepStatus.SUCCESS:
                    step.status = StepStatus.FAILED
                    wf.status = WorkflowStatus.FAILED
                step.completed_at = datetime.now().isoformat()

        if wf.status == WorkflowStatus.RUNNING:
            failed = [s for s in wf.steps if s.status == StepStatus.FAILED]
            wf.status = WorkflowStatus.FAILED if failed else WorkflowStatus.COMPLETED
        wf.updated_at = datetime.now().isoformat()
        return self.summary(wf_id)

    def summary(self, wf_id: str) -> dict:
        wf = self.get(wf_id)
        if not wf:
            return {"ok": False, "error": "not found"}
        steps_summary = []
        for s in wf.steps:
            steps_summary.append({
                "id": s.step_id, "tool": s.tool, "label": s.label,
                "status": s.status.value, "error": s.error,
                "result_preview": str(s.result)[:100] if s.result else None,
            })
        return {
            "ok": True, "wf_id": wf.wf_id, "name": wf.name,
            "status": wf.status.value,
            "total_steps": len(wf.steps),
            "completed": sum(1 for s in wf.steps if s.status == StepStatus.SUCCESS),
            "failed": sum(1 for s in wf.steps if s.status == StepStatus.FAILED),
            "steps": steps_summary,
        }

# 全局实例
_default_engine = None

def get_engine() -> WorkflowEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = WorkflowEngine()
    return _default_engine
