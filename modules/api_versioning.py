"""
AUTO-EVO-AI V0.1 — API版本管理
Grade: A (生产级) | Category: API基础设施
职责：API版本注册与路由、版本生命周期管理、兼容性检查、废弃策略、版本迁移
"""

__module_meta__ = {
        "id": "api-versioning",
        "name": "Api Versioning",
        "version": "V0.1",
        "group": "api",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "api_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "version",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "from_ver",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "to_ver",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "version_2",
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
                "type": "webhook",
                "config": {
                    "path": "/hooks/api_versioning",
                    "method": "POST"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "api",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — API版本管理 Grade: A (生产级) | Category: API基础设施"
    }

import os
import asyncio
import time
import logging
import re
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

logger = logging.getLogger("api_versioning")

class VersionStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    RETIRED = "retired"
    DRAFT = "draft"

@dataclass
class ApiVersion:
    """API版本"""

    version_id: str
    api_name: str
    version: str
    base_path: str
    status: VersionStatus = VersionStatus.ACTIVE
    changelog: str = ""
    breaking_changes: list[str] = field(default_factory=list)
    deprecated_at: float | None = None
    sunset_at: float | None = None
    retired_at: float | None = None
    request_count: int = 0
    created_at: float = field(default_factory=time.time)

@dataclass
class VersionRoute:
    """版本路由"""

    route_id: str
    api_name: str
    path_pattern: str
    version: str
    target: str
    methods: list[str] = field(default_factory=lambda: ["GET"])
    enabled: bool = True

@dataclass
class CompatibilityReport:
    """兼容性报告"""

    report_id: str
    from_version: str
    to_version: str
    compatible: bool
    breaking_changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

class ApiVersioningManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """API版本管理器"""

    MODULE_ID = "api_versioning"
    MODULE_NAME = "API版本管理"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._versions: dict[str, ApiVersion] = {}
        self._routes: dict[str, VersionRoute] = {}
        self._compat_reports: list[CompatibilityReport] = []
        self._counter: int = 0
        self._route_counter: int = 0

    def initialize(self) -> None:
        try:
            defaults = [
                ("用户API", "v1", "/api/v1/users", VersionStatus.ACTIVE, "", [], None),
                ("用户API", "v2", "/api/v2/users", VersionStatus.ACTIVE, "新增批量操作接口", [], None),
                ("模块API", "v1", "/api/v1/modules", VersionStatus.ACTIVE, "", [], None),
                (
                    "认证API",
                    "v1",
                    "/api/v1/auth",
                    VersionStatus.DEPRECATED,
                    "",
                    ["移除旧的token验证方式"],
                    time.time() - 86400 * 30,
                ),
            ]
            for item in defaults:
                api_name, version, path, status, changelog, breaking, deprecated_at = item
                self._counter += 1
                v = ApiVersion(
                    version_id=f"ver_{self._counter}",
                    api_name=api_name,
                    version=version,
                    base_path=path,
                    status=status,
                    changelog=changelog,
                    breaking_changes=breaking,
                    deprecated_at=deprecated_at,
                )
                self._versions[v.version_id] = v
            if self._audit:
                self._audit.log("api_versioning_initialized", {"versions": len(self._versions)})
            self.stats.success_count += 1
            logger.info("API版本管理初始化完成")
        except Exception as e:
            logger.error(f"API版本管理初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "api_versioning"})
        self.metrics_collector.counter("api_versioning.execute.calls", 1)
        self.audit("execute", {"module": "api_versioning"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "register_version":
                api_name = params.get("api_name", "")
                version = params.get("version", "")
                base_path = params.get("base_path", "")
                changelog = params.get("changelog", "")
                breaking = params.get("breaking_changes", [])
                if not api_name or not version or not base_path:
                    return {"success": False, "error": "Missing: api_name, version, base_path"}
                self._counter += 1
                v = ApiVersion(
                    version_id=f"ver_{self._counter}",
                    api_name=api_name,
                    version=version,
                    base_path=base_path,
                    changelog=changelog,
                    breaking_changes=breaking,
                )
                self._versions[v.version_id] = v
                ok = True
                return {"success": True, "result": {"version_id": v.version_id, "api": api_name, "version": version}}

            elif action == "deprecate_version":
                version_id = params.get("version_id", "")
                sunset_days = params.get("sunset_days", 90)
                v = self._versions.get(version_id)
                if not v:
                    return {"success": False, "error": "Version not found"}
                v.status = VersionStatus.DEPRECATED
                v.deprecated_at = time.time()
                v.sunset_at = time.time() + sunset_days * 86400
                return {
                    "success": True,
                    "result": {"version_id": version_id, "status": "deprecated", "sunset_at": v.sunset_at},
                }

            elif action == "retire_version":
                version_id = params.get("version_id", "")
                v = self._versions.get(version_id)
                if not v:
                    return {"success": False, "error": "Version not found"}
                v.status = VersionStatus.RETIRED
                v.retired_at = time.time()
                return {"success": True, "result": {"version_id": version_id, "status": "retired"}}

            elif action == "check_compatibility":
                from_version = params.get("from_version", "")
                to_version = params.get("to_version", "")
                if not from_version or not to_version:
                    return {"success": False, "error": "Missing: from_version, to_version"}
                report = self._check_compat(from_version, to_version)
                return {
                    "success": True,
                    "result": {
                        "from": report.from_version,
                        "to": report.to_version,
                        "compatible": report.compatible,
                        "breaking": report.breaking_changes,
                        "warnings": report.warnings,
                    },
                }

            elif action == "resolve_version":
                api_name = params.get("api_name", "")
                accept_version = params.get("version", "")
                header_version = params.get("header_version", "")
                version = header_version or accept_version or "latest"
                v = self._resolve(api_name, version)
                if not v:
                    return {"success": False, "error": "No matching version"}
                v.request_count += 1
                return {
                    "success": True,
                    "result": {
                        "version_id": v.version_id,
                        "version": v.version,
                        "path": v.base_path,
                        "status": v.status.value,
                    },
                }

            elif action == "list_versions":
                api_name = params.get("api_name", "")
                versions = self._versions.values()
                if api_name:
                    versions = [v for v in versions if v.api_name == api_name]
                return {
                    "success": True,
                    "result": [
                        {
                            "version_id": v.version_id,
                            "api": v.api_name,
                            "version": v.version,
                            "path": v.base_path,
                            "status": v.status.value,
                            "requests": v.request_count,
                            "breaking_changes": v.breaking_changes,
                        }
                        for v in sorted(versions, key=lambda x: x.version, reverse=True)
                    ],
                }

            elif action == "get_stats":
                status_counts = {}
                for v in self._versions.values():
                    s = v.status.value
                    status_counts[s] = status_counts.get(s, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "versions": len(self._versions),
                        "by_status": status_counts,
                        "total_requests": sum(v.request_count for v in self._versions.values()),
                        "compat_reports": len(self._compat_reports),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        sunset = sum(1 for v in self._versions.values() if v.status == VersionStatus.SUNSET)
        return {
            "status": "degraded" if sunset > 0 else "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "versions": len(self._versions),
            "active": sum(1 for v in self._versions.values() if v.status == VersionStatus.ACTIVE),
            "deprecated": sum(1 for v in self._versions.values() if v.status == VersionStatus.DEPRECATED),
        }

    def shutdown(self) -> None:
        pass

    def _resolve(self, api_name: str, version: str) -> ApiVersion | None:
        candidates = [
            v for v in self._versions.values() if v.api_name == api_name and v.status != VersionStatus.RETIRED
        ]
        if version == "latest":
            active = [v for v in candidates if v.status == VersionStatus.ACTIVE]
            if active:
                return max(active, key=lambda v: v.version)
            return candidates[0] if candidates else None
        for v in candidates:
            if v.version == version:
                return v
        return None

    def _check_compat(self, from_ver: str, to_ver: str) -> CompatibilityReport:
        report = CompatibilityReport(
            report_id=f"compat_{int(time.time())}", from_version=from_ver, to_version=to_ver, compatible=True
        )
        for v in self._versions.values():
            if v.version == to_ver and v.breaking_changes:
                report.breaking_changes = v.breaking_changes
                report.compatible = False
        if not report.compatible:
            report.warnings.append(f"版本 {to_ver} 包含不兼容变更")
        self._compat_reports.append(report)
        self.stats.success_count += 1
        return report

    def deprecate_version(
        self, version: str, sunset_date: str, migration_guide: str, notify_callers: bool = True
    ) -> dict[str, Any]:
        """标记API版本为废弃状态。企业场景：V1→V2迁移期，提前通知调用方迁移，
         提供迁移指南，到期后自动返回410 Gone和Deprecated头。
        sunset_date格式: ISO 8601日期，如 2026-12-31。
        """
        ver = self._versions.get(version)
        if not ver:
            return {"success": False, "error": f"版本{version}未注册"}
        ver.deprecated = True
        ver.sunset_date = sunset_date
        ver.migration_guide = migration_guide
        # 生成废弃通知消息
        notification = {
            "version": version,
            "sunset_date": sunset_date,
            "migration_guide": migration_guide,
            "affected_endpoints": [ep for ep, v in self._routes.items() if v == version],
            "created_at": time.time(),
        }
        if not hasattr(self, "_deprecation_notices"):
            self._deprecation_notices = {}
        self._deprecation_notices[version] = notification
        callers_notified = 0
        if notify_callers and hasattr(self, "_version_callers"):
            callers = self._version_callers.get(version, [])
            callers_notified = len(callers)
        return {"success": True, "version": version, "sunset_date": sunset_date, "callers_notified": callers_notified}

    def get_version_traffic(self, days: int = 7) -> dict[str, Any]:
        """获取各API版本的流量分布统计。企业场景：判断旧版本是否可以安全下线，
        统计各版本调用次数、错误率、P95延迟，辅助版本淘汰决策。
        """
        now = time.time()
        cutoff = now - days * 86400
        if not hasattr(self, "_access_log"):
            return {"success": True, "message": "暂无访问日志", "versions": {}}
        recent = [l for l in self._access_log if l.get("timestamp", 0) >= cutoff]
        version_stats: dict[str, dict] = {}
        for log in recent:
            ver = log.get("version", "unknown")
            if ver not in version_stats:
                version_stats[ver] = {"calls": 0, "errors": 0, "total_latency_ms": 0, "latencies": []}
            version_stats[ver]["calls"] += 1
            if log.get("status_code", 200) >= 400:
                version_stats[ver]["errors"] += 1
            lat = log.get("latency_ms", 0)
            version_stats[ver]["latencies"].append(lat)
            version_stats[ver]["total_latency_ms"] += lat
        result = {}
        for ver, stats in version_stats.items():
            lats = sorted(stats["latencies"])
            p95 = lats[int(len(lats) * 0.95)] if lats else 0
            result[ver] = {
                "calls": stats["calls"],
                "error_rate": round(stats["errors"] / max(stats["calls"], 1) * 100, 1),
                "avg_latency_ms": round(stats["total_latency_ms"] / max(stats["calls"], 1), 1),
                "p95_latency_ms": p95,
                "traffic_share": round(stats["calls"] / max(len(recent), 1) * 100, 1),
            }
        return {"success": True, "period_days": days, "total_requests": len(recent), "versions": result}

    def create_api_changelog(
        self, version: str, changes: list[dict[str, str]], author: str = "system"
    ) -> dict[str, Any]:
        """创建API变更日志。企业场景：版本发布时记录接口变更详情，
        自动生成CHANGELOG供前端团队和第三方接入方参考。
        """
        if not changes:
            return {"success": False, "error": "变更列表不能为空"}
        valid_types = {"breaking", "feature", "fix", "deprecated", "security", "performance"}
        for c in changes:
            if c.get("type", "") not in valid_types:
                return {"success": False, "error": f"无效变更类型: {c.get('type')}"}
        changelog_id = hashlib.md5(f"{version}:{time.time()}".encode()).hexdigest()[:10]
        entry = {
            "changelog_id": changelog_id,
            "version": version,
            "author": author,
            "created_at": time.time(),
            "changes": changes,
            "breaking_count": sum(1 for c in changes if c["type"] == "breaking"),
        }
        if not hasattr(self, "_changelogs"):
            self._changelogs = []
        self._changelogs.append(entry)
        return {
            "success": True,
            "changelog_id": changelog_id,
            "version": version,
            "changes": len(changes),
            "breaking": entry["breaking_count"],
        }

    def get_migration_status(self, from_version: str, to_version: str) -> dict[str, Any]:
        """API迁移进度。企业场景：V1→V2迁移过程中，追踪各客户端的迁移状态，
        识别未迁移的客户端并发送通知。生产环境在大版本废弃前跟踪迁移率。
        """
        versions = getattr(self, "_versions", {})
        clients = getattr(self, "_version_clients", {})
        from_clients = clients.get(from_version, [])
        to_clients = clients.get(to_version, [])
        migration_rate = 0
        if from_clients or to_clients:
            total = len(set(from_clients + to_clients))
            migration_rate = round(len(to_clients) / max(total, 1) * 100, 1)
        not_migrated = [c for c in from_clients if c not in to_clients]
        return {
            "success": True,
            "from_version": from_version,
            "to_version": to_version,
            "from_clients": len(from_clients),
            "to_clients": len(to_clients),
            "not_migrated": not_migrated,
            "migration_rate": migration_rate,
        }

    def deprecate_version(self, version: str, sunset_date: str, migration_guide_url: str = "") -> dict[str, Any]:
        """废弃API版本。企业场景：大版本升级时设置废弃日期，
        在响应头中添加Deprecation和Sunset头部，引导客户端迁移。
        """
        versions = getattr(self, "_versions", {})
        if version not in versions:
            return {"success": False, "error": f"版本 {version} 不存在"}
        versions[version]["deprecated"] = True
        versions[version]["sunset_date"] = sunset_date
        versions[version]["migration_guide"] = migration_guide_url
        return {
            "success": True,
            "version": version,
            "sunset_date": sunset_date,
            "warning": f"版本 {version} 将于 {sunset_date} 后停止服务",
        }

    def get_version_compatibility_matrix(self) -> dict[str, Any]:
        """版本兼容性矩阵。企业场景：前端/移动端开发团队查看各API版本间
        的兼容性关系，识别breaking changes影响范围。
        """
        versions = getattr(self, "_versions", {})
        changelogs = getattr(self, "_changelogs", [])
        matrix = []
        for version, info in versions.items():
            changes = [c for c in changelogs if c.get("version") == version]
            breaking = sum(c.get("breaking_count", 0) for c in changes)
            matrix.append(
                {
                    "version": version,
                    "status": "active",
                    "deprecated": info.get("deprecated", False),
                    "total_changes": sum(len(c.get("changes", [])) for c in changes),
                    "breaking_changes": breaking,
                    "sunset_date": info.get("sunset_date", ""),
                }
            )
        matrix.sort(key=lambda x: x["version"], reverse=True)
        return {"success": True, "versions": matrix, "deprecated_count": sum(1 for m in matrix if m["deprecated"])}

    def get_version_request_stats(self, days: int = 7) -> dict[str, Any]:
        """API版本请求统计。企业场景：评估各版本API的调用量，辅助废弃决策。
        如果某版本调用量降至阈值以下，可安全废弃。
        """
        versions = getattr(self, "_versions", {})
        stats = []
        for version in versions:
            stats.append(
                {"version": version, "requests": getattr(versions[version], "request_count", 0), "status": "active"}
            )
        stats.sort(key=lambda x: -x["requests"])
        return {"success": True, "period_days": days, "total_versions": len(stats), "stats": stats}

    def batch_add_version_headers(self, routes: list[dict[str, str]]) -> dict[str, Any]:
        """批量设置路由版本头。企业场景：微服务网关上线时，一次性为数百个路由
        配置 X-API-Version 响应头，确保客户端能感知API版本变化。
        """
        added = 0
        skipped = 0
        for route in routes:
            path = route.get("path", "")
            version = route.get("version", "")
            if not path or not version:
                skipped += 1
                continue
            headers = getattr(self, "_route_headers", {})
            headers[path] = {"X-API-Version": version, "X-Deprecated": "false"}
            added += 1
        return {"success": True, "added": added, "skipped": skipped}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = ApiVersioningManager
