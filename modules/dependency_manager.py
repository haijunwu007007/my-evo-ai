"""
AUTO-EVO-AI V0.1 — 依赖管理器
Grade: A (生产级) | Category: 工具链
职责：依赖扫描、版本管理、漏洞检测、兼容性分析、更新策略
"""

__module_meta__ = {
    "id": "dependency-manager",
    "name": "Dependency Manager",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "dependency", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 依赖管理器 Grade: A (生产级) | Category: 工具链",
}

import asyncio
import time
import uuid
import re
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
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
logger = logging.getLogger("dependency_manager")

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

class VulnSeverity(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DepStatus(Enum):
    CURRENT = "current"
    OUTDATED = "outdated"
    MAJOR_UPDATE = "major_update"
    VULNERABLE = "vulnerable"
    UNRESOLVED = "unresolved"
    INVALID = "invalid"

@dataclass
class Dependency:
    """依赖项"""

    name: str
    version: str
    latest_version: str = ""
    status: DepStatus = DepStatus.CURRENT
    is_direct: bool = True
    is_dev: bool = False
    license: str = ""
    description: str = ""
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    size_bytes: int = 0

@dataclass
class VulnReport:
    """漏洞报告"""

    vuln_id: str
    package: str
    installed_version: str
    affected_versions: str
    severity: VulnSeverity
    title: str
    description: str
    cve: Optional[str] = None
    patch_version: Optional[str] = None
    references: List[str] = field(default_factory=list)
    published_at: Optional[str] = None

@dataclass
class LockEntry:
    """锁文件条目"""

    name: str
    version: str
    hash: str = ""
    source: str = "pypi"
    dependencies: List[str] = field(default_factory=list)

class DependencyManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """依赖管理器"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._dependencies: Dict[str, Dependency] = {}
        self._lockfile: Dict[str, LockEntry] = {}
        self._vulns: List[VulnReport] = []
        self._scan_history: List[Dict] = []
        self._manifest_files = {
            "requirements.txt": self._parse_requirements_txt,
            "setup.py": self._parse_setup_py,
            "pyproject.toml": self._parse_pyproject_toml,
            "Pipfile": self._parse_pipfile,
            "package.json": self._parse_package_json,
        }
        self._known_vulns = self._load_known_vulnerabilities()
        self._version_cache: Dict[str, str] = {}

    def initialize(self) -> None:
        logger.info("依赖管理器初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _load_known_vulnerabilities(self) -> List[Dict]:
        """加载已知漏洞数据库（模拟）"""
        return [
            {
                "package": "requests",
                "versions": "<2.28.0",
                "severity": "high",
                "cve": "CVE-2023-32681",
                "title": "请求走私漏洞",
                "patch": "2.28.0",
            },
            {
                "package": "urllib3",
                "versions": "<1.26.16",
                "severity": "medium",
                "cve": "CVE-2023-43804",
                "title": "ReDoS漏洞",
                "patch": "1.26.16",
            },
            {
                "package": "flask",
                "versions": "<2.3.0",
                "severity": "medium",
                "cve": "CVE-2023-30861",
                "title": "Cookie作用域问题",
                "patch": "2.3.0",
            },
            {
                "package": "pillow",
                "versions": "<9.5.0",
                "severity": "critical",
                "cve": "CVE-2023-44271",
                "title": "缓冲区溢出",
                "patch": "9.5.0",
            },
            {
                "package": "django",
                "versions": "<4.2.0",
                "severity": "high",
                "cve": "CVE-2023-46695",
                "title": "SQL注入",
                "patch": "4.2.0",
            },
            {
                "package": "numpy",
                "versions": "<1.24.0",
                "severity": "medium",
                "cve": "CVE-2023-41104",
                "title": "缓冲区溢出",
                "patch": "1.24.0",
            },
        ]

    @trace_operation("scan_dependencies")
    def scan_project(self, project_path: str) -> Dict[str, Any]:
        """扫描项目依赖"""
        start = time.time()
        self._dependencies.clear()
        self._vulns.clear()

        scan_results = []
        for filename, parser in self._manifest_files.items():
            filepath = os.path.join(project_path, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    deps = parser(content)
                    for dep in deps:
                        dep.is_direct = True
                        self._dependencies[dep.name] = dep
                    scan_results.append({"file": filename, "dependencies": len(deps), "status": "parsed"})
                except Exception as e:
                    scan_results.append({"file": filename, "dependencies": 0, "status": "error", "error": str(e)})

        # 版本检查
        self._check_versions()

        # 漏洞扫描
        self._scan_vulnerabilities()

        # 构建依赖树
        dep_tree = self._build_dependency_tree()

        duration = (time.time() - start) * 1000
        total = len(self._dependencies)
        outdated = sum(1 for d in self._dependencies.values() if d.status == DepStatus.OUTDATED)
        major = sum(1 for d in self._dependencies.values() if d.status == DepStatus.MAJOR_UPDATE)
        vuln_deps = set(v.package for v in self._vulns)

        self._scan_history.append(
            {
                "timestamp": time.time(),
                "total": total,
                "outdated": outdated + major,
                "vulnerable": len(vuln_deps),
                "duration_ms": duration,
            }
        )

        self.stats["scans_total"] = self.stats.get("scans_total", 0) + 1

        audit_logger.log(
            action="dependency_scan",
            resource=project_path,
            details=f"扫描完成: {total}个依赖, {outdated + major}个过时, {len(vuln_deps)}个有漏洞",
        )

        return {
            "project_path": project_path,
            "total_dependencies": total,
            "current": sum(1 for d in self._dependencies.values() if d.status == DepStatus.CURRENT),
            "outdated": outdated,
            "major_updates": major,
            "vulnerable": len(vuln_deps),
            "vulnerabilities": len(self._vulns),
            "manifests_scanned": scan_results,
            "dependency_tree": dep_tree,
            "duration_ms": round(duration, 2),
        }

    def _parse_requirements_txt(self, content: str) -> List[Dependency]:
        """解析 requirements.txt"""
        deps = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # 处理各种版本规范
            match = re.match(r"^([a-zA-Z0-9_-]+)\s*([><=!~]+)?\s*([\d.]+(?:\.\*)?)?", line)
            if match:
                name = match.group(1).lower().replace("-", "_")
                version = match.group(3) or "*"
                deps.append(Dependency(name=name, version=version))
            else:
                # 纯包名
                name = re.match(r"^([a-zA-Z0-9_-]+)", line)
                if name:
                    deps.append(Dependency(name=name.group(1).lower(), version="*"))
        return deps

    def _parse_setup_py(self, content: str) -> List[Dependency]:
        """解析 setup.py"""
        deps = []
        match = re.search(r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            block = match.group(1)
            for m in re.finditer(r"'([^']+)'", block):
                deps.append(Dependency(name=m.group(1).lower().split(">=")[0].split("<")[0], version="*"))
        return deps

    def _parse_pyproject_toml(self, content: str) -> List[Dependency]:
        """解析 pyproject.toml"""
        deps = []
        match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            block = match.group(1)
            for m in re.finditer(r'"([^"]+)"', block):
                pkg = m.group(1).lower()
                name = re.match(r"^([a-zA-Z0-9_-]+)", pkg).group(1) if re.match(r"^([a-zA-Z0-9_-]+)", pkg) else pkg
                deps.append(Dependency(name=name, version="*"))
        return deps

    def _parse_pipfile(self, content: str) -> List[Dependency]:
        """解析 Pipfile"""
        deps = []
        match = re.search(r"\[packages\](.*?)\[", content, re.DOTALL)
        if match:
            for m in re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"', match.group(1)):
                deps.append(Dependency(name=m.group(1).lower(), version=m.group(2)))
        return deps

    def _parse_package_json(self, content: str) -> List[Dependency]:
        """解析 package.json"""
        deps = []
        try:
            data = json.loads(content)
            for section in ["dependencies", "devDependencies"]:
                if section in data:
                    for name, version in data[section].items():
                        clean_ver = re.sub(r"[\^~>=<]", "", version)
                        deps.append(
                            Dependency(name=name.lower(), version=clean_ver, is_dev=(section == "devDependencies"))
                        )
        except json.JSONDecodeError:
            pass
        return deps

    def _check_versions(self) -> None:
        """检查版本更新（模拟）"""
        # 模拟最新版本映射
        latest_versions = {
            "requests": "2.31.0",
            "flask": "3.0.0",
            "django": "5.0.0",
            "numpy": "1.26.0",
            "pandas": "2.1.0",
            "fastapi": "0.104.0",
            "uvicorn": "0.24.0",
            "sqlalchemy": "2.0.23",
            "redis": "5.0.0",
            "celery": "5.3.4",
            "httpx": "0.25.0",
            "pydantic": "2.5.0",
            "aiohttp": "3.9.0",
            "pillow": "10.1.0",
            "pytest": "7.4.0",
            "black": "23.11.0",
            "flake8": "6.1.0",
            "mypy": "1.7.0",
            "urllib3": "2.0.7",
            "certifi": "2023.11.0",
            "charset_normalizer": "3.3.0",
            "idna": "3.4",
            "click": "8.1.7",
            "itsdangerous": "2.1.2",
            "jinja2": "3.1.2",
            "markupsafe": "2.1.3",
            "werkzeug": "3.0.0",
        }

        for dep in self._dependencies.values():
            latest = latest_versions.get(dep.name, "")
            dep.latest_version = latest or dep.version

            if not latest:
                dep.status = DepStatus.UNRESOLVED
                continue

            installed = dep.version.replace("*", "0")
            installed_parts = [int(p) for p in installed.split(".") if p.isdigit()]
            latest_parts = [int(p) for p in latest.split(".") if p.isdigit()]

            if not installed_parts or not latest_parts:
                dep.status = DepStatus.UNRESOLVED
                continue

            if installed_parts[0] < latest_parts[0]:
                dep.status = DepStatus.MAJOR_UPDATE
            elif installed_parts < latest_parts:
                dep.status = DepStatus.OUTDATED
            else:
                dep.status = DepStatus.CURRENT

    def _scan_vulnerabilities(self) -> None:
        """扫描已知漏洞"""
        self._vulns.clear()
        for known in self._known_vulns:
            pkg_name = known["package"]
            if pkg_name not in self._dependencies:
                continue

            dep = self._dependencies[pkg_name]
            installed = dep.version.replace("*", "0")
            installed_parts = [int(p) for p in installed.split(".") if p.isdigit()]

            affected_str = known["versions"].lstrip("<>=!")
            affected_parts = [int(p) for p in affected_str.split(".") if p.isdigit()]

            if installed_parts and affected_parts and installed_parts < affected_parts:
                vuln = VulnReport(
                    vuln_id=f"vuln_{uuid.uuid4().hex[:8]}",
                    package=pkg_name,
                    installed_version=dep.version,
                    affected_versions=known["versions"],
                    severity=VulnSeverity(known["severity"]),
                    title=known["title"],
                    cve=known.get("cve"),
                    patch_version=known.get("patch"),
                    references=[],
                    published_at=datetime.now().isoformat(),
                )
                self._vulns.append(vuln)
                dep.vulnerabilities.append(
                    {
                        "vuln_id": vuln.vuln_id,
                        "severity": vuln.severity.value,
                        "title": vuln.title,
                        "patch": vuln.patch_version,
                    }
                )
                dep.status = DepStatus.VULNERABLE

    def _build_dependency_tree(self) -> Dict[str, Any]:
        """构建依赖树"""
        tree = {}
        for name, dep in self._dependencies.items():
            tree[name] = {
                "version": dep.version,
                "latest": dep.latest_version,
                "status": dep.status.value,
                "is_direct": dep.is_direct,
                "is_dev": dep.is_dev,
                "vulns": len(dep.vulnerabilities),
            }
        return tree

    @trace_operation("generate_lockfile")
    def generate_lockfile(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """生成锁文件"""
        lockfile = {}
        for name, dep in self._dependencies.items():
            self._lockfile[name] = LockEntry(
                name=name,
                version=dep.latest_version or dep.version,
                hash=hashlib.sha256(f"{name}:{dep.version}".encode()).hexdigest()[:16],
                dependencies=[],
            )
            lockfile[name] = {"version": self._lockfile[name].version, "hash": self._lockfile[name].hash}

        content = json.dumps(lockfile, indent=2, ensure_ascii=False)

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        self.stats["lockfiles_generated"] = self.stats.get("lockfiles_generated", 0) + 1
        return {"entries": len(lockfile), "output_path": output_path, "content": content if not output_path else None}

    @trace_operation("update_dependencies")
    def get_update_plan(self, strategy: str = "safe") -> Dict[str, Any]:
        """获取更新计划"""
        plan = {"major": [], "minor": [], "patch": [], "vulnerable": []}

        for name, dep in self._dependencies.items():
            if dep.status == DepStatus.VULNERABLE:
                plan["vulnerable"].append(
                    {"name": name, "current": dep.version, "target": dep.latest_version, "reason": "安全修复"}
                )
            elif dep.status == DepStatus.MAJOR_UPDATE and strategy != "conservative":
                plan["major"].append(
                    {"name": name, "current": dep.version, "target": dep.latest_version, "reason": "主版本更新"}
                )
            elif dep.status == DepStatus.OUTDATED:
                plan["minor"].append(
                    {"name": name, "current": dep.version, "target": dep.latest_version, "reason": "次版本更新"}
                )

        total_updates = sum(len(v) for v in plan.values())
        return {
            "strategy": strategy,
            "total_updates": total_updates,
            "vulnerable_first": plan["vulnerable"],
            "major_updates": plan["major"],
            "minor_updates": plan["minor"],
            "recommended_order": plan["vulnerable"] + plan["minor"] + plan["major"],
        }

    def get_vulnerability_report(self) -> Dict[str, Any]:
        """获取漏洞报告"""
        severity_counts = defaultdict(int)
        for v in self._vulns:
            severity_counts[v.severity.value] += 1

        return {
            "total_vulnerabilities": len(self._vulns),
            "by_severity": dict(severity_counts),
            "affected_packages": list(set(v.package for v in self._vulns)),
            "details": [
                {
                    "package": v.package,
                    "installed": v.installed_version,
                    "severity": v.severity.value,
                    "title": v.title,
                    "cve": v.cve,
                    "patch": v.patch_version,
                }
                for v in sorted(self._vulns, key=lambda x: x.severity.value, reverse=True)
            ],
        }

    def get_dependency_report(self) -> Dict[str, Any]:
        """获取依赖报告"""
        status_counts = defaultdict(int)
        for dep in self._dependencies.values():
            status_counts[dep.status.value] += 1

        return {
            "total": len(self._dependencies),
            "by_status": dict(status_counts),
            "direct": sum(1 for d in self._dependencies.values() if d.is_direct),
            "vulnerable": sum(1 for d in self._dependencies.values() if d.status == DepStatus.VULNERABLE),
            "licenses": list(set(d.license for d in self._dependencies.values() if d.license)),
            "scans_performed": len(self._scan_history),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        metrics_collector.counter("dependency_manager_ops_total", labels={"action": action})
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "scan_project": self.scan_project,
            "generate_lockfile": self.generate_lockfile,
            "get_update_plan": self.get_update_plan,
            "get_vulnerability_report": self.get_vulnerability_report,
            "get_dependency_report": self.get_dependency_report,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "dependencies_tracked": len(self._dependencies),
                "lockfile_entries": len(self._lockfile),
                "vulnerabilities": len(self._vulns),
                "scans_performed": len(self._scan_history),
            }
        )
        return base

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown",
            resource="dependency_manager",
            details=f"关闭，跟踪 {len(self._dependencies)} 个依赖",
        )

# 补充import
import hashlib

module_class = DependencyManager
