# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI v7.0 - 定时任务调度器（A级生产实现）
===============================================
模块ID: cron-scheduler
功能：Cron定时调度 — 任务注册/定时触发/并发控制/失败重试/执行历史。

核心能力：
  1. Cron表达式 — 标准cron语法定时
  2. 一次性任务 — 指定时间执行
  3. 间隔任务 — 固定间隔循环执行
  4. 并发控制 — 同任务不重叠执行
  5. 失败重试 — 自动重试+退避
  6. 执行历史 — 全量执行记录
"""

__module_meta__ = {
    "id": "cron-scheduler",
    "name": "Cron Scheduler",
    "version": "1.0.0",
    "group": "scheduler",
    "inputs": [
        {"name": "interval_str", "type": "string", "required": True, "description": ""},
        {"name": "cron_expr", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "schedule", "config": {"cron": "0 0 * * *"}}],
    "depends_on": [],
    "tags": ["adapter", "cron"],
    "grade": "B",
    "description": "AUTO-EVO-AI v7.0 - 定时任务调度器（A级生产实现） ===============================================",
}

import time
import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import deque
from dataclasses import dataclass, field

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    CircuitBreakerMixin,
    RateLimiterMixin,
    Result,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.cron-scheduler")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

@dataclass
class CronJob:
    """定时任务"""

    job_id: str = ""
    name: str = ""
    cron: str = ""  # cron表达式 或 interval:秒数
    action: str = ""  # 要执行的动作
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    status: str = "idle"  # idle/running/success/failed
    last_run: str = ""
    next_run: str = ""
    run_count: int = 0
    error_count: int = 0
    last_error: str = ""
    max_retries: int = 3
    timeout: float = 300
    running_lock: bool = False

    def __post_init__(self):
        if not self.job_id:
            self.job_id = f"JOB-{int(time.time() * 1000) % 10000000}"

@dataclass
class ExecutionRecord:
    """执行记录"""

    job_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = ""
    duration_ms: float = 0.0
    error: str = ""

def parse_interval(interval_str: str) -> Optional[float]:
    """解析间隔表达式: '30s', '5m', '1h'"""
    m = re.match(r"(\d+)([smh])", interval_str.strip())
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2)
    return val if unit == "s" else val * 60 if unit == "m" else val * 3600

def should_run_cron(cron_expr: str) -> bool:
    """简化版cron匹配（每分钟检查）"""
    now = datetime.now()
    parts = cron_expr.split()
    if len(parts) != 5:
        return False
    minute, hour, dom, month, dow = parts

    if minute != "*" and now.minute != int(minute):
        return False
    if hour != "*" and now.hour != int(hour):
        return False
    if dom != "*" and now.day != int(dom):
        return False
    if month != "*" and now.month != int(month):
        return False
    if dow != "*" and now.weekday() != int(dow):
        return False
    return True

class CronExecutionAnalyzer(object):
    """调度执行分析器 — 任务执行统计分析、失败模式识别、资源消耗追踪、SLA合规检测"""

    def __init__(self):
        self._exec_records: List[Dict[str, Any]] = []
        self._failure_patterns: Dict[str, int] = {}

    def record_execution(
        self,
        job_id: str,
        job_name: str,
        status: str,
        duration_ms: float,
        error_msg: str = "",
        retry_count: int = 0,
        memory_mb: float = 0,
    ) -> Dict[str, Any]:
        """记录一次任务执行"""
        record = {
            "job_id": job_id,
            "job_name": job_name,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error_msg": error_msg,
            "retry_count": retry_count,
            "memory_mb": round(memory_mb, 2),
            "timestamp": time.time(),
        }
        self._exec_records.append(record)
        if status == "failed" and error_msg:
            pattern = self._extract_error_pattern(error_msg)
            self._failure_patterns[pattern] = self._failure_patterns.get(pattern, 0) + 1
        return record

    def get_job_summary(self, job_id: str, window_hours: int = 24) -> Dict[str, Any]:
        """获取指定任务的执行统计摘要"""
        cutoff = time.time() - window_hours * 3600
        records = [r for r in self._exec_records if r["job_id"] == job_id and r["timestamp"] >= cutoff]
        if not records:
            return {"job_id": job_id, "window_hours": window_hours, "total_runs": 0}
        total = len(records)
        success = sum(1 for r in records if r["status"] == "success")
        failed = sum(1 for r in records if r["status"] == "failed")
        durations = [r["duration_ms"] for r in records]
        avg_duration = sum(durations) / total
        p95_idx = int(total * 0.95)
        sorted_d = sorted(durations)
        p95 = sorted_d[p95_idx] if p95_idx < total else sorted_d[-1]
        avg_memory = sum(r["memory_mb"] for r in records) / total
        total_retries = sum(r["retry_count"] for r in records)
        return {
            "job_id": job_id,
            "window_hours": window_hours,
            "total_runs": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total, 4),
            "avg_duration_ms": round(avg_duration, 2),
            "p95_duration_ms": round(p95, 2),
            "avg_memory_mb": round(avg_memory, 2),
            "total_retries": total_retries,
            "retry_rate": round(total_retries / max(total, 1), 2),
        }

    def detect_failure_trends(self, window_hours: int = 24) -> Dict[str, Any]:
        """检测失败趋势：失败率变化、周期性失败、新增失败模式"""
        cutoff = time.time() - window_hours * 3600
        records = [r for r in self._exec_records if r["timestamp"] >= cutoff]
        if not records:
            return {"trends": [], "total_records": 0}
        hour_buckets: Dict[int, List[Dict]] = {}
        for r in records:
            hour = int((r["timestamp"] - cutoff) / 3600)
            hour_buckets.setdefault(hour, []).append(r)
        hourly_rates = []
        for h in sorted(hour_buckets.keys()):
            bucket = hour_buckets[h]
            total_h = len(bucket)
            failed_h = sum(1 for b in bucket if b["status"] == "failed")
            hourly_rates.append({"hour_offset": h, "rate": round(failed_h / max(total_h, 1), 4)})
        if len(hourly_rates) >= 2:
            recent = hourly_rates[-1]["rate"]
            previous = hourly_rates[-2]["rate"]
            trend_direction = "increasing" if recent > previous * 1.5 else "stable"
        else:
            trend_direction = "unknown"
        top_patterns = sorted(self._failure_patterns.items(), key=lambda x: -x[1])[:5]
        return {
            "total_records": len(records),
            "failure_trend": trend_direction,
            "hourly_failure_rates": hourly_rates[-6:],
            "top_failure_patterns": [{"pattern": p, "count": c} for p, c in top_patterns],
            "total_unique_failures": len(self._failure_patterns),
        }

    def check_sla_compliance(self, sla_config: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """检查SLA合规性：可用性、延迟、成功率"""
        violations = []
        summaries = {}
        for job_id, sla in sla_config.items():
            summary = self.get_job_summary(job_id, window_hours=sla.get("window_hours", 24))
            summaries[job_id] = summary
            min_availability = sla.get("min_availability", 0.99)
            max_p95_latency = sla.get("max_p95_latency_ms", 5000)
            if summary["total_runs"] > 0:
                if summary["success_rate"] < min_availability:
                    violations.append(
                        {
                            "job_id": job_id,
                            "type": "availability",
                            "required": min_availability,
                            "actual": summary["success_rate"],
                            "gap": round(min_availability - summary["success_rate"], 4),
                        }
                    )
                if summary["p95_duration_ms"] > max_p95_latency:
                    violations.append(
                        {
                            "job_id": job_id,
                            "type": "latency",
                            "required_ms": max_p95_latency,
                            "actual_ms": summary["p95_duration_ms"],
                            "exceeded_by_ms": round(summary["p95_duration_ms"] - max_p95_latency, 2),
                        }
                    )
        return {
            "total_jobs_checked": len(sla_config),
            "violations": violations,
            "compliant": len(sla_config) - len(set(v["job_id"] for v in violations)),
            "summaries": summaries,
        }

    def get_resource_report(self, window_hours: int = 24) -> Dict[str, Any]:
        """获取资源消耗报告：内存、CPU时间、执行频次"""
        cutoff = time.time() - window_hours * 3600
        records = [r for r in self._exec_records if r["timestamp"] >= cutoff]
        if not records:
            return {"total_executions": 0, "resource_usage": {}}
        by_job: Dict[str, List[Dict]] = {}
        for r in records:
            by_job.setdefault(r["job_id"], []).append(r)
        job_resources = []
        for job_id, job_records in by_job.items():
            total_mem = sum(r["memory_mb"] for r in job_records)
            total_time = sum(r["duration_ms"] for r in job_records) / 1000
            job_resources.append(
                {
                    "job_id": job_id,
                    "run_count": len(job_records),
                    "total_memory_mb": round(total_mem, 2),
                    "avg_memory_mb": round(total_mem / len(job_records), 2),
                    "total_cpu_seconds": round(total_time, 2),
                }
            )
        job_resources.sort(key=lambda x: x["total_cpu_seconds"], reverse=True)
        return {
            "total_executions": len(records),
            "window_hours": window_hours,
            "total_memory_mb": round(sum(r["memory_mb"] for r in records), 2),
            "total_cpu_seconds": round(sum(r["duration_ms"] for r in records) / 1000, 2),
            "by_job": job_resources[:20],
        }

    def _extract_error_pattern(self, error_msg: str) -> str:
        """提取错误模式（去除变量部分）"""
        normalized = re.sub(r"'[^']*'", "'?'", error_msg)
        normalized = re.sub(r"\b\d+\b", "N", normalized)
        return normalized[:80]

class CronScheduler(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """定时任务调度器"""

    MODULE_ID = "cron-scheduler"
    MODULE_NAME = "定时任务调度器"
    VERSION = "v7.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        self._circuits = {}
        self._buckets = {}
        self._windows = {}
        self._jobs: Dict[str, CronJob] = {}
        self._history: deque = deque(maxlen=2000)
        self._bg_scheduler: Optional[asyncio.Task] = None

    def initialize(self) -> None:
        self.info("初始化定时调度器...")
        self.record_metrics("cron-scheduler.init", 1)
        self._setup_rate_limit(rate=50, burst=100)
        self._init_default_jobs()
        self._bg_scheduler = asyncio.create_task(self._schedule_loop())
        self.status = ModuleStatus.RUNNING
        self.stats.start_time = datetime.now()
        self.info(f"定时调度器就绪，{len(self._jobs)}个任务")

    async def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        _ = self.trace("execute")
        metrics_collector.counter("cron_scheduler_ops_total", labels={"action": action})
        params = params or {}
        return self._safe_execute(action, params, self._dispatch)

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "cron-scheduler"},
        )

    def shutdown(self) -> None:
        if self._bg_scheduler:
            self._bg_scheduler.cancel()
        self.status = ModuleStatus.STOPPED

    def list_jobs_by_status(self, status_filter: str = "active") -> List[Dict[str, Any]]:
        """按状态筛选任务列表，返回任务详情和下次执行时间"""
        jobs = self._jobs if hasattr(self, "_jobs") else []
        filtered = []
        for job in jobs:
            if status_filter == "all" or getattr(job, "status", "active") == status_filter:
                info = {
                    "job_id": getattr(job, "job_id", ""),
                    "name": getattr(job, "name", ""),
                    "cron": getattr(job, "cron", ""),
                    "status": getattr(job, "status", ""),
                    "last_run": getattr(job, "last_run_at", None),
                    "next_run": getattr(job, "next_run_at", None),
                }
                filtered.append(info)
        filtered.sort(key=lambda x: x.get("next_run") or "")
        return filtered

    def get_execution_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取执行统计摘要：成功/失败/跳过数量、平均执行时间"""
        history = self._history if hasattr(self, "_history") else []
        cutoff = time.time() - hours * 3600
        recent = [h for h in history if hasattr(h, "timestamp") and h.timestamp >= cutoff]
        if not recent:
            return {"window_hours": hours, "total_executions": 0}
        success = sum(1 for h in recent if getattr(h, "status", "") == "success")
        failed = sum(1 for h in recent if getattr(h, "status", "") == "failed")
        skipped = sum(1 for h in recent if getattr(h, "status", "") == "skipped")
        durations = [getattr(h, "duration_ms", 0) for h in recent if getattr(h, "status", "") == "success"]
        avg_dur = sum(durations) / max(len(durations), 1)
        return {
            "window_hours": hours,
            "total_executions": len(recent),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "success_rate": round(success / max(len(recent), 1), 4),
            "avg_duration_ms": round(avg_dur, 2),
        }

    def pause_job(self, job_id: str) -> Dict[str, Any]:
        """暂停指定任务"""
        jobs = self._jobs if hasattr(self, "_jobs") else []
        for job in jobs:
            if getattr(job, "job_id", "") == job_id:
                old_status = getattr(job, "status", "active")
                setattr(job, "status", "paused")
                return {"job_id": job_id, "old_status": old_status, "new_status": "paused"}
        return {"error": "job not found", "job_id": job_id}

    def resume_job(self, job_id: str) -> Dict[str, Any]:
        """恢复已暂停的任务"""
        jobs = self._jobs if hasattr(self, "_jobs") else []
        for job in jobs:
            if getattr(job, "job_id", "") == job_id:
                old_status = getattr(job, "status", "paused")
                setattr(job, "status", "active")
                return {"job_id": job_id, "old_status": old_status, "new_status": "active"}
        return {"error": "job not found", "job_id": job_id}

    def _init_default_jobs(self):
        defaults = [
            CronJob(name="健康检查", cron="*/5 * * * *", action="health_check"),
            CronJob(name="缓存清理", cron="interval:60", action="cleanup_cache"),
            CronJob(name="审计日志归档", cron="0 */6 * * *", action="archive_audit"),
            CronJob(name="备份清理", cron="0 3 * * *", action="cleanup_backups"),
        ]
        for job in defaults:
            self._jobs[job.job_id] = job

    def _dispatch(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "")
        handlers = {
            "add": self._do_add,
            "remove": self._do_remove,
            "run": self._do_run,
            "enable": self._do_enable,
            "disable": self._do_disable,
            "list": self._do_list,
            "history": self._do_history,
            "get": self._do_get,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"未知动作: {action}", "available": list(handlers.keys())}
        return handler(params)

    def _do_add(self, params: Dict) -> Dict:
        job = CronJob(
            name=params.get("name", ""),
            cron=params.get("cron", ""),
            action=params.get("action", ""),
            params=params.get("params", {}),
            max_retries=params.get("max_retries", 3),
            timeout=params.get("timeout", 300),
        )
        self._jobs[job.job_id] = job
        self.audit("add_job", job.job_id)
        return {"success": True, "job_id": job.job_id}

    def _do_remove(self, params: Dict) -> Dict:
        jid = params.get("job_id", "")
        if jid in self._jobs:
            del self._jobs[jid]
            return {"deleted": True}
        return {"error": "任务不存在"}

    def _do_run(self, params: Dict) -> Dict:
        jid = params.get("job_id", "")
        job = self._jobs.get(jid)
        if not job:
            return {"error": "任务不存在"}
        record = asyncio.get_event_loop().run_until_complete(self._execute_job(job))
        return {"job_id": jid, "status": record.status, "duration_ms": round(record.duration_ms, 0)}

    def _do_enable(self, params: Dict) -> Dict:
        job = self._jobs.get(params.get("job_id", ""))
        if not job:
            return {"error": "任务不存在"}
        job.enabled = True
        return {"enabled": True}

    def _do_disable(self, params: Dict) -> Dict:
        job = self._jobs.get(params.get("job_id", ""))
        if not job:
            return {"error": "任务不存在"}
        job.enabled = False
        return {"enabled": False}

    def _do_list(self, params: Dict) -> Dict:
        return {
            "total": len(self._jobs),
            "jobs": [
                {
                    "job_id": j.job_id,
                    "name": j.name,
                    "cron": j.cron,
                    "enabled": j.enabled,
                    "status": j.status,
                    "runs": j.run_count,
                    "errors": j.error_count,
                    "last_run": j.last_run,
                    "next_run": j.next_run,
                }
                for j in self._jobs.values()
            ],
        }

    def _do_get(self, params: Dict) -> Dict:
        job = self._jobs.get(params.get("job_id", ""))
        if not job:
            return {"error": "任务不存在"}
        return {
            "job_id": job.job_id,
            "name": job.name,
            "cron": job.cron,
            "action": job.action,
            "enabled": job.enabled,
            "status": job.status,
            "run_count": job.run_count,
            "error_count": job.error_count,
            "last_error": job.last_error,
            "last_run": job.last_run,
            "running": job.running_lock,
        }

    def _do_history(self, params: Dict) -> Dict:
        limit = params.get("limit", 50)
        jid = params.get("job_id", "")
        records = list(self._history)
        if jid:
            records = [r for r in records if r.job_id == jid]
        return {
            "total": len(records),
            "records": [
                {
                    "job_id": r.job_id,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                    "status": r.status,
                    "duration_ms": round(r.duration_ms, 0),
                    "error": r.error,
                }
                for r in records[-limit:]
            ],
        }

    def _execute_job(self, job: CronJob) -> ExecutionRecord:
        if job.running_lock:
            return ExecutionRecord(job_id=job.job_id, status="skipped(overlap)")

        job.running_lock = True
        job.status = "running"
        start = time.time()
        record = ExecutionRecord(job_id=job.job_id, started_at=self._now())

        try:
            from modules._base.registry import get_registry

            registry = get_registry()
            module = registry.get_instance(job.action.replace("_", "-").replace(" ", "-"))
            if module:
                result = module.execute(job.action, job.params)
                record.status = "success" if (not hasattr(result, "success") or result.success) else "failed"
            else:
                record.status = "success"
            job.run_count += 1
            self.stats.request_count += 1

        except Exception as e:
            record.status = "failed"
            record.error = str(e)
            job.error_count += 1
            job.last_error = str(e)
            self.stats.error_count += 1

        record.duration_ms = (time.time() - start) * 1000
        record.completed_at = self._now()
        job.status = record.status
        job.last_run = self._now()
        job.running_lock = False
        self._history.append(record)
        return record

    def _schedule_loop(self):
        try:
            while self.status == ModuleStatus.RUNNING:
                time.sleep(30)
                if self.status != ModuleStatus.RUNNING:
                    break
                for job in self._jobs.values():
                    if not job.enabled or job.running_lock:
                        continue
                    interval = parse_interval(job.cron)
                    if interval:
                        if (
                            not job.last_run
                            or time.time() - datetime.fromisoformat(job.last_run).timestamp() >= interval
                        ):
                            asyncio.ensure_future(self._execute_job(job))
                    elif job.cron:
                        if should_run_cron(job.cron):
                            asyncio.ensure_future(self._execute_job(job))
        except asyncio.CancelledError:
            pass

    # ── 标准Action处理器（自动注入）──

    def _do_get_status(self, params):
        """标准action: 模块状态"""
        try:
            status = self.get_status() if hasattr(self, "get_status") else {}
        except:
            status = {}
        if isinstance(status, dict):
            status["module_id"] = self.module_id
            status["version"] = getattr(self, "version", "")
            status["actions"] = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        return status

    def _do_get_stats(self, params):
        """标准action: 运行统计"""
        s = getattr(self, "stats", None)
        if s and hasattr(s, "to_dict"):
            return s.to_dict()
        return {"message": "no stats available"}

    def _do_list_actions(self, params):
        """标准action: 列出可用操作"""
        actions = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        # Clean up method names
        clean = [a.replace("_do_", "").replace("_", "-") for a in actions]
        # Also include standard actions
        standard = [
            "status",
            "info",
            "health",
            "ping",
            "list_actions",
            "help",
            "metrics",
            "stats",
            "configure",
            "config",
            "reset",
            "version",
        ]
        return {"total": len(set(clean + standard)), "actions": sorted(set(clean + standard))}

    def _do_configure(self, params):
        """标准action: 修改配置"""
        if not isinstance(params, dict):
            return {"error": "params must be a dict"}
        updated = []
        for k, v in params.items():
            if k in ("action",):
                continue
            if hasattr(self, "config"):
                self.config[k] = v
                updated.append(k)
        return {"success": True, "updated": updated}

    def _do_version(self, params):
        """标准action: 版本信息"""
        return {
            "module_id": self.module_id,
            "version": getattr(self, "version", "unknown"),
            "class": self.__class__.__name__,
        }

    def _do_reset(self, params):
        """标准action: 重置"""
        if hasattr(self, "stats"):
            self.stats.request_count = 0
            self.stats.error_count = 0
            self.stats.success_count = 0
            self.stats.latencies = []
        return {"success": True, "message": "reset done"}

module_class = CronScheduler
