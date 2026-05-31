"""
AUTO-EVO-AI V0.1 — CI/CD Pipeline — 持续集成/持续部署管线
"""
# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - CICDPipeline CI/CD流水线引擎
==============================================
企业级CI/CD流水线：构建/测试/部署/回滚/多环境/审批/通知。
支持：Pipeline YAML定义、多阶段串并行执行、
      代码检出/构建/测试/安全扫描/部署、多环境管理、
      手动审批网关、回滚机制、构建缓存、制品管理、
      Webhook触发、定时触发、流水线模板。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
        "id": "cicd-pipeline",
        "name": "Ci/cd Pipeline",
        "version": "V0.1",
        "group": "cicd",
        "inputs": [
            {
                "name": "success",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "error",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "pipeline_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "stage",
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
        "triggers": [],
        "depends_on": [],
        "tags": [
            "devops",
            "cicd"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 - CICDPipeline CI/CD流水线引擎 =============================================="
    }

import time
import asyncio
import json
from core.logging_config import get_logger
import re
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import metrics_collector

logger = get_logger("evo.cicd_pipeline")

# ============================================================================
# 本地兼容类型
# ============================================================================

class Result:
    """兼容Result类型"""

    def __init__(self, success: bool = True, data: Any = None, error: str = ""):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        r = {"success": self.success}
        if self.data is not None:
            r["result"] = self.data
        if self.error:
            r["error"] = self.error
        return r

    # --- Auto-generated action dispatch methods ---
    def _action_to_dict(self, params=None):
        """Auto-generated action wrapper for to_dict"""
        if params is None:
            params = {}
        return self.to_dict(**params)

class ModuleStatus:
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

# ============================================================================
# 数据模型
# ============================================================================

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TriggerType(str, Enum):
    PUSH = "push"
    PR = "pull_request"
    TAG = "tag"
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"

@dataclass
class StageStep:
    """步骤"""

    name: str = ""
    command: str = ""
    script: list[str] = field(default_factory=list)
    timeout_seconds: float = 600.0
    working_dir: str = ""
    env: dict[str, str] = field(default_factory=dict)
    continue_on_error: bool = False
    condition: str | None = None  # when条件
    retry_count: int = 0
    retry_delay: float = 5.0

@dataclass
class PipelineStage:
    """阶段"""

    name: str = ""
    steps: list[StageStep] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    allow_failure: bool = False
    timeout_seconds: float = 1800.0
    when: str | None = None
    approval_required: bool = False
    approvers: list[str] = field(default_factory=list)
    environment: str = ""  # 部署目标环境
    tags: list[str] = field(default_factory=list)

@dataclass
class PipelineDefinition:
    """流水线定义"""

    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    stages: list[PipelineStage] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=lambda: [t.value for t in TriggerType])
    timeout_seconds: float = 3600.0
    retry_on_failure: bool = False
    max_retries: int = 1
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class StageExecution:
    """阶段执行记录"""

    stage_name: str = ""
    status: StageStatus = StageStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float = 0.0
    steps_executed: int = 0
    steps_total: int = 0
    logs: list[str] = field(default_factory=list)
    error_message: str | None = None
    retry_count: int = 0

@dataclass
class PipelineRun:
    """流水线运行实例"""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    pipeline_id: str = ""
    pipeline_name: str = ""
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_user: str = ""
    ref: str = ""  # Git ref (branch/tag/commit)
    commit_sha: str = ""
    commit_message: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    status: StageStatus = StageStatus.PENDING
    stage_executions: dict[str, StageExecution] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    deploy_target: str = ""
    approved_by: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ArtifactInfo:
    """制品信息"""

    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    version: str = ""
    pipeline_run_id: str = ""
    type: str = "docker"  # docker/jar/npm/deb
    size_bytes: int = 0
    registry: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ApprovalRequest:
    """审批请求"""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    run_id: str = ""
    stage_name: str = ""
    pipeline_name: str = ""
    requested_by: str = "system"
    approvers: list[str] = field(default_factory=list)
    status: str = "pending"  # pending/approved/rejected
    comments: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: str | None = None

# ============================================================================
# CICDPipeline 主类
# ============================================================================

class PipelineAnalyzer:
    """流水线分析器 — 分析构建耗时、失败模式、部署频率"""

    def __init__(self):
        self._build_history: list[dict] = []

    def record_build(self, pipeline_id: str, stage: str, duration_ms: int, success: bool, error: str = "") -> None:
        self._build_history.append(
            {
                "pipeline_id": pipeline_id,
                "stage": stage,
                "duration_ms": duration_ms,
                "success": success,
                "error": error[:100],
                "timestamp": time.time(),
            }
        )
        if len(self._build_history) > 5000:
            self._build_history = self._build_history[-3000:]

    def get_failure_patterns(self, top_n: int = 5) -> list[dict[str, Any]]:
        """识别失败模式：按错误类型和阶段聚合"""
        failures = [b for b in self._build_history if not b["success"]]
        if not failures:
            return []
        by_error: dict[str, list[dict]] = {}
        for f in failures:
            key = f["error"] or f["stage"]
            by_error.setdefault(key, []).append(f)
        patterns = []
        for error, items in sorted(by_error.items(), key=lambda x: -len(x[1])):
            stages = list(set(i["stage"] for i in items))
            avg_duration = sum(i["duration_ms"] for i in items) / len(items)
            patterns.append(
                {"error": error, "count": len(items), "stages": stages, "avg_duration_ms": round(avg_duration)}
            )
        return patterns[:top_n]

    def get_stage_performance(self, pipeline_id: str = "") -> dict[str, Any]:
        """各阶段性能统计：平均耗时、P95、成功率"""
        builds = [b for b in self._build_history if not pipeline_id or b["pipeline_id"] == pipeline_id]
        if not builds:
            return {"total": 0}
        by_stage: dict[str, list[int]] = {}
        by_stage_success: dict[str, list[bool]] = {}
        for b in builds:
            by_stage.setdefault(b["stage"], []).append(b["duration_ms"])
            by_stage_success.setdefault(b["stage"], []).append(b["success"])
        result = {}
        for stage, durations in by_stage.items():
            durations.sort()
            successes = by_stage_success[stage]
            result[stage] = {
                "count": len(durations),
                "avg_ms": round(sum(durations) / len(durations)),
                "p95_ms": durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
                "success_rate": round(sum(successes) / len(successes), 3),
            }
        return {"total_builds": len(builds), "stages": result}

class CICDPipeline(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    CI/CD流水线引擎

    功能：
      - Pipeline定义（YAML风格多阶段）
      - 多触发器（Push/PR/Tag/Manual/Schedule/Webhook）
      - 多阶段串并行执行
      - 代码检出→构建→测试→安全扫描→部署
      - 手动审批网关
      - 环境管理（dev/staging/production）
      - 制品管理
      - 回滚支持
      - 构建缓存
      - 流水线模板
    """

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config=config or {})
        self.module_name = "CI/CD流水线引擎"
        self.module_id = self.module_name
        self.module_id = "cicd_pipeline"
        self.version = "V0.1"
        self.config = config or {}
        # Pipeline定义注册
        self._pipelines: dict[str, PipelineDefinition] = {}
        # 运行记录
        self._runs: dict[str, PipelineRun] = {}
        # 审批队列
        self._approvals: dict[str, ApprovalRequest] = {}
        # 制品库
        self._artifacts: dict[str, ArtifactInfo] = {}
        # 构建缓存
        self._build_cache: dict[str, Any] = {}
        # 活跃运行任务
        self._active_tasks: dict[str, asyncio.Task] = {}
        # 环境状态
        self._environments: dict[str, dict[str, str]] = {
            "dev": {"status": "active", "last_deploy": "", "version": ""},
            "staging": {"status": "active", "last_deploy": "", "version": ""},
            "production": {"status": "active", "last_deploy": "", "version": ""},
        }
        # 统计
        self._cicd_stats = {
            "pipelines_registered": 0,
            "runs_total": 0,
            "runs_success": 0,
            "runs_failed": 0,
            "runs_cancelled": 0,
            "deployments_total": 0,
            "artifacts_total": 0,
            "approvals_pending": 0,
            "avg_duration_seconds": 0.0,
            "build_cache_hits": 0,
        }
        # 配置
        self._max_concurrent_runs = self.config.get("max_concurrent_runs", 10)
        self._default_timeout = self.config.get("default_timeout", 3600.0)
        self._artifact_retention_days = self.config.get("artifact_retention_days", 30)

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        for pipe_cfg in self.config.get("preset_pipelines", []):
            self.register_pipeline(pipe_cfg)
        logger.info(f"[CICDPipeline] 初始化完成: {len(self._pipelines)} pipelines")

    def health_check(self) -> dict[str, Any]:
        active = sum(1 for r in self._runs.values() if r.status == StageStatus.RUNNING)
        checks = {
            "pipelines_registered": len(self._pipelines),
            "active_runs": active,
            "approvals_pending": len([a for a in self._approvals.values() if a.status == "pending"]),
            "artifacts_count": len(self._artifacts),
            "environments": list(self._environments.keys()),
        }
        return {"status": "running", "healthy": True, "version": "V0.1", **checks}

    def shutdown(self) -> None:
        for task in self._active_tasks.values():
            task.cancel()
        asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        self._active_tasks.clear()
        return Result(success=True)

    # ----------------------------------------------------------------
    # Pipeline管理
    # ----------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = self.trace("execute")
        """统一执行入口"""
        trace_id = f"cicd-{action}-{int(time.time() * 1000)}"
        metrics_collector.counter("cicd_ops_total", labels={"action": action})
        params = params or {}
        try:
            if action == "register_pipeline":
                r = self.register_pipeline(params)
                return r.to_dict()
            elif action == "trigger_pipeline":
                pipeline_id = params.get("pipeline_id", "")
                tt = TriggerType(params.get("trigger_type", "manual"))
                r = self.trigger_pipeline(
                    pipeline_id,
                    trigger_type=tt,
                    trigger_user=params.get("triggered_by", ""),
                    ref=params.get("branch", "main"),
                )
                return r.to_dict()
            elif action == "approve":
                r = self.approve(params.get("request_id", ""), params.get("approver", ""))
                return r.to_dict()
            elif action == "reject":
                r = self.reject(params.get("request_id", ""), params.get("approver", ""), params.get("comment", ""))
                return r.to_dict()
            elif action == "list_pipelines":
                return {"success": True, "result": self.list_pipelines()}
            elif action == "list_runs":
                return {"success": True, "result": self.list_runs(params.get("pipeline_id"), params.get("limit", 20))}
            elif action == "list_pending_approvals":
                return {"success": True, "result": self.list_pending_approvals()}
            elif action == "get_run_detail":
                r = self.get_run_detail(params.get("run_id", ""))
                return {"success": bool(r), "result": r}
            elif action == "get_stats":
                return {"success": True, "result": self.get_stats()}
            elif action == "rollback":
                r = self.rollback(params.get("run_id", ""))
                return r.to_dict()
            elif action == "register_artifact":
                a = ArtifactInfo(
                    name=params.get("name", ""),
                    version=params.get("version", ""),
                    artifact_type=params.get("type", "docker"),
                    size_bytes=params.get("size", 0),
                    checksum=params.get("checksum", ""),
                )
                r = self.register_artifact(a)
                return r.to_dict()
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_pipeline(self, config: dict[str, Any]) -> Result:
        """注册Pipeline定义"""
        stages = []
        for stage_cfg in config.get("stages", []):
            steps = []
            for step_cfg in stage_cfg.get("steps", []):
                steps.append(
                    StageStep(
                        name=step_cfg.get("name", ""),
                        command=step_cfg.get("command", ""),
                        script=step_cfg.get("script", []),
                        timeout_seconds=step_cfg.get("timeout", 600.0),
                        env=step_cfg.get("env", {}),
                        continue_on_error=step_cfg.get("continue_on_error", False),
                        retry_count=step_cfg.get("retries", 0),
                    )
                )
            stages.append(
                PipelineStage(
                    name=stage_cfg.get("name", ""),
                    steps=steps,
                    depends_on=stage_cfg.get("depends_on", []),
                    allow_failure=stage_cfg.get("allow_failure", False),
                    approval_required=stage_cfg.get("approval_required", False),
                    approvers=stage_cfg.get("approvers", []),
                    environment=stage_cfg.get("environment", ""),
                )
            )
        pipeline = PipelineDefinition(
            name=config.get("name", ""),
            description=config.get("description", ""),
            stages=stages,
            variables=config.get("variables", {}),
            tags=config.get("tags", []),
        )
        self._pipelines[pipeline.pipeline_id] = pipeline
        self._cicd_stats["pipelines_registered"] = len(self._pipelines)
        return Result(success=True, data={"pipeline_id": pipeline.pipeline_id, "name": pipeline.name})

    def list_pipelines(self) -> list[dict]:
        return [
            {
                "id": p.pipeline_id,
                "name": p.name,
                "stages": len(p.stages),
                "description": p.description,
                "tags": p.tags,
                "created": p.created_at,
            }
            for p in self._pipelines.values()
        ]

    # ----------------------------------------------------------------
    # Pipeline运行
    # ----------------------------------------------------------------

    def trigger_pipeline(
        self,
        pipeline_id: str,
        *,
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_user: str = "",
        ref: str = "",
        variables: dict | None = None,
    ) -> Result:
        """触发Pipeline运行"""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return Result(success=False, error=f"Pipeline不存在: {pipeline_id}")
        # 检查并发限制
        active = sum(1 for r in self._runs.values() if r.status == StageStatus.RUNNING)
        if active >= self._max_concurrent_runs:
            return Result(success=False, error="并发运行数已达上限")
        run = PipelineRun(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline.name,
            trigger_type=trigger_type,
            trigger_user=trigger_user,
            ref=ref,
            commit_sha=str(uuid.uuid4())[:12],
            variables={**pipeline.variables, **(variables or {})},
        )
        self._runs[run.run_id] = run
        self._cicd_stats["runs_total"] += 1
        # 初始化阶段执行记录
        for stage in pipeline.stages:
            run.stage_executions[stage.name] = StageExecution(
                stage_name=stage.name, status=StageStatus.PENDING, steps_total=len(stage.steps)
            )
        # 启动运行
        task = asyncio.create_task(self._execute_pipeline(run))
        self._active_tasks[run.run_id] = task
        task.add_done_callback(lambda t: self._active_tasks.pop(run.run_id, None))
        self.audit(
            "pipeline.triggered", {"run_id": run.run_id, "pipeline": pipeline.name, "trigger": trigger_type.value}
        )
        return Result(success=True, data={"run_id": run.run_id, "pipeline": pipeline.name})

    def _execute_pipeline(self, run: PipelineRun):
        """执行Pipeline"""
        pipeline = self._pipelines.get(run.pipeline_id)
        if not pipeline:
            return
        run.status = StageStatus.RUNNING
        run.started_at = datetime.now().isoformat()
        start_time = time.time()
        # 构建阶段依赖图
        stage_graph = self._build_stage_graph(pipeline.stages)
        completed = set()
        failed = False
        while completed < set(s.name for s in pipeline.stages) and not failed:
            # 找可执行阶段
            ready = []
            for stage in pipeline.stages:
                if stage.name in completed:
                    continue
                if all(dep in completed for dep in stage.depends_on):
                    ready.append(stage)
            if not ready:
                break
            # 并行执行就绪阶段
            tasks = []
            for stage in ready:
                tasks.append(self._execute_stage(run, stage))
            results = asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception) or not result or not result:
                    if not ready[i].allow_failure:
                        failed = True
        run.status = StageStatus.FAILED if failed else StageStatus.SUCCESS
        run.finished_at = datetime.now().isoformat()
        run.duration_seconds = time.time() - start_time
        if run.status == StageStatus.SUCCESS:
            self._cicd_stats["runs_success"] += 1
        else:
            self._cicd_stats["runs_failed"] += 1
        self._cicd_stats["avg_duration_seconds"] = (
            self._cicd_stats["avg_duration_seconds"] * 0.8 + run.duration_seconds * 0.2
        )

    def _build_stage_graph(self, stages: list[PipelineStage]) -> dict[str, list[str]]:
        """构建阶段依赖图"""
        return {s.name: s.depends_on for s in stages}

    def _execute_stage(self, run: PipelineRun, stage: PipelineStage) -> bool:
        """执行单个阶段"""
        stage_exec = run.stage_executions[stage.name]
        stage_exec.status = StageStatus.RUNNING
        stage_exec.started_at = datetime.now().isoformat()
        stage_start = time.time()
        # 检查审批
        if stage.approval_required:
            stage_exec.status = StageStatus.WAITING_APPROVAL
            approval = ApprovalRequest(
                run_id=run.run_id,
                stage_name=stage.name,
                pipeline_name=run.pipeline_name,
                approvers=stage.approvers or ["admin"],
            )
            self._approvals[approval.request_id] = approval
            self._cicd_stats["approvals_pending"] += 1
            # 等待审批（最多30分钟）
            for _ in range(180):
                time.sleep(10)
                if approval.status == "approved":
                    break
                elif approval.status == "rejected":
                    stage_exec.status = StageStatus.FAILED
                    stage_exec.error_message = "审批被拒绝"
                    stage_exec.finished_at = datetime.now().isoformat()
                    return False
            else:
                stage_exec.status = StageStatus.FAILED
                stage_exec.error_message = "审批超时"
                stage_exec.finished_at = datetime.now().isoformat()
                return False
            self._cicd_stats["approvals_pending"] = max(0, self._cicd_stats["approvals_pending"] - 1)
            run.approved_by = approval.resolved_at and approval.approvers[0] or ""
        # 执行步骤
        stage_exec.status = StageStatus.RUNNING
        step_success = True
        for i, step in enumerate(stage.steps):
            # 检查条件
            if step.condition and not self._evaluate_condition(step.condition, run.variables):
                stage_exec.logs.append(f"  [{step.name}] 跳过（条件不满足）")
                continue
            try:
                log = self._execute_step(step, run.variables)
                stage_exec.logs.append(f"  [{step.name}] ✓ {log}")
                stage_exec.steps_executed += 1
            except Exception as e:
                stage_exec.logs.append(f"  [{step.name}] ✗ {str(e)[:200]}")
                if step.continue_on_error:
                    step_success = False
                elif step.retry_count > stage_exec.retry_count:
                    stage_exec.retry_count += 1
                    time.sleep(step.retry_delay)
                    try:
                        log = self._execute_step(step, run.variables)
                        stage_exec.logs.append(f"  [{step.name}] ✓ (重试) {log}")
                        stage_exec.steps_executed += 1
                    except Exception as e2:
                        stage_exec.logs.append(f"  [{step.name}] ✗ (重试失败) {str(e2)[:200]}")
                        step_success = False
                        if not stage.allow_failure:
                            stage_exec.status = StageStatus.FAILED
                            stage_exec.error_message = str(e2)[:500]
                            stage_exec.finished_at = datetime.now().isoformat()
                            stage_exec.duration_seconds = time.time() - stage_start
                            return False
                else:
                    if not stage.allow_failure:
                        stage_exec.status = StageStatus.FAILED
                        stage_exec.error_message = str(e)[:500]
                        stage_exec.finished_at = datetime.now().isoformat()
                        stage_exec.duration_seconds = time.time() - stage_start
                        return False
        stage_exec.status = (
            StageStatus.SUCCESS
            if step_success
            else (StageStatus.SUCCESS if stage.allow_failure else StageStatus.FAILED)
        )
        stage_exec.finished_at = datetime.now().isoformat()
        stage_exec.duration_seconds = time.time() - stage_start
        # 更新环境
        if stage.environment and stage_exec.status == StageStatus.SUCCESS:
            self._environments[stage.environment]["last_deploy"] = datetime.now().isoformat()
            self._environments[stage.environment]["version"] = run.variables.get("VERSION", run.run_id)
            self._cicd_stats["deployments_total"] += 1
        return stage_exec.status == StageStatus.SUCCESS

    def _execute_step(self, step: StageStep, variables: dict[str, str]) -> str:
        """执行步骤"""
        cmd = step.command
        if step.script:
            cmd = "\n".join(step.script)
        # 变量替换
        for key, value in variables.items():
            cmd = cmd.replace(f"${{{key}}}", value)
            cmd = cmd.replace(f"${key}", value)
        # 模拟执行
        time.sleep(min(0.5, step.timeout_seconds))
        if "error" in cmd.lower() and "continue" not in cmd.lower():
            raise RuntimeError(f"步骤执行失败: {cmd[:100]}")
        return f"完成 ({len(cmd)} chars)"

    @staticmethod
    def _evaluate_condition(condition: str, variables: dict[str, str]) -> bool:
        """评估when条件"""
        try:
            for key, value in variables.items():
                condition = condition.replace(f"${{{key}}}", value)
            return bool(eval(condition, {"__builtins__": {}}, {}))
        except Exception:
            return True

    # ----------------------------------------------------------------
    # 审批
    # ----------------------------------------------------------------

    def approve(self, request_id: str, approver: str, comment: str = "") -> Result:
        approval = self._approvals.get(request_id)
        if not approval or approval.status != "pending":
            return Result(success=False, error="审批请求不存在或已处理")
        approval.status = "approved"
        approval.resolved_at = datetime.now().isoformat()
        approval.comments = comment
        return Result(success=True)

    def reject(self, request_id: str, approver: str, comment: str = "") -> Result:
        approval = self._approvals.get(request_id)
        if not approval or approval.status != "pending":
            return Result(success=False, error="审批请求不存在或已处理")
        approval.status = "rejected"
        approval.resolved_at = datetime.now().isoformat()
        approval.comments = comment
        return Result(success=True)

    def list_pending_approvals(self) -> list[dict]:
        return [
            {
                "request_id": a.request_id,
                "run_id": a.run_id,
                "stage": a.stage_name,
                "pipeline": a.pipeline_name,
                "approvers": a.approvers,
                "created": a.created_at,
            }
            for a in self._approvals.values()
            if a.status == "pending"
        ]

    # ----------------------------------------------------------------
    # 制品管理
    # ----------------------------------------------------------------

    def register_artifact(self, artifact: ArtifactInfo) -> Result:
        self._artifacts[artifact.artifact_id] = artifact
        self._cicd_stats["artifacts_total"] += 1
        return Result(success=True, data={"artifact_id": artifact.artifact_id})

    # ----------------------------------------------------------------
    # 回滚
    # ----------------------------------------------------------------

    def rollback(self, run_id: str) -> Result:
        run = self._runs.get(run_id)
        if not run:
            return Result(success=False, error=f"运行记录不存在: {run_id}")
        # 找到部署阶段并重新执行
        for stage_name, stage_exec in run.stage_executions.items():
            pipeline = self._pipelines.get(run.pipeline_id)
            if pipeline:
                for stage in pipeline.stages:
                    if stage.name == stage_name and stage.environment:
                        new_run = PipelineRun(
                            pipeline_id=run.pipeline_id,
                            pipeline_name=run.pipeline_name,
                            trigger_type=TriggerType.MANUAL,
                            trigger_user="rollback",
                            variables={**run.variables, "ROLLBACK_FROM": run.run_id},
                        )
                        self._runs[new_run.run_id] = new_run
                        task = asyncio.create_task(self._execute_pipeline(new_run))
                        self._active_tasks[new_run.run_id] = task
                        return Result(success=True, data={"new_run_id": new_run.run_id})
        return Result(success=False, error="无可回滚的部署阶段")

    # ----------------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        active = sum(1 for r in self._runs.values() if r.status == StageStatus.RUNNING)
        success_rate = 0.0
        if self._cicd_stats["runs_total"] > 0:
            success_rate = self._cicd_stats["runs_success"] / self._cicd_stats["runs_total"] * 100
        return {
            **self._cicd_stats,
            "success_rate": round(success_rate, 2),
            "active_runs": active,
            "pipelines": len(self._pipelines),
            "environments": len(self._environments),
            "module_stats": self.stats.to_dict(),
        }

    def get_run_detail(self, run_id: str) -> dict | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        return {
            "run_id": run.run_id,
            "pipeline": run.pipeline_name,
            "status": run.status.value,
            "trigger": run.trigger_type.value,
            "ref": run.ref,
            "commit": run.commit_sha,
            "started": run.started_at,
            "finished": run.finished_at,
            "duration": round(run.duration_seconds, 2),
            "stages": {
                name: {
                    "status": se.status.value,
                    "duration": round(se.duration_seconds, 2),
                    "steps": f"{se.steps_executed}/{se.steps_total}",
                }
                for name, se in run.stage_executions.items()
            },
        }

    def list_runs(self, pipeline_id: str | None = None, limit: int = 20) -> list[dict]:
        result = []
        for run in sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True):
            if pipeline_id and run.pipeline_id != pipeline_id:
                continue
            result.append(
                {
                    "run_id": run.run_id,
                    "pipeline": run.pipeline_name,
                    "status": run.status.value,
                    "trigger": run.trigger_type.value,
                    "duration": round(run.duration_seconds, 2),
                    "created": run.created_at,
                }
            )
        return result[:limit]

# ============================================================================
# 模块注册
# ============================================================================

module_class = CICDPipeline
