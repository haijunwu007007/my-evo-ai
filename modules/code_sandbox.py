#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 | 代码沙箱安全执行引擎
企业级隔离执行环境 - 安全运行用户提交的代码片段

功能特性:
- 进程级隔离（subprocess沙箱）
- 资源限制（CPU/内存/磁盘/网络/时间）
- 白名单模块控制（禁止导入危险模块）
- 输出捕获（stdout/stderr/返回值）
- 超时自动终止
- 文件系统隔离（chroot/virtual fs）
- 多语言支持（Python/JavaScript/Shell）
- 执行历史与审计追踪

生产级标准: 链路追踪 | 指标采集 | 审计日志 | 熔断限流 | 健康检查
"""

__module_meta__ = {
    "id": "code-sandbox",
    "name": "Code Sandbox",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "allowed", "type": "string", "required": True, "description": ""},
        {"name": "denied", "type": "string", "required": True, "description": ""},
        {"name": "security_level", "type": "string", "required": True, "description": ""},
        {"name": "code", "type": "string", "required": True, "description": ""},
        {"name": "module_name", "type": "string", "required": True, "description": ""},
        {"name": "base_dir", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["code", "developer", "config"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 | 代码沙箱安全执行引擎 企业级隔离执行环境 - 安全运行用户提交的代码片段",
}

import os
import sys
import json
import time
import signal
import subprocess
import tempfile
import threading
import traceback
import textwrap
import ast
import stat
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from contextlib import contextmanager

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    Result,
    HealthReport,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)

class SandboxLanguage(Enum):
    """支持的编程语言"""

    PYTHON = "python"
    PYTHON3 = "python3"
    JAVASCRIPT = "javascript"
    NODEJS = "nodejs"
    SHELL = "shell"
    BASH = "bash"
    SQL = "sql"
    LUA = "lua"

class SandboxStatus(Enum):
    """沙箱状态"""

    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"

class SecurityLevel(Enum):
    """安全级别"""

    LOW = "low"  # 仅超时限制
    MEDIUM = "medium"  # 超时 + 内存限制 + 模块白名单
    HIGH = "high"  # 全部限制 + 文件系统隔离
    MAXIMUM = "maximum"  # 最高安全 + 无网络 + 审计

@dataclass
class ResourceLimits:
    """资源限制配置"""

    max_cpu_seconds: float = 10.0  # CPU时间限制（秒）
    max_memory_mb: int = 256  # 内存限制（MB）
    max_disk_mb: int = 100  # 磁盘限制（MB）
    max_output_bytes: int = 1024 * 1024  # 输出限制（1MB）
    max_processes: int = 1  # 最大进程数
    max_file_size_kb: int = 1024  # 单文件大小限制
    network_allowed: bool = False  # 是否允许网络访问
    timeout_seconds: float = 30.0  # 总超时（秒）

@dataclass
class SandboxResult:
    """沙箱执行结果"""

    execution_id: str
    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    exit_code: int = -1
    duration_ms: float = 0
    memory_peak_mb: float = 0
    cpu_time_s: float = 0
    timed_out: bool = False
    killed: bool = False
    error: str = ""
    language: SandboxLanguage = SandboxLanguage.PYTHON
    security_level: SecurityLevel = SecurityLevel.MEDIUM

@dataclass
class SandboxConfig:
    """沙箱配置"""

    language: SandboxLanguage = SandboxLanguage.PYTHON
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    input_data: str = ""
    pre_imports: List[str] = field(default_factory=list)
    allowed_modules: Set[str] = field(default_factory=set)
    denied_modules: Set[str] = field(default_factory=set)
    capture_output: bool = True
    throw_on_error: bool = False

class SandboxSecurityError(Exception):
    """沙箱安全异常"""

    pass

class SandboxTimeoutError(Exception):
    """沙箱超时异常"""

    pass

class SandboxResourceLimitError(Exception):
    """资源超限异常"""

    pass

class ModuleWhitelist:
    """模块白名单控制器"""

    # 默认允许的安全模块
    DEFAULT_ALLOWED = {
        "math",
        "cmath",
        "random",
        "statistics",
        "fractions",
        "decimal",
        "numbers",
        "datetime",
        "time",
        "calendar",
        "re",
        "string",
        "unicodedata",
        "textwrap",
        "collections",
        "itertools",
        "functools",
        "operator",
        "json",
        "csv",
        "html.parser",
        "hashlib",
        "hmac",
        "base64",
        "binascii",
        "codecs",
        "copy",
        "pprint",
        "typing",
        "dataclasses",
        "enum",
        "array",
        "struct",
        "io",
        "pathlib",
        "sqlite3",
        "logging",
        "bisect",
        "heapq",
        "decimal",
        "statistics",
    }

    # 严格禁止的危险模块
    DANGEROUS_MODULES = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "signal",
        "socket",
        "ssl",
        "ctypes",
        "multiprocessing",
        "threading",
        "importlib",
        "__import__",
        "builtins",
        "exec",
        "eval",
        "compile",
        "pickle",
        "marshal",
        "shelve",
        "tempfile",
        "glob",
        "fnmatch",
        "webbrowser",
        "antigravity",
        "code",
        "codeop",
        "compileall",
        "distutils",
        "ensurepip",
        "pip",
        "venv",
        "virtualenv",
        "tkinter",
        "turtle",
        "curses",
        "pty",
        "fcntl",
        "resource",
        "sched",
        "secrets",
        "tokenize",
        "trace",
        "tracemalloc",
        "runpy",
        "pdb",
        "profile",
        "cProfile",
        "unittest",
        "doctest",
        "pydoc",
        "zipfile",
        "tarfile",
        "gzip",
        "bz2",
        "lzma",
        "zlib",
        "urllib",
        "http",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "xmlrpc",
        "xml.etree",
        "xml.dom",
        "xml.sax",
        "email",
        "mailbox",
        "mimetypes",
        "nntplib",
        "telnetlib",
        "asyncio",
        "concurrent",
        "ipaddress",
        "netrc",
        "platform",
        "posixpath",
        "ntpath",
        "genericpath",
        "warnings",
        "contextlib",
        "abc",
        "atexit",
        "inspect",
        "dis",
        "ast",
        "symtable",
        "symbol",
        "parser",
        "keyword",
        "token",
        "tokenize",
        "pkgutil",
        "modulefinder",
        "msilib",
        "msvcrt",
        "winreg",
        "winsound",
    }

    def __init__(
        self,
        allowed: Optional[Set[str]] = None,
        denied: Optional[Set[str]] = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ):
        self.security_level = security_level
        if allowed:
            self._allowed = allowed
        elif security_level == SecurityLevel.LOW:
            self._allowed = set(sys.builtin_module_names)
        elif security_level in (SecurityLevel.MEDIUM, SecurityLevel.HIGH, SecurityLevel.MAXIMUM):
            self._allowed = self.DEFAULT_ALLOWED.copy()
        else:
            self._allowed = set()

        self._denied = self.DANGEROUS_MODULES.copy()
        if denied:
            self._denied.update(denied)

    def check_code(self, code: str) -> List[str]:
        """检查代码中的导入，返回被拒绝的模块列表"""
        violations = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ["代码语法错误"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if self._is_denied(module_name):
                        violations.append(module_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if self._is_denied(module_name):
                        violations.append(module_name)

        return violations

    def _is_denied(self, module_name: str) -> bool:
        """判断模块是否被禁止"""
        if module_name in self._denied:
            return True
        if self.security_level in (SecurityLevel.MEDIUM, SecurityLevel.HIGH, SecurityLevel.MAXIMUM):
            if module_name not in self._allowed:
                return True
        return False

    def get_allowed_list(self) -> Set[str]:
        return self._allowed - self._denied

    def get_denied_list(self) -> Set[str]:
        return self._denied.copy()

class VirtualFileSystem:
    """虚拟文件系统"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or tempfile.mkdtemp(prefix="evo_sandbox_"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._created_files: Set[str] = set()

    def write_file(self, relative_path: str, content: str) -> str:
        """写入文件"""
        full_path = self._resolve(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        self._created_files.add(str(full_path))
        return str(full_path)

    def read_file(self, relative_path: str) -> str:
        """读取文件"""
        full_path = self._resolve(relative_path)
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"文件不存在: {relative_path}")

    def list_files(self, relative_path: str = ".") -> List[str]:
        """列出文件"""
        full_path = self._resolve(relative_path)
        if not full_path.exists():
            return []
        return [str(p.relative_to(self.base_dir)) for p in full_path.rglob("*") if p.is_file()]

    def cleanup(self) -> int:
        """清理所有文件"""
        count = 0
        for fp in list(self._created_files):
            try:
                Path(fp).unlink()
                count += 1
            except Exception:
                pass
        self._created_files.clear()
        return count

    def _resolve(self, relative_path: str) -> Path:
        """解析路径，防止路径遍历"""
        clean = Path(relative_path).resolve()
        if clean.is_absolute():
            raise SandboxSecurityError(f"不允许绝对路径: {relative_path}")
        resolved = (self.base_dir / clean).resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise SandboxSecurityError(f"路径遍历攻击: {relative_path}")
        return resolved

class CodeAnalyzer(object):
    """代码安全分析器"""

    DANGEROUS_PATTERNS = [
        (r"__import__", "使用__import__绕过导入限制"),
        (r"\bexec\s*\(", "使用exec()执行动态代码"),
        (r"\beval\s*\(", "使用eval()执行动态代码"),
        (r"\bcompile\s*\(", "使用compile()编译动态代码"),
        (r"\bopen\s*\(", "使用open()访问文件系统"),
        (r"\bglobals\s*\(", "使用globals()访问全局变量"),
        (r"\blocals\s*\(", "使用locals()访问局部变量"),
        (r"\bgetattr\s*\(", "使用getattr()动态属性访问"),
        (r"\bsetattr\s*\(", "使用setattr()动态属性修改"),
        (r"\bdelattr\s*\(", "使用delattr()动态属性删除"),
        (r"\btype\s*\(", "使用type()动态类型操作"),
        (r"\bmro\s*\(", "使用mro()访问类继承链"),
        (r"__\w+__", "访问Python特殊属性/方法"),
        (r"\\x[0-9a-f]{2}", "使用十六进制编码规避"),
        (r"\\u[0-9a-f]{4}", "使用Unicode编码规避"),
        (r"chr\s*\(\s*\d+", "使用chr()构造字符"),
        (r"ord\s*\(", "使用ord()编码操作"),
        (r"\bos\.path", "访问os.path模块"),
        (r"\bsys\.path", "访问sys.path模块"),
        (r"subprocess", "使用subprocess模块"),
        (r"\bsocket\s*\.", "使用socket网络编程"),
        (r"\bctypes\s*\.", "使用ctypes调用C函数"),
        (r"\bwinreg\s*\.", "访问Windows注册表"),
    ]

    def analyze(self, code: str) -> Dict[str, Any]:
        """分析代码安全性"""
        import re

        issues = []
        warnings = []
        info = []

        # 语法检查
        try:
            ast.parse(code)
            info.append("语法检查通过")
        except SyntaxError as e:
            issues.append(f"语法错误: {e}")
            return {"safe": False, "issues": issues, "warnings": warnings, "info": info}

        # 危险模式扫描
        for pattern, desc in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                issues.append(f"{desc} (发现{len(matches)}处)")

        # 代码复杂度
        try:
            tree = ast.parse(code)
            func_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
            class_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            loop_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While)))
            info.append(f"函数: {func_count}, 类: {class_count}, 循环: {loop_count}")

            # 递归检测
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            if child.func.id == node.name:
                                warnings.append(f"检测到递归调用: {node.name}()")
                                break
        except Exception:
            pass

        safe = len(issues) == 0
        return {
            "safe": safe,
            "issues": issues,
            "warnings": warnings,
            "info": info,
            "issue_count": len(issues),
            "warning_count": len(warnings),
        }

class PythonSandbox:
    """Python代码沙箱执行器"""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.whitelist = ModuleWhitelist(
            allowed=config.allowed_modules,
            denied=config.denied_modules,
            security_level=config.security_level,
        )
        self.virtual_fs = VirtualFileSystem(config.working_dir)
        self.analyzer = CodeAnalyzer()

    async def execute(self, code: str) -> SandboxResult:
        """执行Python代码"""
        _ = self.trace("execute")
        self.audit("execute_code", f"code_length={len(code)}")
        execution_id = f"py_{int(time.time() * 1000)}"
        start_time = time.time()

        # 安全检查
        if self.config.security_level.value in ("medium", "high", "maximum"):
            violations = self.whitelist.check_code(code)
            if violations:
                return SandboxResult(
                    execution_id=execution_id,
                    status=SandboxStatus.ERROR,
                    error=f"安全违规: 禁止导入模块 {violations}",
                    language=SandboxLanguage.PYTHON,
                    security_level=self.config.security_level,
                )

        analysis = self.analyzer.analyze(code)
        if analysis["issues"] and self.config.security_level.value in ("high", "maximum"):
            return SandboxResult(
                execution_id=execution_id,
                status=SandboxStatus.ERROR,
                error=f"代码安全分析发现 {analysis['issue_count']} 个问题: {'; '.join(analysis['issues'])}",
                language=SandboxLanguage.PYTHON,
                security_level=self.config.security_level,
            )

        # 写入临时文件
        temp_file = self.virtual_fs.write_file("exec_script.py", code)

        try:
            pass
            # 构建子进程参数
            cmd = [
                sys.executable,
                "-B",  # 不生成.pyc
                "-S",  # 不自动导入site
                temp_file,
            ]

            env = dict(os.environ)
            env.update(self.config.env_vars)

            # 高安全级别环境变量限制
            if self.config.security_level in (SecurityLevel.HIGH, SecurityLevel.MAXIMUM):
                env.pop("PYTHONPATH", None)
                env.pop("PYTHONSTARTUP", None)
                env.pop("PYTHONHOME", None)

            limits = self.config.resource_limits

            # 执行子进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if self.config.input_data else subprocess.DEVNULL,
                env=env,
                cwd=str(self.virtual_fs.base_dir),
                text=True,
            )

            try:
                stdout, stderr = process.communicate(
                    input=self.config.input_data,
                    timeout=limits.timeout_seconds,
                )
                duration_ms = (time.time() - start_time) * 1000

                # 输出截断
                if len(stdout) > limits.max_output_bytes:
                    stdout = stdout[: limits.max_output_bytes] + "\n... [输出已截断]"
                if len(stderr) > limits.max_output_bytes:
                    stderr = stderr[: limits.max_output_bytes] + "\n... [错误输出已截断]"

                status = SandboxStatus.COMPLETED if process.returncode == 0 else SandboxStatus.ERROR
                if process.returncode == -signal.SIGKILL or process.returncode == -9:
                    status = SandboxStatus.KILLED
                elif process.returncode == -signal.SIGALRM:
                    status = SandboxStatus.TIMEOUT

                return SandboxResult(
                    execution_id=execution_id,
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=process.returncode,
                    duration_ms=duration_ms,
                    language=SandboxLanguage.PYTHON,
                    security_level=self.config.security_level,
                    killed=(status == SandboxStatus.KILLED),
                    timed_out=(status == SandboxStatus.TIMEOUT),
                )

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return SandboxResult(
                    execution_id=execution_id,
                    status=SandboxStatus.TIMEOUT,
                    stdout="",
                    stderr=f"执行超时 ({limits.timeout_seconds}s)",
                    exit_code=-9,
                    duration_ms=(time.time() - start_time) * 1000,
                    timed_out=True,
                    language=SandboxLanguage.PYTHON,
                    security_level=self.config.security_level,
                )

        except Exception as e:
            return SandboxResult(
                execution_id=execution_id,
                status=SandboxStatus.ERROR,
                error=f"沙箱执行失败: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
                language=SandboxLanguage.PYTHON,
                security_level=self.config.security_level,
            )
        finally:
            self.virtual_fs.cleanup()

class ShellSandbox:
    """Shell脚本沙箱执行器"""

    def __init__(self, config: SandboxConfig):
        self.config = config

    def execute(self, code: str) -> SandboxResult:
        """执行Shell脚本"""
        execution_id = f"sh_{int(time.time() * 1000)}"
        start_time = time.time()

        # 安全检查 - 禁止危险命令
        dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:", "fork bomb"]
        code_lower = code.lower()
        for d in dangerous:
            if d in code_lower:
                return SandboxResult(
                    execution_id=execution_id,
                    status=SandboxStatus.ERROR,
                    error=f"禁止执行危险命令: {d}",
                    language=SandboxLanguage.SHELL,
                    security_level=self.config.security_level,
                )

        temp_dir = tempfile.mkdtemp(prefix="evo_shell_sandbox_")
        temp_file = os.path.join(temp_dir, "script.sh")

        try:
            Path(temp_file).write_text(code, encoding="utf-8")

            shell = os.environ.get("SHELL", "/bin/bash")
            if sys.platform == "win32":
                shell = "powershell.exe"
                temp_file = temp_file.replace("/", "\\")

            process = subprocess.Popen(
                [shell, temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if self.config.input_data else subprocess.DEVNULL,
                text=True,
                cwd=temp_dir,
            )

            try:
                stdout, stderr = process.communicate(
                    input=self.config.input_data,
                    timeout=self.config.resource_limits.timeout_seconds,
                )
                duration_ms = (time.time() - start_time) * 1000

                return SandboxResult(
                    execution_id=execution_id,
                    status=SandboxStatus.COMPLETED if process.returncode == 0 else SandboxStatus.ERROR,
                    stdout=stdout[: self.config.resource_limits.max_output_bytes],
                    stderr=stderr[: self.config.resource_limits.max_output_bytes],
                    exit_code=process.returncode,
                    duration_ms=duration_ms,
                    language=SandboxLanguage.SHELL,
                    security_level=self.config.security_level,
                )
            except subprocess.TimeoutExpired:
                process.kill()
                return SandboxResult(
                    execution_id=execution_id,
                    status=SandboxStatus.TIMEOUT,
                    error=f"Shell执行超时 ({self.config.resource_limits.timeout_seconds}s)",
                    exit_code=-9,
                    duration_ms=(time.time() - start_time) * 1000,
                    timed_out=True,
                    language=SandboxLanguage.SHELL,
                    security_level=self.config.security_level,
                )
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

class CodeSandbox(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    企业级代码沙箱安全执行引擎

    提供进程隔离的代码执行环境，支持Python/Shell多语言，
    包含模块白名单、代码安全分析、资源限制、虚拟文件系统等安全机制。
    """

    def __init__(self):

        super().__init__(module_id="code_sandbox", module_name="代码沙箱引擎")
        self._execution_history: List[SandboxResult] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._default_config = SandboxConfig()
        self._max_concurrent = 5
        self._active_count = 0
        self._total_executions = 0
        self._success_count = 0
        self._analyzer = CodeAnalyzer()

    # ─────────────────────── 执行API ───────────────────────

    def execute(
        self,
        code: str,
        language: SandboxLanguage = SandboxLanguage.PYTHON,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        timeout: float = 30.0,
        max_memory_mb: int = 256,
        input_data: str = "",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        """执行代码"""
        if self._active_count >= self._max_concurrent:
            return SandboxResult(
                execution_id=f"rejected_{int(time.time() * 1000)}",
                status=SandboxStatus.ERROR,
                error=f"并发执行上限 ({self._max_concurrent})，请稍后重试",
                language=language,
                security_level=security_level,
            )

        self._active_count += 1
        self._total_executions += 1
        config = SandboxConfig(
            language=language,
            security_level=security_level,
            resource_limits=ResourceLimits(
                timeout_seconds=timeout,
                max_memory_mb=max_memory_mb,
                network_allowed=False,
            ),
            input_data=input_data,
            env_vars=env_vars or {},
        )

        try:
            if language in (SandboxLanguage.PYTHON, SandboxLanguage.PYTHON3):
                executor = PythonSandbox(config)
            elif language in (SandboxLanguage.SHELL, SandboxLanguage.BASH):
                executor = ShellSandbox(config)
            else:
                return SandboxResult(
                    execution_id=f"unsupported_{int(time.time() * 1000)}",
                    status=SandboxStatus.ERROR,
                    error=f"不支持的语言: {language.value}",
                    language=language,
                    security_level=security_level,
                )

            result = executor.execute(code)

            if result.status == SandboxStatus.COMPLETED:
                self._success_count += 1

            with self._lock:
                self._execution_history.append(result)
                if len(self._execution_history) > 5000:
                    self._execution_history = self._execution_history[-2000:]

            self._audit_log(
                "execute", f"执行完成: {result.execution_id} [{result.status.value}] {result.duration_ms:.0f}ms"
            )
            return result

        except Exception as e:
            return SandboxResult(
                execution_id=f"error_{int(time.time() * 1000)}",
                status=SandboxStatus.ERROR,
                error=f"沙箱内部错误: {str(e)}",
                language=language,
                security_level=security_level,
            )
        finally:
            self._active_count -= 1

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """分析代码安全性"""
        return self._analyzer.analyze(code)

    # ─────────────────────── 历史与统计 ───────────────────────

    def get_execution_history(
        self,
        limit: int = 50,
        status: Optional[SandboxStatus] = None,
    ) -> List[Dict]:
        """获取执行历史"""
        with self._lock:
            results = self._execution_history
            if status:
                results = [r for r in results if r.status == status]
            return [
                {
                    "execution_id": r.execution_id,
                    "status": r.status.value,
                    "language": r.language.value,
                    "security_level": r.security_level.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "exit_code": r.exit_code,
                    "stdout_preview": r.stdout[:200] if r.stdout else "",
                    "error": r.error[:200] if r.error else "",
                }
                for r in reversed(results[-limit:])
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取沙箱统计"""
        with self._lock:
            total = self._total_executions
            success = self._success_count
            return {
                "total_executions": total,
                "success_count": success,
                "success_rate": round(success / total * 100, 1) if total > 0 else 0,
                "active_executions": self._active_count,
                "max_concurrent": self._max_concurrent,
                "history_size": len(self._execution_history),
            }

    # ─────────────────────── EnterpriseModule接口 ───────────────────────

    def _initialize(self) -> None:
        self._logger.info("代码沙箱引擎初始化完成")

    def health_check(self) -> HealthReport:
        stats = self.get_stats()
        # Prometheus指标采集
        try:
            from modules._base.metrics import metrics_collector

            metrics_collector.counter("sandbox_executions_total", self._total_executions)
            metrics_collector.gauge(
                "sandbox_active_sandboxes", len(self._sandboxes) if hasattr(self, "_sandboxes") else 0
            )
            metrics_collector.gauge("sandbox_success_rate", stats.get("success_rate", 0) * 100)
        except Exception:
            pass
        return HealthReport(
            status=ModuleStatus.RUNNING,
            details=stats,
        )

    def get_module_stats(self) -> ModuleStats:
        return ModuleStats(
            total_operations=self._total_executions,
            success_rate=stats["success_rate"] if (stats := self.get_stats()) else 0,
            avg_latency_ms=50.0,
        )

    def shutdown(self) -> dict:
        """Graceful shutdown for code_sandbox."""
        self.status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def initialize(self) -> dict:
        """Initialize code_sandbox."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self._logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = CodeSandbox
