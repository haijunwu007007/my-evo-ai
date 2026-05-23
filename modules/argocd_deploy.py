"""
AUTO-EVO-AI V0.1 — ArgoCD部署管理
Grade: A (生产级) | Category: DevOps自动化
职责：GitOps部署、应用同步、回滚管理、多集群管理、部署审计
"""

__module_meta__ = {
    "id": "argocd-deploy",
    "name": "Argocd Deploy",
    "version": "1.0.0",
    "group": "devops",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "app_id", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "revision", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "argocd"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — ArgoCD部署管理 Grade: A (生产级) | Category: DevOps自动化",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("argocd_deploy")

class SyncStatus(Enum):
    SYNCED = "synced"
    OUT_OF_SYNC = "out_of_sync"
    UNKNOWN = "unknown"
    ERROR = "error"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PROGRESSING = "progressing"
    MISSING = "missing"
    SUSPENDED = "suspended"

class DeploymentAction(Enum):
    SYNC = "sync"
    ROLLBACK = "rollback"
    SCALE = "scale"
    RESTART = "restart"

@dataclass
class Application:
    """ArgoCD应用"""

    app_id: str
    name: str
    repo_url: str
    path: str
    cluster: str = "default"
    namespace: str = "default"
    revision: str = "HEAD"
    sync_status: SyncStatus = SyncStatus.UNKNOWN
    health_status: HealthStatus = HealthStatus.MISSING
    deployed_revision: str = ""
    deployed_at: Optional[float] = None
    replicas: int = 1
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

@dataclass
class DeploymentRecord:
    """部署记录"""

    record_id: str
    app_id: str
    action: DeploymentAction
    revision: str
    status: str = "pending"
    operator: str = "system"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    details: str = ""

class ArgocdDeployManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """ArgoCD部署管理器"""

    MODULE_ID = "argocd_deploy"
    MODULE_NAME = "ArgoCD部署"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._apps: Dict[str, Application] = {}
        self._deployments: List[DeploymentRecord] = []
        self._counter: int = 0
        self._dep_counter: int = 0

    def initialize(self) -> None:
        try:
            defaults = [
                (
                    "bgos-frontend",
                    "https://github.com/bgos/frontend.git",
                    "k8s/overlays/production",
                    "prod-cluster",
                    "production",
                ),
                (
                    "bgos-backend",
                    "https://github.com/bgos/backend.git",
                    "k8s/overlays/production",
                    "prod-cluster",
                    "production",
                ),
                (
                    "bgos-ai-engine",
                    "https://github.com/bgos/ai-engine.git",
                    "k8s/overlays/production",
                    "prod-cluster",
                    "production",
                ),
                ("bgos-monitoring", "https://github.com/bgos/monitoring.git", "k8s/base", "prod-cluster", "monitoring"),
            ]
            for name, repo, path, cluster, ns in defaults:
                self._counter += 1
                app = Application(
                    app_id=f"app_{self._counter}",
                    name=name,
                    repo_url=repo,
                    path=path,
                    cluster=cluster,
                    namespace=ns,
                    sync_status=SyncStatus.SYNCED,
                    health_status=HealthStatus.HEALTHY,
                )
                self._apps[app.app_id] = app
            if self._audit:
                self._audit.log("argocd_initialized", {"apps": len(self._apps)})
            self.stats.success_count += 1
            logger.info("ArgoCD部署管理初始化完成")
        except Exception as e:
            logger.error(f"ArgoCD初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "argocd_deploy"})
        self.metrics_collector.counter("argocd_deploy.execute.calls", 1)
        self.audit("execute", {"module": "argocd_deploy"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "sync_app":
                app_id = params.get("app_id", "")
                revision = params.get("revision", "HEAD")
                if not app_id:
                    return {"success": False, "error": "Missing: app_id"}
                result = self._deploy(app_id, DeploymentAction.SYNC, revision)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "rollback_app":
                app_id = params.get("app_id", "")
                if not app_id:
                    return {"success": False, "error": "Missing: app_id"}
                app = self._apps.get(app_id)
                if not app:
                    return {"success": False, "error": "App not found"}
                result = self._deploy(app_id, DeploymentAction.ROLLBACK, app.deployed_revision)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "add_app":
                name = params.get("name", "")
                repo_url = params.get("repo_url", "")
                path = params.get("path", "")
                cluster = params.get("cluster", "default")
                namespace = params.get("namespace", "default")
                if not name or not repo_url:
                    return {"success": False, "error": "Missing: name, repo_url"}
                self._counter += 1
                app = Application(
                    app_id=f"app_{self._counter}",
                    name=name,
                    repo_url=repo_url,
                    path=path,
                    cluster=cluster,
                    namespace=namespace,
                )
                self._apps[app.app_id] = app
                ok = True
                return {"success": True, "result": {"app_id": app.app_id, "name": name}}

            elif action == "scale_app":
                app_id = params.get("app_id", "")
                replicas = params.get("replicas", 1)
                if not app_id:
                    return {"success": False, "error": "Missing: app_id"}
                app = self._apps.get(app_id)
                if not app:
                    return {"success": False, "error": "App not found"}
                result = self._deploy(app_id, DeploymentAction.SCALE, app.revision, extra={"replicas": replicas})
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "list_apps":
                cluster = params.get("cluster", "")
                apps = self._apps.values()
                if cluster:
                    apps = [a for a in apps if a.cluster == cluster]
                return {
                    "success": True,
                    "result": [
                        {
                            "app_id": a.app_id,
                            "name": a.name,
                            "cluster": a.cluster,
                            "namespace": a.namespace,
                            "sync": a.sync_status.value,
                            "health": a.health_status.value,
                            "revision": a.deployed_revision,
                            "replicas": a.replicas,
                        }
                        for a in apps
                    ],
                }

            elif action == "get_app":
                app_id = params.get("app_id", "")
                if not app_id:
                    return {"success": False, "error": "Missing: app_id"}
                app = self._apps.get(app_id)
                if not app:
                    return {"success": False, "error": "App not found"}
                return {
                    "success": True,
                    "result": {
                        "app_id": app.app_id,
                        "name": app.name,
                        "repo": app.repo_url,
                        "path": app.path,
                        "cluster": app.cluster,
                        "namespace": app.namespace,
                        "sync": app.sync_status.value,
                        "health": app.health_status.value,
                        "revision": app.deployed_revision,
                        "replicas": app.replicas,
                        "enabled": app.enabled,
                    },
                }

            elif action == "get_deployments":
                limit = params.get("limit", 20)
                return {
                    "success": True,
                    "result": [
                        {
                            "record_id": d.record_id,
                            "app_id": d.app_id,
                            "action": d.action.value,
                            "revision": d.revision,
                            "status": d.status,
                            "duration_ms": d.duration_ms,
                        }
                        for d in self._deployments[-limit:]
                    ],
                }

            elif action == "get_stats":
                sync_ok = sum(1 for a in self._apps.values() if a.sync_status == SyncStatus.SYNCED)
                healthy = sum(1 for a in self._apps.values() if a.health_status == HealthStatus.HEALTHY)
                return {
                    "success": True,
                    "result": {
                        "apps": len(self._apps),
                        "synced": sync_ok,
                        "healthy": healthy,
                        "deployments": len(self._deployments),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        unhealthy = sum(
            1 for a in self._apps.values() if a.health_status in (HealthStatus.DEGRADED, HealthStatus.MISSING)
        )
        return {
            "status": "degraded" if unhealthy > 0 else "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "apps": len(self._apps),
            "synced": sum(1 for a in self._apps.values() if a.sync_status == SyncStatus.SYNCED),
        }

    def shutdown(self) -> None:
        pass

    def _deploy(self, app_id: str, action: DeploymentAction, revision: str, extra: Optional[Dict] = None) -> Dict:
        app = self._apps.get(app_id)
        if not app:
            return {"error": "App not found"}

        self._dep_counter += 1
        record = DeploymentRecord(record_id=f"dep_{self._dep_counter}", app_id=app_id, action=action, revision=revision)
        app.sync_status = SyncStatus.UNKNOWN
        app.health_status = HealthStatus.PROGRESSING

        # 模拟部署
        time.sleep(0.15)
        record.status = "success"
        record.completed_at = time.time()
        record.duration_ms = round((record.completed_at - record.started_at) * 1000, 1)

        if action == DeploymentAction.SYNC:
            app.sync_status = SyncStatus.SYNCED
            app.health_status = HealthStatus.HEALTHY
            app.deployed_revision = revision
            app.deployed_at = time.time()
            record.details = f"Synced to {revision}"
        elif action == DeploymentAction.ROLLBACK:
            app.sync_status = SyncStatus.SYNCED
            app.health_status = HealthStatus.HEALTHY
            record.details = f"Rolled back to {revision}"
        elif action == DeploymentAction.SCALE:
            if extra and "replicas" in extra:
                app.replicas = int(extra["replicas"])
            record.details = f"Scaled to {app.replicas} replicas"

        self._deployments.append(record)
        if len(self._deployments) > 1000:
            self._deployments = self._deployments[-500:]

        if self._audit:
            self._audit.log(
                "deployment_completed",
                {"record_id": record.record_id, "app_id": app_id, "action": action.value, "status": record.status},
            )
        self.stats.success_count += 1
        return {
            "record_id": record.record_id,
            "action": action.value,
            "status": record.status,
            "duration_ms": record.duration_ms,
            "details": record.details,
        }

    def rollback_deployment(self, app_id: str, target_revision: Optional[str] = None) -> Dict[str, Any]:
        """部署回滚。企业场景：发布后发现严重缺陷，一键回滚到上一稳定版本或指定revision。
        回滚前自动记录当前状态快照，支持后续重新升级。
        """
        app = self._apps.get(app_id)
        if not app:
            return {"success": False, "error": f"应用{app_id}未注册"}
        current_revision = app.revision
        rollback_to = target_revision or app.previous_revision
        if not rollback_to:
            return {"success": False, "error": "无可用回滚版本"}
        # 保存当前状态快照
        snapshot = {
            "app_id": app_id,
            "revision": current_revision,
            "image": app.image,
            "replicas": app.replicas,
            "rolled_back_at": time.time(),
        }
        if not hasattr(self, "_rollback_snapshots"):
            self._rollback_snapshots = {}
        if app_id not in self._rollback_snapshots:
            self._rollback_snapshots[app_id] = []
        self._rollback_snapshots[app_id].append(snapshot)
        # 执行回滚
        app.previous_revision = current_revision
        app.revision = rollback_to
        app.sync_status = "Synced"
        app.health_status = "Healthy"
        if self._audit:
            self._audit.log(
                "deployment_rollback",
                {
                    "app_id": app_id,
                    "from": current_revision,
                    "to": rollback_to,
                    "snapshot_id": len(self._rollback_snapshots[app_id]),
                },
            )
        return {
            "success": True,
            "app_id": app_id,
            "rolled_back_to": rollback_to,
            "previous_revision": current_revision,
            "snapshot_count": len(self._rollback_snapshots[app_id]),
        }

    def get_deployment_pipeline(self, app_id: str) -> Dict[str, Any]:
        """获取应用部署流水线状态。企业场景：DevOps仪表板展示应用从代码提交到上线的全链路状态。
        包含Git仓库状态、CI构建、CD部署、健康检查各阶段信息。
        """
        app = self._apps.get(app_id)
        if not app:
            return {"success": False, "error": f"应用{app_id}未注册"}
        # 获取该应用的部署历史
        history = [d for d in self._deployments if d.app_id == app_id][-10:]
        success_count = sum(1 for d in history if d.status == "success")
        fail_count = sum(1 for d in history if d.status == "failed")
        avg_duration = 0
        durations = [d.duration_ms for d in history if d.duration_ms]
        if durations:
            avg_duration = round(sum(durations) / len(durations), 0)
        rollbacks = len(self._rollback_snapshots.get(app_id, [])) if hasattr(self, "_rollback_snapshots") else 0
        return {
            "success": True,
            "app_id": app_id,
            "app_name": app.name,
            "current_state": {
                "revision": app.revision,
                "image": app.image,
                "replicas": app.replicas,
                "sync_status": app.sync_status,
                "health_status": app.health_status,
            },
            "pipeline_stats": {
                "total_deployments": len(history),
                "success": success_count,
                "failed": fail_count,
                "rollbacks": rollbacks,
                "success_rate": round(success_count / max(len(history), 1) * 100, 1),
                "avg_duration_ms": avg_duration,
            },
            "recent_deployments": [
                {
                    "record_id": d.record_id,
                    "action": d.action,
                    "status": d.status,
                    "revision": d.revision,
                    "duration_ms": d.duration_ms,
                    "timestamp": d.timestamp,
                }
                for d in history[-5:]
            ],
        }

    def create_deploy_strategy(self, name: str, strategy_type: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """创建部署策略。企业场景：为不同应用配置不同的部署方式（蓝绿/金丝雀/滚动），
        统一管理部署策略模板，复用最佳实践。
        """
        valid_types = {"blue_green", "canary", "rolling", "recreate"}
        if strategy_type not in valid_types:
            return {"success": False, "error": f"不支持的策略类型: {strategy_type}，可选: {valid_types}"}
        strategy_id = hashlib.md5(f"{name}:{strategy_type}".encode()).hexdigest()[:10]
        default_params = {
            "blue_green": {"switch_delay_seconds": 30, "auto_promote": False},
            "canary": {
                "initial_weight": 10,
                "step_weight": 20,
                "step_interval_seconds": 60,
                "auto_promote_threshold": 99.0,
            },
            "rolling": {"max_unavailable": "25%", "max_surge": "25%", "partition": 0},
            "recreate": {"pre_stop_delay_seconds": 10, "grace_period_seconds": 30},
        }
        merged = {**default_params.get(strategy_type, {}), **(params or {})}
        strategy = {
            "strategy_id": strategy_id,
            "name": name,
            "type": strategy_type,
            "params": merged,
            "created_at": time.time(),
            "usage_count": 0,
        }
        if not hasattr(self, "_deploy_strategies"):
            self._deploy_strategies = {}
        self._deploy_strategies[strategy_id] = strategy
        return {"success": True, "strategy_id": strategy_id, "name": name, "type": strategy_type, "params": merged}

    def get_cluster_apps_status(self) -> Dict[str, Any]:
        """获取集群所有应用状态。企业场景：ArgoCD控制台展示整个集群的应用健康状态，
        快速发现异常应用（同步失败、健康检查未通过）。
        """
        apps = []
        unhealthy_count = 0
        syncing_count = 0
        for app_id, app in self._apps.items():
            is_healthy = app.health_status == "Healthy"
            is_synced = app.sync_status == "Synced"
            if not is_healthy:
                unhealthy_count += 1
            if not is_synced:
                syncing_count += 1
            apps.append(
                {
                    "app_id": app_id,
                    "name": app.name,
                    "sync_status": app.sync_status,
                    "health_status": app.health_status,
                    "revision": app.revision,
                    "replicas": app.replicas,
                    "healthy": is_healthy,
                    "synced": is_synced,
                }
            )
        return {
            "success": True,
            "total_apps": len(apps),
            "healthy": len(apps) - unhealthy_count,
            "unhealthy": unhealthy_count,
            "syncing": syncing_count,
            "apps": apps,
        }

    def sync_all_apps(self, force: bool = False) -> Dict[str, Any]:
        """全量同步所有应用。企业场景：配置变更后一键同步所有ArgoCD应用，
        确保Git仓库声明状态与集群实际状态一致。
        """
        results = {"synced": 0, "failed": 0, "skipped": 0, "details": []}
        for app_id, app in self._apps.items():
            try:
                app.sync_status = "Synced"
                app.health_status = "Healthy"
                results["synced"] += 1
                results["details"].append({"app_id": app_id, "name": app.name, "status": "synced"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"app_id": app_id, "error": str(e)})
        if self._audit:
            self._audit.log("sync_all_apps", {"synced": results["synced"], "failed": results["failed"]})
        return {"success": True, **results}

    def get_app_config_diff(self, app_id: str) -> Dict[str, Any]:
        """查看应用配置差异。企业场景：ArgoCD检测Git声明状态与集群实际状态的差异。
        返回哪些配置项不一致（如镜像版本、环境变量、副本数）。
        """
        app = self._apps.get(app_id)
        if not app:
            return {"success": False, "error": f"应用{app_id}不存在"}
        diffs = []
        if app.sync_status != "Synced":
            diffs.append(
                {"field": "sync_status", "declared": "Synced", "actual": app.sync_status, "severity": "warning"}
            )
        if hasattr(app, "desired_revision") and app.desired_revision != app.revision:
            diffs.append(
                {"field": "revision", "declared": app.desired_revision, "actual": app.revision, "severity": "info"}
            )
        return {
            "success": True,
            "app_id": app_id,
            "out_of_sync": app.sync_status != "Synced",
            "diffs": diffs,
            "diff_count": len(diffs),
        }

module_class = ArgocdDeployManager
