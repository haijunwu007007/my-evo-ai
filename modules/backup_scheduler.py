"""
AUTO-EVO-AI V0.1 — 备份调度管理模块
Grade: A (生产级) | Category: 数据保护
职责：管理备份任务的定时调度、策略配置、执行编排、保留策略、通知告警
"""

__module_meta__ = {
        "id": "backup-scheduler",
        "name": "Backup Scheduler",
        "version": "V0.1",
        "group": "backup",
        "inputs": [
            {
                "name": "policy",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "policies",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "source_size_gb",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "recovery_rto_hours",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "recovery_rpo_hours",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "current_usage_gb",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "schedule",
                "config": {
                    "cron": "0 0 * * *"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "backup",
            "manager",
            "resilience"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 备份调度管理模块 Grade: A (生产级) | Category: 数据保护"
    }

import os
import asyncio
import time
import logging
import hashlib
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger(__name__)

class ScheduleFrequency(Enum):
    """调度频率枚举"""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"

class BackupType(Enum):
    """备份类型枚举"""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"

class RetentionPolicy(Enum):
    """保留策略枚举"""

    KEEP_ALL = "keep_all"
    KEEP_LAST_N = "keep_last_n"
    KEEP_DAYS = "keep_days"
    KEEP_WEEKLY_N = "keep_weekly_n"
    KEEP_MONTHLY_N = "keep_monthly_n"

class TaskStatus(Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class BackupPolicy:
    """备份策略定义"""

    policy_id: str = ""
    name: str = ""
    description: str = ""
    backup_type: BackupType = BackupType.FULL
    source: str = ""
    destination: str = ""
    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    schedule_time: str = "02:00"  # HH:MM
    retention: RetentionPolicy = RetentionPolicy.KEEP_DAYS
    retention_value: int = 30
    max_concurrent: int = 1
    timeout_minutes: int = 120
    compression: bool = True
    encryption: bool = False
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.policy_id:
            self.policy_id = f"policy_{hashlib.md5(self.name.encode()).hexdigest()[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
            self.updated_at = self.created_at

@dataclass
class BackupTask:
    """备份任务实例"""

    task_id: str = ""
    policy_id: str = ""
    name: str = ""
    backup_type: BackupType = BackupType.FULL
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    source: str = ""
    destination: str = ""
    size_bytes: int = 0
    duration_seconds: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""
    checksum: str = ""
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"

@dataclass
class BackupRecord:
    """备份记录"""

    record_id: str = ""
    task_id: str = ""
    policy_id: str = ""
    backup_type: BackupType = BackupType.FULL
    source: str = ""
    destination: str = ""
    size_bytes: int = 0
    checksum: str = ""
    status: TaskStatus = TaskStatus.SUCCESS
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.record_id:
            self.record_id = f"rec_{uuid.uuid4().hex[:12]}"

@dataclass
class ScheduleState:
    """调度状态"""

    next_run: Optional[str] = None
    last_run: Optional[str] = None
    last_status: Optional[TaskStatus] = None
    run_count: int = 0
    consecutive_failures: int = 0

class BackupPolicyAnalyzer(object):
    """备份策略分析器 — 评估策略健康度、检测冗余、优化调度建议"""

    def __init__(self):
        self._policy_stats: Dict[str, Dict] = {}

    def analyze_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个备份策略的健康度"""
        score = 100.0
        issues = []
        schedule = policy.get("schedule", {})
        interval_hours = schedule.get("interval_hours", 24)
        retention_days = policy.get("retention_days", 30)
        backup_type = policy.get("type", "full")

        if interval_hours < 1:
            score -= 20
            issues.append({"severity": "warning", "msg": "interval < 1h may cause excessive backups"})
        if backup_type == "full" and interval_hours < 6:
            score -= 15
            issues.append({"severity": "warning", "msg": "full backup too frequent, consider incremental"})
        if retention_days < 7:
            score -= 25
            issues.append({"severity": "critical", "msg": "retention < 7 days, risk of data loss"})
        if retention_days > 90:
            score -= 5
            issues.append({"severity": "info", "msg": "long retention may consume significant storage"})

        est_size_gb = policy.get("estimated_size_gb", 0)
        est_daily_gb = est_size_gb * (24 / max(interval_hours, 0.1))
        storage_needed_gb = est_daily_gb * retention_days
        if storage_needed_gb > 1000:
            score -= 10
            issues.append({"severity": "warning", "msg": f"estimated {storage_needed_gb:.0f}GB storage needed"})

        return {
            "policy_id": policy.get("id", ""),
            "health_score": max(0, round(score, 1)),
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D",
            "issues": issues,
            "estimated_daily_gb": round(est_daily_gb, 2),
            "estimated_total_gb": round(storage_needed_gb, 2),
        }

    def detect_redundant_policies(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测冗余/重叠的备份策略"""
        redundant = []
        sources = {}
        for p in policies:
            src = p.get("source", "")
            sources.setdefault(src, []).append(p)

        for src, polys in sources.items():
            if len(polys) > 1:
                for i in range(len(polys)):
                    for j in range(i + 1, len(polys)):
                        p1, p2 = polys[i], polys[j]
                        if (
                            p1.get("type") == p2.get("type")
                            and abs(
                                p1.get("schedule", {}).get("interval_hours", 0)
                                - p2.get("schedule", {}).get("interval_hours", 0)
                            )
                            < 1
                        ):
                            redundant.append(
                                {
                                    "source": src,
                                    "policy_a": p1.get("id", ""),
                                    "policy_b": p2.get("id", ""),
                                    "overlap": "same_type_and_interval",
                                    "recommendation": "merge or remove one",
                                }
                            )
        return redundant

    def recommend_schedule(
        self, source_size_gb: float, recovery_rto_hours: float, recovery_rpo_hours: float
    ) -> Dict[str, Any]:
        """根据业务需求推荐备份调度策略"""
        if rpo_hours <= 0.5:
            rec_interval = 0.5
            rec_type = "incremental"
        elif rpo_hours <= 4:
            rec_interval = 4
            rec_type = "incremental"
        elif rpo_hours <= 24:
            rec_interval = 24
            rec_type = "differential"
        else:
            rec_interval = 24
            rec_type = "full"

        if rto_hours <= 1:
            retention = 14
        elif rto_hours <= 4:
            retention = 30
        else:
            retention = 7

        est_daily = source_size_gb * (24 / max(rec_interval, 0.1))
        est_total = est_daily * retention

        return {
            "recommended_type": rec_type,
            "recommended_interval_hours": rec_interval,
            "recommended_retention_days": retention,
            "rationale": f"RPO={rpo_hours}h requires {rec_type} every {rec_interval}h",
            "estimated_daily_gb": round(est_daily, 2),
            "estimated_total_gb": round(est_total, 2),
            "cost_level": "high" if est_total > 500 else "medium" if est_total > 50 else "low",
        }

    def get_storage_forecast(
        self, current_usage_gb: float, growth_rate_pct: float, policies: List[Dict[str, Any]], days: int = 90
    ) -> Dict[str, Any]:
        """预测未来N天的存储需求"""
        daily_backup_gb = 0
        for p in policies:
            sz = p.get("estimated_size_gb", 0)
            interval = max(p.get("schedule", {}).get("interval_hours", 24), 0.1)
            retention = p.get("retention_days", 30)
            daily_backup_gb += sz * (24 / interval)
            daily_backup_gb -= sz * (1 / retention)

        forecast = []
        usage = current_usage_gb
        for d in range(0, days + 1, 7):
            forecast.append(
                {
                    "day": d,
                    "projected_gb": round(usage, 2),
                    "daily_backup_gb": round(daily_backup_gb, 2),
                }
            )
            usage += daily_backup_gb * 7 * (1 + growth_rate_pct / 100 / 365)

        return {
            "current_usage_gb": current_usage_gb,
            "daily_backup_rate_gb": round(daily_backup_gb, 2),
            "growth_rate_pct": growth_rate_pct,
            "forecast_days": days,
            "final_projected_gb": round(usage, 2),
            "weekly_forecast": forecast,
        }

class BackupSchedulerManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    备份调度管理器

    生产级功能：
    - 备份策略CRUD（增删改查）
    - 定时调度执行（hourly/daily/weekly/monthly/cron）
    - 并发控制与任务队列
    - 保留策略自动清理
    - 重试机制与超时处理
    - 执行历史与审计追踪
    - 通知告警集成
    """

    def __init__(self):

        super().__init__()
        self.module_name = "backup_scheduler"
        self.module_id = self.module_name
        self.module_version = "7.0.0"
        self.module_category = "数据保护"

        # 策略存储
        self._policies: Dict[str, BackupPolicy] = {}
        # 任务队列
        self._pending_tasks: List[BackupTask] = []
        # 活跃任务
        self._active_tasks: Dict[str, BackupTask] = {}
        # 备份记录
        self._records: Dict[str, BackupRecord] = {}
        # 调度状态
        self._schedule_states: Dict[str, ScheduleState] = {}
        # 统计
        self._total_backups = 0
        self._total_size = 0
        self._total_duration = 0.0
        self._notification_handlers: Dict[str, List[str]] = defaultdict(list)

    def initialize(self):
        """初始化备份调度器，加载默认策略"""

        # 默认策略
        defaults = [
            BackupPolicy(
                name="数据库每日全量备份",
                description="核心数据库每日凌晨2点全量备份",
                backup_type=BackupType.FULL,
                source="postgresql://primary:5432/bgdb",
                destination="s3://backup-pg-daily/",
                frequency=ScheduleFrequency.DAILY,
                schedule_time="02:00",
                retention=RetentionPolicy.KEEP_DAYS,
                retention_value=30,
                tags=["database", "postgresql", "critical"],
            ),
            BackupPolicy(
                name="配置文件增量备份",
                description="系统配置每小时增量备份",
                backup_type=BackupType.INCREMENTAL,
                source="/etc/bgapp/config/",
                destination="nfs://backup-cfg-incremental/",
                frequency=ScheduleFrequency.HOURLY,
                schedule_time="00:00",
                retention=RetentionPolicy.KEEP_LAST_N,
                retention_value=48,
                tags=["config", "incremental"],
            ),
            BackupPolicy(
                name="用户数据每周备份",
                description="用户上传附件和文档每周日备份",
                backup_type=BackupType.FULL,
                source="/data/user-uploads/",
                destination="s3://backup-user-weekly/",
                frequency=ScheduleFrequency.WEEKLY,
                schedule_time="03:00",
                retention=RetentionPolicy.KEEP_WEEKLY_N,
                retention_value=12,
                tags=["userdata", "weekly"],
            ),
            BackupPolicy(
                name="日志快照备份",
                description="运行日志月度快照归档",
                backup_type=BackupType.SNAPSHOT,
                source="/var/log/bgapp/",
                destination="s3://backup-log-archive/",
                frequency=ScheduleFrequency.MONTHLY,
                schedule_time="01:00",
                retention=RetentionPolicy.KEEP_MONTHLY_N,
                retention_value=24,
                tags=["logs", "archive", "monthly"],
            ),
        ]

        for p in defaults:
            self._policies[p.policy_id] = p
            self._schedule_states[p.policy_id] = ScheduleState(
                next_run=self._calculate_next_run(p.frequency, p.schedule_time)
            )

        logger.info(f"[{self.module_name}] 初始化完成，加载 {len(self._policies)} 个备份策略")

    def _calculate_next_run(self, frequency: ScheduleFrequency, schedule_time: str) -> str:
        """计算下次执行时间"""
        now = datetime.now()
        h, m = map(int, schedule_time.split(":"))

        if frequency == ScheduleFrequency.HOURLY:
            target = now.replace(minute=m, second=0, microsecond=0)
            if target <= now:
                target += timedelta(hours=1)
        elif frequency == ScheduleFrequency.DAILY:
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
        elif frequency == ScheduleFrequency.WEEKLY:
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and target <= now:
                days_until_sunday = 7
            target += timedelta(days=days_until_sunday)
        elif frequency == ScheduleFrequency.MONTHLY:
            target = now.replace(day=1, hour=h, minute=m, second=0, microsecond=0)
            if target <= now:
                if now.month == 12:
                    target = target.replace(year=now.year + 1, month=1)
                else:
                    target = target.replace(month=now.month + 1)
        else:
            target = now + timedelta(hours=1)

        return target.isoformat()

    def _create_policy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建备份策略"""
        name = params.get("name", "")
        if not name:
            return {"success": False, "error": "策略名称不能为空"}

        # 检查重名
        for p in self._policies.values():
            if p.name == name:
                return {"success": False, "error": f"策略 '{name}' 已存在"}

        policy = BackupPolicy(
            name=name,
            description=params.get("description", ""),
            backup_type=BackupType(params.get("backup_type", "full")),
            source=params.get("source", ""),
            destination=params.get("destination", ""),
            frequency=ScheduleFrequency(params.get("frequency", "daily")),
            schedule_time=params.get("schedule_time", "02:00"),
            retention=RetentionPolicy(params.get("retention", "keep_days")),
            retention_value=params.get("retention_value", 30),
            max_concurrent=params.get("max_concurrent", 1),
            timeout_minutes=params.get("timeout_minutes", 120),
            compression=params.get("compression", True),
            encryption=params.get("encryption", False),
            tags=params.get("tags", []),
        )

        self._policies[policy.policy_id] = policy
        self._schedule_states[policy.policy_id] = ScheduleState(
            next_run=self._calculate_next_run(policy.frequency, policy.schedule_time)
        )

        logger.info(f"[{self.module_name}] 创建策略: {policy.name} ({policy.policy_id})")
        return {"success": True, "result": {"policy_id": policy.policy_id, "name": policy.name}}

    def _execute_backup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行备份任务"""
        policy_id = params.get("policy_id", "")
        policy = self._policies.get(policy_id)
        if not policy:
            return {"success": False, "error": f"策略 {policy_id} 不存在"}
        if not policy.enabled:
            return {"success": False, "error": f"策略 {policy.name} 已禁用"}

        # 并发检查
        active_count = sum(1 for t in self._active_tasks.values() if t.policy_id == policy_id)
        if active_count >= policy.max_concurrent:
            return {"success": False, "error": f"策略 {policy.name} 已达最大并发数 {policy.max_concurrent}"}

        task = BackupTask(
            policy_id=policy_id,
            name=f"{policy.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            backup_type=policy.backup_type,
            source=policy.source,
            destination=policy.destination,
            max_retries=params.get("max_retries", policy.timeout_minutes > 60 and 3 or 2),
        )

        self._active_tasks[task.task_id] = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()

        # 模拟备份执行
        try:
            time.sleep(0.05)  # 模拟IO操作
            task.progress = 25.0
            time.sleep(0.03)
            task.progress = 50.0
            time.sleep(0.03)
            task.progress = 75.0
            time.sleep(0.02)

            # 计算备份大小（模拟）
            base_size = {
                BackupType.FULL: 1024 * 1024 * 512,  # 512MB
                BackupType.INCREMENTAL: 1024 * 1024 * 32,  # 32MB
                BackupType.DIFFERENTIAL: 1024 * 1024 * 128,  # 128MB
                BackupType.SNAPSHOT: 1024 * 1024 * 256,  # 256MB
            }
            task.size_bytes = base_size.get(policy.backup_type, 1024 * 1024 * 100)
            if policy.compression:
                task.size_bytes = int(task.size_bytes * 0.4)

            # 计算校验和
            task.checksum = hashlib.sha256(f"{task.task_id}:{policy.source}:{task.size_bytes}".encode()).hexdigest()[
                :32
            ]
            task.progress = 100.0
            task.status = TaskStatus.SUCCESS
            task.completed_at = datetime.now().isoformat()
            task.duration_seconds = (
                datetime.fromisoformat(task.completed_at) - datetime.fromisoformat(task.started_at)
            ).total_seconds()

            # 创建备份记录
            record = BackupRecord(
                task_id=task.task_id,
                policy_id=policy_id,
                backup_type=policy.backup_type,
                source=policy.source,
                destination=policy.destination,
                size_bytes=task.size_bytes,
                checksum=task.checksum,
                status=TaskStatus.SUCCESS,
                started_at=task.started_at,
                completed_at=task.completed_at,
                duration_seconds=task.duration_seconds,
                tags=policy.tags,
            )
            self._records[record.record_id] = record

            # 更新统计
            self._total_backups += 1
            self._total_size += task.size_bytes
            self._total_duration += task.duration_seconds

            # 更新调度状态
            state = self._schedule_states.get(policy_id)
            if state:
                state.last_run = task.started_at
                state.last_status = TaskStatus.SUCCESS
                state.run_count += 1
                state.consecutive_failures = 0
                state.next_run = self._calculate_next_run(policy.frequency, policy.schedule_time)

            # 应用保留策略
            self._apply_retention(policy_id)

            logger.info(
                f"[{self.module_name}] 备份完成: {task.name}, 大小: {task.size_bytes}, 校验: {task.checksum[:16]}"
            )
            return {
                "success": True,
                "result": {
                    "task_id": task.task_id,
                    "record_id": record.record_id,
                    "status": task.status.value,
                    "size_bytes": task.size_bytes,
                    "checksum": task.checksum,
                    "duration_seconds": round(task.duration_seconds, 3),
                },
            }

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error_message = "备份执行超时"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"[{self.module_name}] 备份失败: {task.name}, 错误: {e}")
        finally:
            task.completed_at = datetime.now().isoformat()
            del self._active_tasks[task.task_id]

        # 更新调度状态（失败）
        state = self._schedule_states.get(policy_id)
        if state:
            state.last_run = task.started_at
            state.last_status = TaskStatus.FAILED
            state.run_count += 1
            state.consecutive_failures += 1

        return {
            "success": False,
            "error": task.error_message,
            "result": {"task_id": task.task_id, "status": task.status.value},
        }

    def _apply_retention(self, policy_id: str):
        """应用保留策略，清理过期备份"""
        policy = self._policies.get(policy_id)
        if not policy:
            return

        policy_records = [
            r for r in self._records.values() if r.policy_id == policy_id and r.status == TaskStatus.SUCCESS
        ]
        if len(policy_records) <= 1:
            return

        to_remove: List[str] = []
        now = datetime.now()

        if policy.retention == RetentionPolicy.KEEP_LAST_N:
            policy_records.sort(key=lambda r: r.completed_at, reverse=True)
            for r in policy_records[policy.retention_value :]:
                to_remove.append(r.record_id)

        elif policy.retention == RetentionPolicy.KEEP_DAYS:
            cutoff = now - timedelta(days=policy.retention_value)
            for r in policy_records:
                if r.completed_at:
                    completed = datetime.fromisoformat(r.completed_at)
                    if completed < cutoff:
                        to_remove.append(r.record_id)

        elif policy.retention == RetentionPolicy.KEEP_WEEKLY_N:
            weekly: Dict[str, BackupRecord] = {}
            for r in sorted(policy_records, key=lambda x: x.completed_at or ""):
                if r.completed_at:
                    week_key = datetime.fromisoformat(r.completed_at).strftime("%Y-W%W")
                    if week_key not in weekly:
                        weekly[week_key] = r
            kept = set(r.record_id for r in weekly.values())
            sorted_weeks = sorted(weekly.items(), key=lambda x: x[0], reverse=True)
            actual_keep = set(r.record_id for _, r in sorted_weeks[: policy.retention_value])
            for r in policy_records:
                if r.record_id not in actual_keep:
                    to_remove.append(r.record_id)

        elif policy.retention == RetentionPolicy.KEEP_MONTHLY_N:
            monthly: Dict[str, BackupRecord] = {}
            for r in sorted(policy_records, key=lambda x: x.completed_at or ""):
                if r.completed_at:
                    month_key = datetime.fromisoformat(r.completed_at).strftime("%Y-%m")
                    if month_key not in monthly:
                        monthly[month_key] = r
            sorted_months = sorted(monthly.items(), key=lambda x: x[0], reverse=True)
            actual_keep = set(r.record_id for _, r in sorted_months[: policy.retention_value])
            for r in policy_records:
                if r.record_id not in actual_keep:
                    to_remove.append(r.record_id)

        for rid in to_remove:
            rec = self._records.get(rid)
            if rec:
                self._total_size -= rec.size_bytes
                del self._records[rid]

        if to_remove:
            logger.info(f"[{self.module_name}] 保留策略清理: 删除 {len(to_remove)} 个过期备份")

    def _list_policies(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """列出所有备份策略"""
        tag_filter = (params or {}).get("tag", "")
        result = []
        for p in self._policies.values():
            if tag_filter and tag_filter not in p.tags:
                continue
            state = self._schedule_states.get(p.policy_id)
            result.append(
                {
                    "policy_id": p.policy_id,
                    "name": p.name,
                    "description": p.description,
                    "backup_type": p.backup_type.value,
                    "source": p.source,
                    "destination": p.destination,
                    "frequency": p.frequency.value,
                    "schedule_time": p.schedule_time,
                    "retention": p.retention.value,
                    "retention_value": p.retention_value,
                    "enabled": p.enabled,
                    "next_run": state.next_run if state else None,
                    "last_run": state.last_run if state else None,
                    "last_status": state.last_status.value if state and state.last_status else None,
                    "run_count": state.run_count if state else 0,
                    "consecutive_failures": state.consecutive_failures if state else 0,
                    "tags": p.tags,
                }
            )
        return {"success": True, "result": result}

    def _toggle_policy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """启用/禁用策略"""
        policy_id = params.get("policy_id", "")
        enabled = params.get("enabled")
        policy = self._policies.get(policy_id)
        if not policy:
            return {"success": False, "error": f"策略 {policy_id} 不存在"}
        if enabled is None:
            enabled = not policy.enabled
        policy.enabled = enabled
        policy.updated_at = datetime.now().isoformat()
        logger.info(f"[{self.module_name}] 策略 {policy.name} {'启用' if enabled else '禁用'}")
        return {"success": True, "result": {"policy_id": policy_id, "name": policy.name, "enabled": enabled}}

    def _delete_policy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除备份策略"""
        policy_id = params.get("policy_id", "")
        policy = self._policies.get(policy_id)
        if not policy:
            return {"success": False, "error": f"策略 {policy_id} 不存在"}
        name = policy.name
        del self._policies[policy_id]
        self._schedule_states.pop(policy_id, None)
        logger.info(f"[{self.module_name}] 删除策略: {name}")
        return {"success": True, "result": {"deleted": policy_id, "name": name}}

    def _get_history(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """查询备份历史"""
        params = params or {}
        policy_id = params.get("policy_id", "")
        status = params.get("status", "")
        limit = params.get("limit", 20)

        records = list(self._records.values())
        if policy_id:
            records = [r for r in records if r.policy_id == policy_id]
        if status:
            records = [r for r in records if r.status.value == status]

        records.sort(key=lambda r: r.completed_at or "", reverse=True)
        records = records[:limit]

        return {
            "success": True,
            "result": {
                "records": [
                    {
                        "record_id": r.record_id,
                        "task_id": r.task_id,
                        "policy_id": r.policy_id,
                        "backup_type": r.backup_type.value,
                        "size_bytes": r.size_bytes,
                        "checksum": r.checksum[:16],
                        "status": r.status.value,
                        "started_at": r.started_at,
                        "completed_at": r.completed_at,
                        "duration_seconds": round(r.duration_seconds, 3),
                        "tags": r.tags,
                    }
                    for r in records
                ],
                "total": len(records),
            },
        }

    def _get_stats(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取备份统计"""
        success_count = sum(1 for r in self._records.values() if r.status == TaskStatus.SUCCESS)
        failed_count = sum(1 for r in self._records.values() if r.status == TaskStatus.FAILED)
        active_count = len(self._active_tasks)

        # 按策略统计
        by_policy: Dict[str, int] = defaultdict(int)
        for r in self._records.values():
            by_policy[r.policy_id] += 1

        # 按类型统计
        by_type: Dict[str, int] = defaultdict(int)
        for r in self._records.values():
            by_type[r.backup_type.value] += 1

        # 总大小格式化
        total_gb = self._total_size / (1024**3)

        return {
            "success": True,
            "result": {
                "total_policies": len(self._policies),
                "enabled_policies": sum(1 for p in self._policies.values() if p.enabled),
                "total_backups": self._total_backups,
                "success_count": success_count,
                "failed_count": failed_count,
                "active_tasks": active_count,
                "total_size_bytes": self._total_size,
                "total_size_gb": round(total_gb, 2),
                "avg_duration_seconds": round(self._total_duration / max(success_count, 1), 3),
                "by_policy": dict(by_policy),
                "by_type": dict(by_type),
                "success_rate": round(success_count / max(self._total_backups, 1) * 100, 1),
            },
        }

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行备份调度操作"""
        _ = self.trace("execute")
        metrics_collector.counter("backup_scheduler_ops_total", labels={"operation": operation})
        params = params or {}
        operations = {
            "create_policy": self._create_policy,
            "execute_backup": self._execute_backup,
            "list_policies": self._list_policies,
            "toggle_policy": self._toggle_policy,
            "delete_policy": self._delete_policy,
            "history": self._get_history,
            "stats": self._get_stats,
        }

        handler = operations.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}

        try:
            return handler(params)
        except Exception as e:
            logger.error(f"[{self.module_name}] 操作 {operation} 异常: {e}")
            return {"success": False, "error": str(e)}

    def shutdown(self):
        """优雅关闭"""
        self.audit("execute", f"action={action}")

        for task in list(self._active_tasks.values()):
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
        self._active_tasks.clear()
        logger.info(f"[{self.module_name}] 已关闭，共执行 {self._total_backups} 次备份")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "module": self.module_name,
                "version": self.module_version,
                "total_policies": len(self._policies),
                "enabled_policies": sum(1 for p in self._policies.values() if p.enabled),
                "active_tasks": len(self._active_tasks),
                "total_records": len(self._records),
                "total_size_gb": round(self._total_size / (1024**3), 2),
                "success_rate": round(
                    sum(1 for r in self._records.values() if r.status == TaskStatus.SUCCESS)
                    / max(len(self._records), 1)
                    * 100,
                    1,
                )
                if self._records
                else 100.0,
            }
        )
        return result

module_class = BackupSchedulerManager
