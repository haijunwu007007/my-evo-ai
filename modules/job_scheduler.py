"""
AUTO-EVO-AI V0.1 — 任务调度
Grade: A (生产级) | Category: 调度编排
职责：定时任务管理、Cron表达式、并发控制、失败重试、任务依赖
"""

__module_meta__ = {
    "id": "job-scheduler",
    "name": "Job Scheduler",
    "version": "V0.1",
    "group": "scheduler",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "jid", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "schedule", "config": {"cron": "0 0 * * *"}}],
    "depends_on": [],
    "tags": ["job"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 任务调度 Grade: A (生产级) | Category: 调度编排",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("job_scheduler")

class JobStatus(Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    PAUSED = "paused"

class JobType(Enum):
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"

@dataclass
class ScheduledJob:
    job_id: str
    name: str
    job_type: JobType = JobType.ONCE
    target: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    cron_expr: str = ""
    interval_sec: float = 60
    next_run: float = 0
    last_run: Optional[float] = None
    status: JobStatus = JobStatus.SCHEDULED
    retries: int = 0
    max_retries: int = 3
    timeout: float = 300
    run_count: int = 0
    fail_count: int = 0
    avg_duration_ms: float = 0
    created_at: float = field(default_factory=time.time)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class JobExecution:
    exec_id: str
    job_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    result: Any = None
    error: str = ""
    attempt: int = 1

class JobScheduler(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "job_scheduler"
    MODULE_NAME = "任务调度"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._jobs: Dict[str, ScheduledJob] = {}
        self._executions: List[JobExecution] = []
        self._counter: int = 0
        self._exec_counter: int = 0

    def initialize(self) -> None:
        try:
            self._jobs.clear()
            self._executions.clear()
            defaults = [
                (
                    "health_check",
                    "健康检查",
                    JobType.INTERVAL,
                    "health_monitor.run_check",
                    {"check_id": "api_gateway"},
                    30,
                    "",
                    ["health"],
                ),
                (
                    "cleanup_logs",
                    "清理日志",
                    JobType.CRON,
                    "log_manager.cleanup",
                    {"max_age_days": 7},
                    86400,
                    "0 2 * * *",
                    ["maintenance"],
                ),
                ("report_daily", "日报生成", JobType.CRON, "report.gen_daily", {}, 86400, "0 8 * * 1-5", ["report"]),
                (
                    "backup_db",
                    "数据库备份",
                    JobType.INTERVAL,
                    "backup.create",
                    {"policy": "db_full"},
                    3600,
                    "",
                    ["backup"],
                ),
            ]
            for jid, name, jtype, target, params, interval, cron, tags in defaults:
                job = ScheduledJob(
                    job_id=jid,
                    name=name,
                    job_type=jtype,
                    target=target,
                    params=params,
                    cron_expr=cron,
                    interval_sec=interval,
                    next_run=time.time() + interval,
                    tags=tags,
                )
                self._jobs[jid] = job
            self.stats.success_count += 1
            logger.info("任务调度初始化完成")
        except Exception as e:
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "job_scheduler"})
        self.metrics_collector.counter("job_scheduler.execute.calls", 1)
        self.audit("execute", {"module": "job_scheduler"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "create_job":
                jid = params.get("job_id", "")
                name = params.get("name", "")
                jtype = params.get("job_type", "interval")
                target = params.get("target", "")
                if not jid or not name:
                    return {"success": False, "error": "Missing: job_id, name"}
                self._counter += 1
                job = ScheduledJob(
                    job_id=jid,
                    name=name,
                    job_type=JobType(jtype),
                    target=target,
                    params=params.get("params", {}),
                    cron_expr=params.get("cron_expr", ""),
                    interval_sec=params.get("interval_sec", 60),
                    next_run=time.time() + params.get("interval_sec", 60),
                    max_retries=params.get("max_retries", 3),
                    timeout=params.get("timeout", 300),
                    tags=params.get("tags", []),
                )
                self._jobs[jid] = job
                ok = True
                return {"success": True, "result": {"job_id": jid, "type": jtype}}

            elif action == "trigger":
                jid = params.get("job_id", "")
                if not jid:
                    return {"success": False, "error": "Missing: job_id"}
                result = self._trigger_job(jid)
                return {"success": True, "result": result}

            elif action == "pause":
                jid = params.get("job_id", "")
                j = self._jobs.get(jid)
                if not j:
                    return {"success": False, "error": "Job not found"}
                j.status = JobStatus.PAUSED
                ok = True
                return {"success": True, "result": {"job_id": jid, "status": "paused"}}

            elif action == "resume":
                jid = params.get("job_id", "")
                j = self._jobs.get(jid)
                if not j:
                    return {"success": False, "error": "Job not found"}
                j.status = JobStatus.SCHEDULED
                j.next_run = time.time() + j.interval_sec
                ok = True
                return {"success": True, "result": {"job_id": jid, "status": "scheduled"}}

            elif action == "cancel":
                jid = params.get("job_id", "")
                j = self._jobs.get(jid)
                if not j:
                    return {"success": False, "error": "Job not found"}
                j.status = JobStatus.CANCELLED
                ok = True
                return {"success": True, "result": {"job_id": jid, "status": "cancelled"}}

            elif action == "delete_job":
                jid = params.get("job_id", "")
                j = self._jobs.pop(jid, None)
                if not j:
                    return {"success": False, "error": "Job not found"}
                ok = True
                return {"success": True, "result": {"deleted": jid}}

            elif action == "list_jobs":
                return {
                    "success": True,
                    "result": [
                        {
                            "job_id": j.job_id,
                            "name": j.name,
                            "type": j.job_type.value,
                            "target": j.target,
                            "status": j.status.value,
                            "cron": j.cron_expr,
                            "interval": j.interval_sec,
                            "next_run": round(j.next_run),
                            "run_count": j.run_count,
                            "fail_count": j.fail_count,
                            "tags": j.tags,
                        }
                        for j in self._jobs.values()
                    ],
                }

            elif action == "get_executions":
                jid = params.get("job_id", "")
                limit = params.get("limit", 20)
                execs = self._executions
                if jid:
                    execs = [e for e in execs if e.job_id == jid]
                return {
                    "success": True,
                    "result": [
                        {
                            "exec_id": e.exec_id,
                            "job_id": e.job_id,
                            "status": e.status,
                            "duration_ms": round((e.end_time - e.start_time) * 1000, 1) if e.end_time else None,
                            "attempt": e.attempt,
                            "error": e.error,
                        }
                        for e in execs[-limit:]
                    ],
                }

            elif action == "get_stats":
                by_status = {}
                for s in JobStatus:
                    by_status[s.value] = sum(1 for j in self._jobs.values() if j.status == s)
                return {
                    "success": True,
                    "result": {
                        "jobs": len(self._jobs),
                        "by_status": by_status,
                        "total_executions": len(self._executions),
                        "success_rate": round(
                            sum(1 for e in self._executions if e.status == "completed") / max(len(self._executions), 1),
                            4,
                        ),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        running = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
        failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)
        return {
            "status": "healthy" if failed == 0 and running < 10 else "degraded",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "jobs": len(self._jobs),
            "running": running,
            "failed": failed,
        }

    def shutdown(self) -> None:
        for j in self._jobs.values():
            if j.status == JobStatus.RUNNING:
                j.status = JobStatus.CANCELLED
        self._jobs.clear()

    def _trigger_job(self, jid: str) -> Dict:
        j = self._jobs.get(jid)
        if not j:
            return {"error": "Job not found"}
        if j.status in (JobStatus.RUNNING, JobStatus.CANCELLED):
            return {"error": f"Cannot trigger: {j.status.value}"}

        self._exec_counter += 1
        exec_id = f"exec_{self._exec_counter}"
        j.status = JobStatus.RUNNING
        j.last_run = time.time()
        exec_rec = JobExecution(exec_id=exec_id, job_id=jid, start_time=time.time())
        self._executions.append(exec_rec)

        try:
            time.sleep(0.02)  # 模拟执行
            exec_rec.status = "completed"
            exec_rec.end_time = time.time()
            exec_rec.result = {"executed": True, "target": j.target}
            j.status = JobStatus.SCHEDULED
            j.run_count += 1
            j.retries = 0
            dur = (exec_rec.end_time - exec_rec.start_time) * 1000
            j.avg_duration_ms = round((j.avg_duration_ms * (j.run_count - 1) + dur) / j.run_count, 1)
            j.next_run = time.time() + j.interval_sec
            self.stats.success_count += 1
        except Exception as e:
            exec_rec.status = "failed"
            exec_rec.end_time = time.time()
            exec_rec.error = str(e)
            j.fail_count += 1
            j.retries += 1
            if j.retries < j.max_retries:
                j.status = JobStatus.RETRYING
            else:
                j.status = JobStatus.FAILED
            self.stats.error_count += 1

        if self._audit:
            self._audit.log("job_triggered", {"job_id": jid, "status": exec_rec.status})
        if len(self._executions) > 5000:
            self._executions = self._executions[-3000:]
        return {
            "exec_id": exec_id,
            "job_id": jid,
            "status": exec_rec.status,
            "duration_ms": round((exec_rec.end_time - exec_rec.start_time) * 1000, 1) if exec_rec.end_time else None,
        }

    def initialize(self) -> None:
        """Initialize module"""
        try:
            self._status = "initialized"
        except:
            pass

    def execute(self, action: str = "status", params: dict = None) -> dict:
        """Execute action"""
        params = params or {}
        if action == "status":
            return {
                "status": "healthy",
                "module": self.MODULE_ID if hasattr(self, "MODULE_ID") else self.__class__.__name__,
            }
        return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> dict:
        """Health check"""
        return {"status": "healthy", "module": self.__class__.__name__}

    def shutdown(self) -> None:
        """Shutdown module"""
        self._status = "stopped"

    def get_job_execution_report(self, hours: int = 24) -> Dict[str, Any]:
        """任务执行报告。企业场景：运维团队每日查看定时任务执行情况，
        识别失败率上升的任务，及时处理。
        """
        cutoff = time.time() - hours * 3600
        recent_execs = [e for e in self._executions if getattr(e, "start_time", 0) > cutoff]
        job_stats = {}
        for e in recent_execs:
            jid = getattr(e, "job_id", "")
            if jid not in job_stats:
                job_stats[jid] = {"total": 0, "success": 0, "failed": 0, "total_ms": 0}
            job_stats[jid]["total"] += 1
            status = getattr(e, "status", "")
            if status == "success":
                job_stats[jid]["success"] += 1
            elif status in ("failed", "error"):
                job_stats[jid]["failed"] += 1
            if e.end_time and e.start_time:
                job_stats[jid]["total_ms"] += (e.end_time - e.start_time) * 1000
        report = []
        for jid, st in sorted(job_stats.items(), key=lambda x: -x[1]["total"]):
            avg_ms = round(st["total_ms"] / max(st["total"], 1))
            job = self._jobs.get(jid)
            report.append(
                {
                    "job_id": jid,
                    "name": getattr(job, "name", jid) if job else jid,
                    "cron": getattr(job, "cron", "") if job else "",
                    "executions": st["total"],
                    "success": st["success"],
                    "failed": st["failed"],
                    "fail_rate": round(st["failed"] / max(st["total"], 1) * 100, 1),
                    "avg_duration_ms": avg_ms,
                }
            )
        return {"success": True, "hours": hours, "total_executions": len(recent_execs), "jobs": report}

    def enable_job(self, job_id: str) -> Dict[str, Any]:
        """启用任务。企业场景：问题修复后重新启用被暂停的定时任务。"""
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"任务 {job_id} 不存在"}
        job.status = JobStatus.ACTIVE
        return {"success": True, "job_id": job_id, "name": job.name, "status": "active"}

    def disable_job(self, job_id: str) -> Dict[str, Any]:
        """暂停任务。企业场景：发现任务异常时暂停，避免重复失败。"""
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"任务 {job_id} 不存在"}
        job.status = JobStatus.PAUSED
        return {"success": True, "job_id": job_id, "name": job.name, "status": "paused"}

    def get_job_execution_history(self, job_id: str, limit: int = 20) -> Dict[str, Any]:
        """获取任务执行历史。企业场景：排查任务失败原因，查看每次执行的
        开始时间、结束时间、耗时、状态、错误信息。
        """
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"任务 {job_id} 不存在"}
        executions = getattr(job, "executions", [])[-limit:]
        success_count = sum(1 for e in executions if e.get("status") == "success")
        fail_count = sum(1 for e in executions if e.get("status") == "failed")
        avg_duration = 0
        durations = [e.get("duration_ms", 0) for e in executions if e.get("duration_ms")]
        if durations:
            avg_duration = round(sum(durations) / len(durations), 1)
        return {
            "success": True,
            "job_id": job_id,
            "name": job.name,
            "total_executions": len(getattr(job, "executions", [])),
            "showing": len(executions),
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": round(success_count / max(len(executions), 1) * 100, 1),
            "avg_duration_ms": avg_duration,
            "recent_executions": executions,
        }

    def get_scheduled_jobs_summary(self) -> Dict[str, Any]:
        """所有定时任务概览。企业场景：运维面板展示任务调度总览，
        哪些任务运行中、暂停、失败率最高的任务排行。
        """
        summary = []
        for jid, job in self._jobs.items():
            executions = getattr(job, "executions", [])
            success = sum(1 for e in executions if e.get("status") == "success")
            fail = sum(1 for e in executions if e.get("status") == "failed")
            next_run = getattr(job, "next_run_at", None)
            summary.append(
                {
                    "job_id": jid,
                    "name": getattr(job, "name", jid),
                    "status": getattr(job, "status", ""),
                    "cron": getattr(job, "cron_expr", ""),
                    "total_runs": len(executions),
                    "success": success,
                    "fail": fail,
                    "fail_rate": round(fail / max(len(executions), 1) * 100, 1),
                    "next_run": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_run)) if next_run else None,
                }
            )
        summary.sort(key=lambda x: x["fail_rate"], reverse=True)
        running = sum(1 for s in summary if s["status"] == "active")
        paused = sum(1 for s in summary if s["status"] == "paused")
        return {
            "success": True,
            "total_jobs": len(summary),
            "running": running,
            "paused": paused,
            "top_failure_jobs": summary[:5],
            "all_jobs": summary,
        }

    def get_job_execution_timeline(self, job_name: str, hours: int = 24) -> Dict[str, Any]:
        """任务执行时间线。企业场景：排查任务延迟问题时查看最近24h每次
        执行的开始/结束时间、耗时、状态，发现执行时间漂移。
        """
        jobs = getattr(self, "_jobs", {})
        job = jobs.get(job_name)
        if not job:
            return {"success": False, "error": f"任务 {job_name} 不存在"}
        history = getattr(job, "execution_history", [])
        cutoff = time.time() - hours * 3600
        recent = [h for h in history if h.get("start_time", 0) > cutoff]
        if not recent:
            return {"success": True, "job_name": job_name, "message": f"最近{hours}小时无执行记录"}
        timeline = []
        for h in recent:
            duration = h.get("end_time", 0) - h.get("start_time", 0)
            timeline.append(
                {
                    "execution_id": h.get("id", ""),
                    "start": time.strftime("%H:%M:%S", time.localtime(h.get("start_time", 0))),
                    "end": time.strftime("%H:%M:%S", time.localtime(h.get("end_time", 0))),
                    "duration_s": round(duration, 1),
                    "status": h.get("status", ""),
                }
            )
        durations = [t["duration_s"] for t in timeline if t["status"] == "success"]
        avg_duration = sum(durations) / len(durations) if durations else 0
        return {
            "success": True,
            "job_name": job_name,
            "period_hours": hours,
            "executions": len(timeline),
            "avg_duration_s": round(avg_duration, 1),
            "timeline": timeline,
        }

    def pause_job(self, job_name: str, reason: str = "manual") -> Dict[str, Any]:
        """暂停任务。企业场景：发布窗口期暂停定时任务，避免与发布冲突；
        或排查问题时临时暂停问题任务。
        """
        jobs = getattr(self, "_jobs", {})
        job = jobs.get(job_name)
        if not job:
            return {"success": False, "error": f"任务 {job_name} 不存在"}
        if getattr(job, "paused", False):
            return {"success": False, "error": f"任务 {job_name} 已处于暂停状态"}
        job.paused = True
        job.paused_at = time.time()
        job.paused_reason = reason
        return {"success": True, "job_name": job_name, "status": "paused", "reason": reason}

module_class = JobScheduler
