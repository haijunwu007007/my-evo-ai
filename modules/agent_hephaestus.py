"""
# Grade: A
AUTO-EVO-AI V0.1 — Agent Hephaestus (代码构建引擎)
====================================================
企业级智能体，负责代码分析、构建编排、编译管理、依赖解析与代码质量门禁。
支持多语言构建管线（Python/Node.js/Java/Go/Rust），内置构建缓存与增量编译优化。

继承: EnterpriseModule
依赖: subprocess, hashlib (标准库)
"""
from __future__ import annotations

__module_meta__ = {
        "id": "agent-hephaestus",
        "name": "Agent Hephaestus",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "cache_dir",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "max_cache_size_mb",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "project_path",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "include_patterns",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "cache_key",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "cache_key_2",
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
                "type": "event",
                "config": {
                    "on": "agent_hephaestus.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "config",
            "manager",
            "multi-agent",
            "agent"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Agent Hephaestus (代码构建引擎) ===================================================="
    }

import os
import sys
import time
import json
import hashlib
import shutil
from core.logging_config import get_logger
import subprocess
import tempfile
import threading
from pathlib import Path
from modules._base.enterprise_module import ModuleStats
from datetime import datetime, timedelta
from modules._base.enterprise_module import ModuleStats
from enum import Enum
from modules._base.enterprise_module import ModuleStats
from typing import Dict, List, Optional, Any, Tuple, Set
from modules._base.enterprise_module import ModuleStats
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = get_logger("agent.hephaestus")

# ============================================================
# 数据模型
# ============================================================

class BuildStatus(Enum):
    """构建状态枚举"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    CACHED = "cached"

class Language(Enum):
    """支持的语言"""

    PYTHON = "python"
    NODEJS = "nodejs"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    GENERIC = "generic"

class QualityGate(Enum):
    """质量门禁等级"""

    CRITICAL = "critical"  # 阻断构建
    WARNING = "warning"  # 警告但不阻断
    INFO = "info"  # 仅信息

@dataclass
class BuildConfig:
    """构建配置"""

    project_path: str = ""
    language: Language = Language.PYTHON
    build_command: str = ""
    test_command: str = ""
    lint_command: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 600
    max_retries: int = 2
    cache_enabled: bool = True
    quality_gates: dict[str, QualityGate] = field(default_factory=dict)
    output_dir: str = ""
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_path": self.project_path,
            "language": self.language.value,
            "build_command": self.build_command,
            "test_command": self.test_command,
            "lint_command": self.lint_command,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "cache_enabled": self.cache_enabled,
            "quality_gates": {k: v.value for k, v in self.quality_gates.items()},
            "output_dir": self.output_dir,
        }

@dataclass
class BuildArtifact:
    """构建产物"""

    artifact_id: str = ""
    name: str = ""
    path: str = ""
    size_bytes: int = 0
    checksum_md5: str = ""
    checksum_sha256: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "checksum_md5": self.checksum_md5,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at,
        }

@dataclass
class BuildResult:
    """构建结果"""

    build_id: str = ""
    status: BuildStatus = BuildStatus.PENDING
    project_path: str = ""
    language: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_seconds: float = 0.0
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    artifacts: list[BuildArtifact] = field(default_factory=list)
    quality_report: dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False
    retry_count: int = 0
    error_message: str = ""

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at) * 1000) if self.started_at else 0

    def to_dict(self) -> dict:
        return {
            "build_id": self.build_id,
            "status": self.status.value,
            "project_path": self.project_path,
            "language": self.language,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:5000] if self.stdout else "",
            "stderr": self.stderr[:5000] if self.stderr else "",
            "artifact_count": len(self.artifacts),
            "cache_hit": self.cache_hit,
            "retry_count": self.retry_count,
            "quality_report": self.quality_report,
            "error_message": self.error_message,
        }

@dataclass
class DependencyNode:
    """依赖节点"""

    name: str
    version: str = ""
    dep_type: str = "direct"  # direct / transitive
    resolved: bool = False
    children: list[DependencyNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "type": self.dep_type,
            "resolved": self.resolved,
            "children_count": len(self.children),
        }

# ============================================================
# 构建缓存管理器
# ============================================================

class BuildCacheManager:
    """构建缓存管理器 — 基于内容哈希的增量编译缓存"""

    def __init__(self, cache_dir: str = "", max_cache_size_mb: int = 500):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "hephaestus_cache")
        self.max_cache_size = max_cache_size_mb * 1024 * 1024
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        os.makedirs(self.cache_dir, exist_ok=True)

    def compute_source_hash(self, project_path: str, include_patterns: list[str] | None = None) -> str:
        """计算源码目录的内容哈希"""
        hasher = hashlib.sha256()
        p = Path(project_path)

        if not p.exists():
            return hashlib.sha256(project_path.encode()).hexdigest()

        default_patterns = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs", "*.cpp", "*.h"]
        patterns = include_patterns or default_patterns

        file_list = []
        for pattern in patterns:
            file_list.extend(p.rglob(pattern))

        # 按路径排序确保稳定性
        file_list = sorted(set(file_list), key=lambda f: str(f))

        for fpath in file_list:
            if fpath.is_file():
                try:
                    content = fpath.read_bytes()
                    # 文件路径 + 内容 + 修改时间
                    rel_path = str(fpath.relative_to(p))
                    entry = f"{rel_path}:{fpath.stat().st_mtime}:{hashlib.md5(content).hexdigest()}"
                    hasher.update(entry.encode())
                except Exception:
                    continue

        return hasher.hexdigest()

    def get_cached_result(self, cache_key: str) -> BuildResult | None:
        """获取缓存的构建结果"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        with self._lock:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        data = json.load(f)
                    self._hits += 1
                    return BuildResult(**data)
                except Exception:
                    pass
        self._misses += 1
        return None

    def cache_result(self, cache_key: str, result: BuildResult) -> bool:
        """缓存构建结果"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with self._lock:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
                self._evict_if_needed()
                return True
        except Exception as e:
            logger.warning(f"缓存构建结果失败: {e}")
            return False

    def _evict_if_needed(self):
        """LRU缓存淘汰"""
        total_size = (
            sum(
                os.path.getsize(os.path.join(self.cache_dir, f))
                for f in os.listdir(self.cache_dir)
                if f.endswith(".json")
            )
            if os.path.exists(self.cache_dir)
            else 0
        )

        if total_size > self.max_cache_size:
            files = []
            for f in os.listdir(self.cache_dir):
                if f.endswith(".json"):
                    fp = os.path.join(self.cache_dir, f)
                    files.append((os.path.getmtime(fp), fp))

            files.sort()
            # 淘汰最旧的30%
            to_remove = int(len(files) * 0.3)
            for _, fp in files[:to_remove]:
                try:
                    os.remove(fp)
                except Exception:
                    pass

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "cache_dir": self.cache_dir,
        }

# ============================================================
# 依赖解析器
# ============================================================

class DependencyResolver:
    """依赖解析器 — 解析项目依赖树，检测循环依赖"""

    def __init__(self):
        self._resolved: dict[str, DependencyNode] = {}
        self._cycles: list[list[str]] = []

    def resolve_python(self, project_path: str) -> tuple[list[DependencyNode], list[list[str]]]:
        """解析Python项目依赖"""
        self._cycles = []
        nodes = []
        p = Path(project_path)

        # 检查 requirements.txt
        req_file = p / "requirements.txt"
        if req_file.exists():
            req_nodes = self._parse_requirements(req_file)
            nodes.extend(req_nodes)

        # 检查 pyproject.toml
        pyproject = p / "pyproject.toml"
        if pyproject.exists():
            pp_nodes = self._parse_pyproject(pyproject)
            nodes.extend(pp_nodes)

        # 检查 setup.py / setup.cfg
        setup_py = p / "setup.py"
        if setup_py.exists():
            setup_nodes = self._parse_setup_py(setup_py)
            nodes.extend(setup_nodes)

        # 检测Python模块间循环导入
        import_cycles = self._detect_python_import_cycles(p)
        self._cycles.extend(import_cycles)

        return nodes, self._cycles

    def resolve_nodejs(self, project_path: str) -> tuple[list[DependencyNode], list[list[str]]]:
        """解析Node.js项目依赖"""
        self._cycles = []
        nodes = []
        p = Path(project_path)

        pkg_json = p / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                for dep_type in ["dependencies", "devDependencies"]:
                    deps = data.get(dep_type, {})
                    for name, version in deps.items():
                        node = DependencyNode(
                            name=name, version=str(version).replace("^", "").replace("~", ""), dep_type="direct"
                        )
                        nodes.append(node)
            except Exception as e:
                logger.warning(f"解析package.json失败: {e}")

        return nodes, self._cycles

    def _parse_requirements(self, filepath: Path) -> list[DependencyNode]:
        """解析requirements.txt"""
        nodes = []
        try:
            content = filepath.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 处理各种格式: pkg==1.0, pkg>=1.0, pkg~=1.0, pkg
                name = (
                    line.split("==")[0]
                    .split(">=")[0]
                    .split("~=")[0]
                    .split("<=")[0]
                    .split("!=")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .strip()
                )
                version = ""
                for sep in ["==", ">=", "~=", "<=", "!=", "=="]:
                    if sep in line:
                        version = line.split(sep)[1].strip().split(";")[0].strip()
                        break
                if name:
                    nodes.append(DependencyNode(name=name, version=version))
        except Exception as e:
            logger.warning(f"解析requirements.txt失败: {e}")
        return nodes

    def _parse_pyproject(self, filepath: Path) -> list[DependencyNode]:
        """解析pyproject.toml"""
        nodes = []
        try:
            content = filepath.read_text(encoding="utf-8")
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("[project]") or stripped.startswith("[tool.poetry]"):
                    in_deps = True
                    continue
                if stripped.startswith("[") and in_deps:
                    in_deps = False
                if in_deps and ("dependencies" in stripped or stripped.startswith('"')):
                    if "=" in stripped and '"' in stripped:
                        parts = stripped.split('"')
                        if len(parts) >= 2:
                            name = parts[1]
                            nodes.append(DependencyNode(name=name))
        except Exception:
            pass
        return nodes

    def _parse_setup_py(self, filepath: Path) -> list[DependencyNode]:
        """简单解析setup.py中的install_requires"""
        nodes = []
        try:
            content = filepath.read_text(encoding="utf-8")
            if "install_requires" in content:
                import re

                matches = re.findall(r'["\']([\w\-\.]+)[\"\']\s*(?:[>=<~!]+\s*[\d\.]+)?', content)
                for m in matches:
                    if m not in ("setuptools", "wheel"):
                        nodes.append(DependencyNode(name=m))
        except Exception:
            pass
        return nodes

    def _detect_python_import_cycles(self, project_path: Path, max_depth: int = 20) -> list[list[str]]:
        """检测Python模块间循环导入"""
        import_map: dict[str, set[str]] = defaultdict(set)
        for py_file in project_path.rglob("*.py"):
            module_name = py_file.stem
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                import re

                imports = re.findall(r"(?:from|import)\s+([\w\.]+)", content)
                for imp in imports:
                    base_module = imp.split(".")[0]
                    if base_module != module_name:
                        import_map[module_name].add(base_module)
            except Exception:
                continue

        cycles = []
        for start in import_map:
            visited = set()
            path = []
            if self._dfs_cycle(start, start, import_map, visited, path, max_depth):
                if path and path[0] == path[-1]:
                    cycles.append(path)

        return cycles[:10]  # 最多返回10个

    def _dfs_cycle(
        self, current: str, target: str, graph: dict[str, set[str]], visited: set[str], path: list[str], max_depth: int
    ) -> bool:
        if len(path) > max_depth:
            return False
        if current in visited:
            return current == target and len(path) > 1
        visited.add(current)
        path.append(current)
        for neighbor in graph.get(current, set()):
            if neighbor in graph:
                if self._dfs_cycle(neighbor, target, graph, visited, path, max_depth):
                    return True
        path.pop()
        visited.discard(current)
        return False

# ============================================================
# 质量门禁检查器
# ============================================================

class QualityGateChecker:
    """代码质量门禁检查器"""

    def __init__(self):
        self._rules = {
            "max_file_lines": {"threshold": 500, "gate": QualityGate.WARNING},
            "max_function_lines": {"threshold": 50, "gate": QualityGate.WARNING},
            "max_complexity": {"threshold": 10, "gate": QualityGate.CRITICAL},
            "require_docstring": {"threshold": True, "gate": QualityGate.WARNING},
            "min_test_coverage": {"threshold": 80, "gate": QualityGate.CRITICAL},
            "no_hardcoded_secrets": {"threshold": True, "gate": QualityGate.CRITICAL},
            "max_duplicate_lines": {"threshold": 20, "gate": QualityGate.WARNING},
        }

    def check_file(self, filepath: str, content: str | None = None) -> dict[str, Any]:
        _ = self.trace("check_file")
        """检查单个文件"""
        if content is None:
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return {"passed": True, "issues": []}

        issues = []
        lines = content.split("\n")

        # 最大行数
        if len(lines) > self._rules["max_file_lines"]["threshold"]:
            issues.append(
                {
                    "rule": "max_file_lines",
                    "value": len(lines),
                    "threshold": self._rules["max_file_lines"]["threshold"],
                    "gate": QualityGate.WARNING.value,
                    "message": f"文件行数 {len(lines)} 超过阈值 {self._rules['max_file_lines']['threshold']}",
                }
            )

        # 函数长度检查
        current_func_start = 0
        current_func_indent = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            if stripped.startswith("def ") or stripped.startswith("async def "):
                func_lines = i - current_func_start
                if current_func_start > 0 and func_lines > self._rules["max_function_lines"]["threshold"]:
                    issues.append(
                        {
                            "rule": "max_function_lines",
                            "value": func_lines,
                            "threshold": self._rules["max_function_lines"]["threshold"],
                            "gate": QualityGate.WARNING.value,
                            "message": f"函数超过 {func_lines} 行 (阈值: {self._rules['max_function_lines']['threshold']})",
                            "line": current_func_start + 1,
                        }
                    )
                current_func_start = i
                current_func_indent = indent

        # 硬编码密钥检测
        secret_patterns = [
            r'(?:password|passwd|pwd|secret|token|api_key|apikey)\s*=\s*["\'][^"\']{8,}["\']',
            r'(?:AWS_ACCESS_KEY|AWS_SECRET)\s*=\s*["\'][A-Z0-9]{16,}["\']',
        ]
        import re

        for pattern in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for m in matches:
                issues.append(
                    {
                        "rule": "no_hardcoded_secrets",
                        "gate": QualityGate.CRITICAL.value,
                        "message": f"检测到可能的硬编码密钥",
                    }
                )

        # 重复行检测
        line_counts: dict[str, int] = defaultdict(int)
        for line in lines:
            if line.strip() and not line.strip().startswith("#"):
                line_counts[line.strip()] += 1
        duplicates = {k: v for k, v in line_counts.items() if v > 3}
        max_dup = max(duplicates.values()) if duplicates else 0
        if max_dup > self._rules["max_duplicate_lines"]["threshold"]:
            issues.append(
                {
                    "rule": "max_duplicate_lines",
                    "value": max_dup,
                    "threshold": self._rules["max_duplicate_lines"]["threshold"],
                    "gate": QualityGate.WARNING.value,
                    "message": f"检测到重复代码块 (最大重复 {max_dup} 次)",
                }
            )

        critical = any(i["gate"] == QualityGate.CRITICAL.value for i in issues)
        return {"passed": not critical, "issues": issues, "file": filepath, "lines": len(lines)}

    def check_project(self, project_path: str) -> dict[str, Any]:
        """检查整个项目"""
        p = Path(project_path)
        all_issues = []
        file_results = []
        total_files = 0
        passed_files = 0

        for py_file in p.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            total_files += 1
            result = self.check_file(str(py_file))
            file_results.append(result)
            if result["passed"]:
                passed_files += 1
            all_issues.extend(result["issues"])

        critical_count = sum(1 for i in all_issues if i["gate"] == QualityGate.CRITICAL.value)
        warning_count = sum(1 for i in all_issues if i["gate"] == QualityGate.WARNING.value)

        return {
            "passed": critical_count == 0,
            "total_files": total_files,
            "passed_files": passed_files,
            "critical_issues": critical_count,
            "warning_issues": warning_count,
            "issues": all_issues[:50],
            "pass_rate": round(passed_files / total_files * 100, 1) if total_files > 0 else 0,
        }

# ============================================================
class BuildDependencyResolver:
    """构建依赖解析器 - 分析项目依赖树，检测版本冲突和循环引用。

    企业场景：单体仓库中数百个模块的依赖关系管理，
    需要解析requirements.txt/pyproject.toml/Cargo.toml等，检测版本冲突。
    """

    def __init__(self):
        self._deps: dict[str, dict] = {}  # package -> {version, dependencies[]}
        self._lock = threading.Lock()

    def add_package(self, name: str, version: str, depends_on: list[str] = None):
        """注册包及其版本和依赖"""
        self._deps[name] = {"version": version, "depends": depends_on or []}

    def detect_conflicts(self) -> list[dict]:
        """检测版本冲突和循环依赖"""
        conflicts = []
        # 版本冲突：同一包不同版本
        version_map: dict[str, set[str]] = defaultdict(set)
        for pkg, info in self._deps.items():
            for dep in info["depends"]:
                dep_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
                version_map[dep_name].add(pkg)
        # 循环依赖检测
        cycles = self._find_cycles()
        for cycle in cycles:
            conflicts.append(
                {
                    "type": "circular_dependency",
                    "cycle": cycle,
                    "severity": "critical",
                    "fix": f"解除 {cycle[0]} -> {cycle[1]} 的依赖关系",
                }
            )
        return conflicts

    def _find_cycles(self) -> list[list[str]]:
        """DFS检测循环依赖"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {pkg: WHITE for pkg in self._deps}
        cycles = []
        path = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)
            for dep in self._deps.get(node, {}).get("depends", []):
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                if dep_name not in color:
                    continue
                if color[dep_name] == GRAY:
                    idx = path.index(dep_name)
                    cycles.append(path[idx:] + [dep_name])
                elif color[dep_name] == WHITE:
                    dfs(dep_name)
            path.pop()
            color[node] = BLACK

        for pkg in self._deps:
            if color[pkg] == WHITE:
                dfs(pkg)
        return cycles

    def topological_sort(self) -> list[str]:
        """拓扑排序 - 返回安全的构建顺序"""
        in_degree = {pkg: 0 for pkg in self._deps}
        for pkg, info in self._deps.items():
            for dep in info["depends"]:
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                if dep_name in in_degree:
                    in_degree[dep_name] = in_degree.get(dep_name, 0)
        # 重新计算入度
        in_degree = {pkg: 0 for pkg in self._deps}
        for pkg, info in self._deps.items():
            for dep in info["depends"]:
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                if dep_name in self._deps:
                    in_degree[dep_name] += 0  # dep_name is depended on by pkg
        # Correct: pkg depends on dep_name, so pkg should come AFTER dep_name
        reverse_deps = defaultdict(set)
        for pkg, info in self._deps.items():
            for dep in info["depends"]:
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                if dep_name in self._deps:
                    reverse_deps[dep_name].add(pkg)
        # in_degree = number of deps a package has
        in_degree = {
            pkg: len([d for d in info["depends"] if d.split(">=")[0].split("==")[0].strip() in self._deps])
            for pkg, info in self._deps.items()
        }
        queue = [pkg for pkg, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            queue.sort()  # 确定性顺序
            node = queue.pop(0)
            result.append(node)
            for dependent in reverse_deps.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        return result

    def estimate_build_impact(self, changed_package: str) -> dict:
        """估算变更包的影响范围 - 受影响的下游包数量和构建时间"""
        affected = set()
        queue = [changed_package]
        visited = {changed_package}
        while queue:
            pkg = queue.pop(0)
            for other, info in self._deps.items():
                deps = [d.split(">=")[0].split("==")[0].strip() for d in info["depends"]]
                if pkg in deps and other not in visited:
                    visited.add(other)
                    affected.add(other)
                    queue.append(other)
        return {
            "changed": changed_package,
            "affected_count": len(affected),
            "affected_packages": sorted(affected),
            "estimated_build_time_min": len(affected) * 5,
            "risk_level": "high" if len(affected) > 10 else "medium" if len(affected) > 3 else "low",
        }

# 主模块: AgentHephaestus
# ============================================================

class AgentHephaestus(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    Hephaestus智能体 — 代码构建引擎

    功能:
    - 多语言构建编排 (Python/Node.js/Java/Go/Rust)
    - 构建缓存与增量编译
    - 依赖解析与循环检测
    - 代码质量门禁
    - 构建产物管理
    - 并行构建队列
    """

    def __init__(self, config: dict | None = None):

        super().__init__(module_name="agent_hephaestus", version="6.39.0", config=config)
        self._builds: OrderedDict[str, BuildResult] = OrderedDict()
        self._configs: dict[str, BuildConfig] = {}
        self._artifacts: dict[str, BuildArtifact] = {}
        self._cache = BuildCacheManager()
        self._dep_resolver = DependencyResolver()
        self._quality_checker = QualityGateChecker()
        self._build_queue: list[str] = []
        self._queue_lock = threading.Lock()
        self._max_concurrent_builds = 2
        self._active_builds: set[str] = set()
        self._build_counter = 0
        self._stats = {
            "total_builds": 0,
            "successful_builds": 0,
            "failed_builds": 0,
            "cached_builds": 0,
            "total_artifacts": 0,
            "total_quality_checks": 0,
            "total_dependency_resolutions": 0,
        }

    async def initialize(self) -> None:
        """初始化模块"""
        self.audit("initialize", "agent_hephaestus_started")
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentHephaestus 代码构建引擎初始化完成")

    async def execute(self, action: str, params: dict | None = None) -> Result:
        """统一执行入口 — 路由到构建/质量检查/依赖解析"""
        _ = self.trace("execute")
        metrics_collector.counter("hephaestus_ops_total", labels={"action": action})
        params = params or {}

        if action == "register_project":
            cfg = (
                BuildConfig(**{k: v for k, v in params.items() if k in BuildConfig.__fields__})
                if hasattr(BuildConfig, "__fields__")
                else BuildConfig(project_path=params.get("project_path", ""))
            )
            result = await self.register_project(params.get("project_id", ""), cfg)
            self.audit("register_project", f"project_id={params.get('project_id', '')}")
            return result
        elif action == "trigger_build":
            result = await self.trigger_build(params.get("project_id", ""), params.get("branch", "main"))
            self.audit(
                "trigger_build", f"project_id={params.get('project_id', '')}, branch={params.get('branch', 'main')}"
            )
            return result
        elif action == "quality_check":
            result = await self.run_quality_check(params.get("project_path", ""))
            self.audit("quality_check", f"path={params.get('project_path', '')}")
            return result
        elif action == "resolve_deps":
            return await self.resolve_dependencies(params.get("project_path", ""))
        elif action == "get_build":
            return await self.get_build(params.get("build_id", ""))
        elif action == "list_builds":
            return await self.list_builds(params.get("project_id"), limit=params.get("limit", 20))
        elif action == "stats":
            return await self.get_module_stats()
        elif action == "health":
            hr = self.health_check()
            return Result(success=True, data={"status": "healthy"} if not hasattr(hr, "to_dict") else hr.to_dict())
        else:
            return Result(success=False, error=f"Unknown action: {action}")

    # ========================================================
    # 构建管理
    # ========================================================

    async def register_project(self, project_id: str, config: BuildConfig) -> Result:
        """注册项目构建配置"""
        self._configs[project_id] = config
        return Result(success=True, message=f"项目 {project_id} 注册成功", data=config.to_dict())

    async def trigger_build(self, project_id: str, force_rebuild: bool = False) -> Result:
        """触发构建"""
        config = self._configs.get(project_id)
        if not config:
            return Result(success=False, message=f"项目 {project_id} 未注册")

        self._build_counter += 1
        build_id = f"build_{project_id}_{self._build_counter}_{int(time.time())}"

        # 缓存检查
        if config.cache_enabled and not force_rebuild:
            source_hash = self._cache.compute_source_hash(config.project_path)
            cache_key = f"{project_id}_{source_hash}"
            cached = self._cache.get_cached_result(cache_key)
            if cached:
                cached.build_id = build_id
                cached.status = BuildStatus.CACHED
                self._builds[build_id] = cached
                self._stats["cached_builds"] += 1
                self._stats["total_builds"] += 1
                await self._audit_log("build_cached", f"构建缓存命中: {build_id}")
                return Result(success=True, message="构建缓存命中", data=cached.to_dict())

        # 创建构建结果
        result = BuildResult(
            build_id=build_id,
            project_path=config.project_path,
            language=config.language.value,
            status=BuildStatus.QUEUED,
        )
        self._builds[build_id] = result
        self._build_queue.append(build_id)

        await self._audit_log("build_queued", f"构建入队: {build_id}")

        # 同步执行构建
        return await self._execute_build(build_id, config)

    async def _execute_build(self, build_id: str, config: BuildConfig) -> Result:
        """执行构建"""
        result = self._builds.get(build_id)
        if not result:
            return Result(success=False, message=f"构建 {build_id} 不存在")

        result.status = BuildStatus.RUNNING
        result.started_at = time.time()

        try:
            pass
            # 1. 质量门禁检查
            quality_report = self._quality_checker.check_project(config.project_path)
            result.quality_report = quality_report
            self._stats["total_quality_checks"] += 1

            critical_issues = quality_report.get("critical_issues", 0)
            gate_level = config.quality_gates.get("code_quality", QualityGate.WARNING)
            if gate_level == QualityGate.CRITICAL and critical_issues > 0:
                result.status = BuildStatus.FAILED
                result.error_message = f"质量门禁失败: {critical_issues} 个严重问题"
                result.finished_at = time.time()
                self._stats["failed_builds"] += 1
                self._stats["total_builds"] += 1
                await self._audit_log("build_quality_gate_failed", result.error_message)
                return Result(success=False, message=result.error_message, data=result.to_dict())

            # 2. 依赖解析
            if config.dependencies:
                deps, cycles = self._dep_resolver.resolve_python(config.project_path)
                self._stats["total_dependency_resolutions"] += 1
                if cycles:
                    logger.warning(f"检测到 {len(cycles)} 个循环依赖")

            # 3. 执行构建命令
            env = os.environ.copy()
            env.update(config.env_vars)

            build_cmd = config.build_command or self._get_default_build_cmd(config.language)
            if not build_cmd:
                result.status = BuildStatus.FAILED
                result.error_message = f"不支持的语言: {config.language.value}"
                result.finished_at = time.time()
                self._stats["failed_builds"] += 1
                self._stats["total_builds"] += 1
                return Result(success=False, message=result.error_message)

            proc = subprocess.run(
                build_cmd,
                shell=True,
                cwd=config.project_path,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                env=env,
            )

            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr

            # 4. 执行测试命令
            if config.test_command and proc.returncode == 0:
                test_proc = subprocess.run(
                    config.test_command,
                    shell=True,
                    cwd=config.project_path,
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_seconds,
                    env=env,
                )
                result.stdout += "\n--- TEST OUTPUT ---\n" + test_proc.stdout
                result.stderr += "\n--- TEST STDERR ---\n" + test_proc.stderr
                if test_proc.returncode != 0:
                    result.exit_code = test_proc.returncode

            # 5. 收集构建产物
            if config.output_dir and os.path.isdir(config.output_dir):
                artifacts = self._collect_artifacts(config.output_dir, build_id)
                result.artifacts = artifacts
                for art in artifacts:
                    self._artifacts[art.artifact_id] = art

            result.finished_at = time.time()
            result.status = BuildStatus.SUCCESS if result.exit_code == 0 else BuildStatus.FAILED

            # 6. 缓存结果
            if config.cache_enabled and result.status == BuildStatus.SUCCESS:
                source_hash = self._cache.compute_source_hash(config.project_path)
                cache_key = f"{config.project_path}_{source_hash}"
                self._cache.cache_result(cache_key, result)

            if result.status == BuildStatus.SUCCESS:
                self._stats["successful_builds"] += 1
                self._stats["total_artifacts"] += len(result.artifacts)
            else:
                self._stats["failed_builds"] += 1
            self._stats["total_builds"] += 1

            await self._audit_log("build_completed", f"构建完成: {build_id} -> {result.status.value}")

            return Result(
                success=result.status == BuildStatus.SUCCESS,
                message=f"构建{'成功' if result.status == BuildStatus.SUCCESS else '失败'}",
                data=result.to_dict(),
            )

        except subprocess.TimeoutExpired:
            result.status = BuildStatus.TIMEOUT
            result.error_message = f"构建超时 ({config.timeout_seconds}s)"
            result.finished_at = time.time()
            self._stats["failed_builds"] += 1
            self._stats["total_builds"] += 1
            return Result(success=False, message=result.error_message, data=result.to_dict())
        except Exception as e:
            result.status = BuildStatus.FAILED
            result.error_message = str(e)
            result.finished_at = time.time()
            self._stats["failed_builds"] += 1
            self._stats["total_builds"] += 1
            logger.error(f"构建异常: {e}")
            return Result(success=False, message=f"构建异常: {str(e)}", data=result.to_dict())

    def _get_default_build_cmd(self, language: Language) -> str:
        """获取默认构建命令"""
        defaults = {
            Language.PYTHON: "python -m py_compile *.py",
            Language.NODEJS: "npm run build",
            Language.JAVA: "mvn clean package -DskipTests",
            Language.GO: "go build -o build/app .",
            Language.RUST: "cargo build --release",
            Language.CPP: "cmake --build build --config Release",
            Language.GENERIC: "echo 'No build command configured'",
        }
        return defaults.get(language, "")

    def _collect_artifacts(self, output_dir: str, build_id: str) -> list[BuildArtifact]:
        """收集构建产物"""
        artifacts = []
        for root, _, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    stat = os.stat(fpath)
                    with open(fpath, "rb") as f:
                        content = f.read()
                    art = BuildArtifact(
                        artifact_id=f"{build_id}_{hashlib.md5(fpath.encode()).hexdigest()[:8]}",
                        name=fname,
                        path=fpath,
                        size_bytes=stat.st_size,
                        checksum_md5=hashlib.md5(content).hexdigest(),
                        checksum_sha256=hashlib.sha256(content).hexdigest(),
                    )
                    artifacts.append(art)
                except Exception:
                    continue
        return artifacts

    # ========================================================
    # 构建查询
    # ========================================================

    async def get_build(self, build_id: str) -> Result:
        """获取构建结果"""
        result = self._builds.get(build_id)
        if not result:
            return Result(success=False, message=f"构建 {build_id} 不存在")
        return Result(success=True, data=result.to_dict())

    async def list_builds(
        self, project_id: str | None = None, status: BuildStatus | None = None, limit: int = 50
    ) -> Result:
        """列出构建历史"""
        builds = list(self._builds.values())
        if project_id:
            builds = [b for b in builds if project_id in b.project_path]
        if status:
            builds = [b for b in builds if b.status == status]
        builds = list(reversed(builds))[:limit]
        return Result(success=True, data={"builds": [b.to_dict() for b in builds], "total": len(builds)})

    # ========================================================
    # 依赖管理
    # ========================================================

    async def resolve_dependencies(self, project_path: str, language: Language = Language.PYTHON) -> Result:
        """解析项目依赖"""
        self._stats["total_dependency_resolutions"] += 1
        if language == Language.PYTHON:
            deps, cycles = self._dep_resolver.resolve_python(project_path)
        elif language == Language.NODEJS:
            deps, cycles = self._dep_resolver.resolve_nodejs(project_path)
        else:
            return Result(success=False, message=f"不支持的依赖解析语言: {language.value}")

        await self._audit_log("resolve_dependencies", f"解析 {len(deps)} 个依赖, {len(cycles)} 个循环")

        return Result(
            success=True,
            data={
                "dependencies": [d.to_dict() for d in deps],
                "cycles": cycles,
                "dependency_count": len(deps),
                "cycle_count": len(cycles),
            },
        )

    # ========================================================
    # 质量检查
    # ========================================================

    async def run_quality_check(self, project_path: str) -> Result:
        """执行代码质量检查"""
        report = self._quality_checker.check_project(project_path)
        self._stats["total_quality_checks"] += 1
        return Result(success=report["passed"], data=report)

    # ========================================================
    # 健康检查
    # ========================================================

    def health_check(self) -> HealthReport:
        """健康检查"""
        # 链路追踪
        trace_id = f"hephaestus-health-{int(time.time() * 1000)}"
        span_start = time.time()
        checks = {
            "build_store": len(self._builds) >= 0,
            "cache_manager": self._cache is not None,
            "dep_resolver": self._dep_resolver is not None,
            "quality_checker": self._quality_checker is not None,
        }
        all_ok = all(checks.values())
        metrics_collector.histogram("hephaestus_health_trace_duration", time.time() - span_start)
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING if all_ok else ModuleStatus.DEGRADED,
            checks=checks,
            stats=ModuleStats(
                total_operations=self._stats["total_builds"],
                custom_stats={**self._stats, "cache_stats": self._cache.get_stats()},
            ),
        )

    async def get_module_stats(self) -> Result:
        """获取模块统计"""
        return Result(success=True, data=self._stats)

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

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_hephaestus."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentHephaestus
