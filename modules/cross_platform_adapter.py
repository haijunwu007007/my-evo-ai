import time

"""
AUTO-EVO-AI V0.1 — 跨平台兼容转译层 (Cross-Platform Adapter)
命名空间: evo.adapter.platform.*
优先级: P0 (紧急)

功能概述:
- 自动检测当前操作系统 (Windows/macOS/Linux)
- 将平台相关调用转译为统一接口
- 路径规范化 (正斜杠/反斜杠互转)
- Shell 命令适配 (cmd/powershell/bash/zsh)
- 环境变量跨平台读写
- 信号处理统一封装
- 进程管理抽象层
"""

__module_meta__ = {
    "id": "cross-platform-adapter",
    "name": "Cross Platform Adapter",
    "version": "V0.1",
    "group": "system",
    "inputs": [
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
        {"name": "days", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "cross"],
    "grade": "C",
    "description": "AUTO-EVO-AI V0.1 — 跨平台兼容转译层 (Cross-Platform Adapter) 命名空间: evo.adapter.platform.*",
}

import os
import sys
import platform
import subprocess
import signal
import shutil
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.adapter.platform")

class CrossPlatformAdapterAnalyzer(EnterpriseModule):
    """cross_platform_adapter 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        super().__init__()
        self._operation_count = 0
        self._error_count = 0
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "cross_platform_adapter"
        self.version = "1.0.0"
        self._analyzer = self
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "CrossPlatformAdapterAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "cross_platform_adapter"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== cross_platform_adapter ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        action = action or "status"
        try:
            self._operation_count += 1
            if action == "status":
                return {
                    "success": True,
                    "data": {"status": "running", "operations": self._operation_count, "errors": self._error_count},
                }
            elif action == "stats":
                return {"success": True, "data": {"operations": self._operation_count, "errors": self._error_count}}
            elif action == "health":
                return {"success": True, "data": {"healthy": True}}
            elif action == "configure":
                return {"success": True, "data": {"message": "Configured"}}
            elif action == "reset":
                self._operation_count = 0
                self._error_count = 0
                return {"success": True, "data": {"message": "Reset"}}
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            self._error_count += 1
            return {"success": False, "error": str(e)}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class OSType(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    UNKNOWN = "unknown"

class ShellType(Enum):
    CMD = "cmd"
    POWERSHELL = "powershell"
    BASH = "bash"
    ZSH = "zsh"
    SH = "sh"
    UNKNOWN = "unknown"

@dataclass
class PlatformInfo:
    """当前平台详细信息"""

    os_type: OSType
    os_name: str
    os_version: str
    machine: str
    processor: str
    python_version: str
    shell_type: ShellType
    home_dir: str
    is_wsl: bool = False
    is_64bit: bool = True
    env_vars: Dict[str, str] = field(default_factory=dict)

class PathAdapter:
    """跨平台路径适配器"""

    @staticmethod
    def normalize(path: str) -> str:
        """规范化路径分隔符为当前平台格式"""
        if not path:
            return path
        if platform.system() == "Windows":
            return path.replace("/", "\\")
        return path.replace("\\", "/")

    @staticmethod
    def to_posix(path: str) -> str:
        """转正斜杠 (POSIX格式)"""
        return path.replace("\\", "/")

    @staticmethod
    def to_windows(path: str) -> str:
        """转反斜杠 (Windows格式)"""
        return path.replace("/", "\\")

    @staticmethod
    def ensure_trailing_sep(path: str) -> str:
        """确保路径以分隔符结尾"""
        sep = "\\" if platform.system() == "Windows" else "/"
        if not path.endswith(sep):
            return path + sep
        return path

    @staticmethod
    def join(*parts: str) -> str:
        """跨平台路径拼接"""
        return str(Path(*parts))

    @staticmethod
    def expand_user(path: str) -> str:
        """展开 ~ 为用户目录"""
        return str(Path(path).expanduser())

    @staticmethod
    def is_same_file(p1: str, p2: str) -> bool:
        """判断两个路径是否指向同一文件"""
        try:
            return os.path.samefile(p1, p2)
        except (OSError, FileNotFoundError):
            return False

    @staticmethod
    def get_relative(base: str, target: str) -> str:
        """获取相对路径"""
        return str(Path(target).relative_to(Path(base)))

class ShellAdapter:
    """跨平台 Shell 命令适配器"""

    def __init__(self, platform_info: PlatformInfo):
        self.platform = platform_info

    def detect_default_shell(self) -> ShellType:
        """检测当前默认 Shell"""
        if self.platform.os_type == OSType.WINDOWS:
            if (
                "powershell" in os.environ.get("SHELL", "").lower()
                or shutil.which("pwsh")
                or shutil.which("powershell")
            ):
                return ShellType.POWERSHELL
            return ShellType.CMD
        # macOS / Linux
        shell_env = os.environ.get("SHELL", "")
        if "zsh" in shell_env:
            return ShellType.ZSH
        if "bash" in shell_env:
            return ShellType.BASH
        return ShellType.SH

    def build_command(self, cmd: str, shell: Optional[ShellType] = None) -> List[str]:
        """构建平台适配的命令列表"""
        target_shell = shell or self.detect_default_shell()

        if target_shell == ShellType.CMD:
            return ["cmd", "/c", cmd]
        elif target_shell == ShellType.POWERSHELL:
            return ["powershell", "-NoProfile", "-Command", cmd]
        elif target_shell == ShellType.BASH:
            return ["bash", "-c", cmd]
        elif target_shell == ShellType.ZSH:
            return ["zsh", "-c", cmd]
        else:
            return ["sh", "-c", cmd]

    def execute(
        self,
        cmd: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        capture: bool = True,
        shell: Optional[ShellType] = None,
    ) -> Tuple[int, str, str]:
        """
        跨平台执行命令
        Returns: (return_code, stdout, stderr)
        """
        cmd_list = self.build_command(cmd, shell)
        exec_env = None
        if env:
            exec_env = {**os.environ, **env}

        try:
            proc = subprocess.Popen(
                cmd_list,
                cwd=cwd,
                env=exec_env,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=timeout)
            return proc.returncode, stdout or "", stderr or ""
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -1, "", f"Shell executable not found for {shell or 'default'}"
        except Exception as e:
            return -1, "", str(e)

    def which(self, program: str) -> Optional[str]:
        """跨平台查找可执行文件"""
        return shutil.which(program)

class EnvAdapter:
    """跨平台环境变量适配器"""

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return os.environ.get(key, default)

    @staticmethod
    def set(key: str, value: str, persistent: bool = False) -> None:
        """
        设置环境变量
        persistent=True 时写入用户级环境变量 (Windows注册表 / .bashrc / .zshrc)
        """
        os.environ[key] = value
        if persistent:
            EnvAdapter._persist_env(key, value)

    @staticmethod
    def delete(key: str, persistent: bool = False) -> None:
        """删除环境变量"""
        os.environ.pop(key, None)
        if persistent:
            EnvAdapter._unpersist_env(key)

    @staticmethod
    def get_all() -> Dict[str, str]:
        """获取所有环境变量"""
        return dict(os.environ)

    @staticmethod
    def _persist_env(key: str, value: str) -> None:
        """持久化环境变量到系统"""
        import winreg

        system = platform.system()
        try:
            if system == "Windows":
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as reg_key:
                    winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, value)
            elif system == "Linux" or system == "Darwin":
                shell_rc = os.path.expanduser("~/.bashrc")
                if os.path.exists(os.path.expanduser("~/.zshrc")):
                    shell_rc = os.path.expanduser("~/.zshrc")
                export_line = f'\nexport {key}="{value}"\n'
                with open(shell_rc, "a", encoding="utf-8") as f:
                    f.write(export_line)
        except Exception as e:
            logger.warning(f"Failed to persist env var {key}: {e}")

    @staticmethod
    def _unpersist_env(key: str) -> None:
        """从系统中移除持久化的环境变量"""
        import winreg

        system = platform.system()
        try:
            if system == "Windows":
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as reg_key:
                    winreg.DeleteValue(reg_key, key)
            elif system in ("Linux", "Darwin"):
                for rc in ["~/.bashrc", "~/.zshrc"]:
                    rc_path = os.path.expanduser(rc)
                    if os.path.exists(rc_path):
                        with open(rc_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        with open(rc_path, "w", encoding="utf-8") as f:
                            for line in lines:
                                if not line.strip().startswith(f"export {key}="):
                                    f.write(line)
        except Exception as e:
            logger.warning(f"Failed to unpersist env var {key}: {e}")

class SignalAdapter:
    """跨平台信号处理适配器"""

    # 信号映射: 标准名称 -> 平台信号
    SIGNAL_MAP = {
        "SIGINT": signal.SIGINT,
        "SIGTERM": signal.SIGTERM,
        "SIGHUP": signal.SIGHUP if hasattr(signal, "SIGHUP") else None,
        "SIGUSR1": signal.SIGUSR1 if hasattr(signal, "SIGUSR1") else None,
        "SIGUSR2": signal.SIGUSR2 if hasattr(signal, "SIGUSR2") else None,
    }

    @classmethod
    def get_signal(cls, name: str):
        """获取信号对象, Windows不支持时返回None"""
        return cls.SIGNAL_MAP.get(name.upper())

    @classmethod
    def register_handler(cls, sig_name: str, handler) -> bool:
        """注册信号处理器, 返回是否成功"""
        sig = cls.get_signal(sig_name)
        if sig is None:
            logger.debug(f"Signal {sig_name} not available on this platform")
            return False
        signal.signal(sig, handler)
        return True

    @classmethod
    def send_signal(cls, pid: int, sig_name: str) -> bool:
        """向进程发送信号"""
        sig = cls.get_signal(sig_name)
        if sig is None:
            logger.debug(f"Signal {sig_name} not available on this platform")
            return False
        try:
            os.kill(pid, sig)
            return True
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found")
            return False
        except PermissionError:
            logger.warning(f"Permission denied to signal process {pid}")
            return False

    @classmethod
    def graceful_shutdown_handler(cls):
        """生成优雅关停处理器"""
        import functools

        def handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            # 这里可以扩展为调用系统关停逻辑
            sys.exit(0)

        return handler

class ProcessAdapter:
    """跨平台进程管理"""

    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}

    def spawn(
        self,
        name: str,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        detached: bool = False,
    ) -> bool:
        """启动一个命名进程"""
        try:
            kwargs = {"cwd": cwd, "env": {**os.environ, **(env or {})}}
            if platform.system() == "Windows" and detached:
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True

            proc = subprocess.Popen(cmd, **kwargs)
            self._processes[name] = proc
            logger.info(f"Process '{name}' started (PID={proc.pid})")
            return True
        except Exception as e:
            logger.error(f"Failed to start process '{name}': {e}")
            return False

    def kill(self, name: str) -> bool:
        """终止指定进程"""
        proc = self._processes.get(name)
        if proc is None:
            logger.warning(f"Process '{name}' not found")
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            del self._processes[name]
            logger.info(f"Process '{name}' terminated")
            return True
        except Exception as e:
            logger.error(f"Failed to kill process '{name}': {e}")
            return False

    def list_processes(self) -> Dict[str, Dict[str, Any]]:
        """列出所有托管进程的状态"""
        result = {}
        for name, proc in self._processes.items():
            result[name] = {
                "pid": proc.pid,
                "status": "running" if proc.poll() is None else "exited",
                "returncode": proc.returncode,
            }
        return result

    def is_running(self, name: str) -> bool:
        """检查进程是否在运行"""
        proc = self._processes.get(name)
        return proc is not None and proc.poll() is None

class CrossPlatformAdapter:
    """
    跨平台兼容转译层 — 主入口
    统一接口, 自动适配 Windows/macOS/Linux/WSL
    """

    def __init__(self):
        self.info = self._detect_platform()
        self.path = PathAdapter()
        self.shell = ShellAdapter(self.info)
        self.env = EnvAdapter()
        self.signal = SignalAdapter()
        self.process = ProcessAdapter()
        logger.info(
            f"CrossPlatformAdapter initialized: {self.info.os_type.value} "
            f"{self.info.os_version} / {self.info.shell_type.value}"
        )

    def _detect_platform(self) -> PlatformInfo:
        """检测当前平台信息"""
        system = platform.system()
        release = platform.release()
        machine = platform.machine()
        processor = platform.processor() or ""
        py_version = platform.python_version()

        os_type = OSType.UNKNOWN
        is_wsl = False

        if system == "Windows":
            os_type = OSType.WINDOWS
            if "microsoft" in release.lower() or "wsl" in release.lower():
                os_type = OSType.WSL
                is_wsl = True
        elif system == "Darwin":
            os_type = OSType.MACOS
        elif system == "Linux":
            if "microsoft" in release.lower() or os.path.exists("/proc/version"):
                try:
                    with open("/proc/version", "r") as f:
                        if "microsoft" in f.read().lower():
                            os_type = OSType.WSL
                            is_wsl = True
                except Exception:
                    pass
            if os_type == OSType.UNKNOWN:
                os_type = OSType.LINUX

        is_64bit = sys.maxsize > 2**32

        # 先构建 PlatformInfo 用于 ShellAdapter 初始化
        temp_info = PlatformInfo(
            os_type=os_type,
            os_name=system,
            os_version=f"{system} {release}",
            machine=machine,
            processor=processor,
            python_version=py_version,
            shell_type=ShellType.UNKNOWN,
            home_dir=str(Path.home()),
            is_wsl=is_wsl,
            is_64bit=is_64bit,
            env_vars=dict(os.environ),
        )
        info = temp_info
        # 创建 ShellAdapter 检测默认 Shell
        shell_adapter = ShellAdapter(info)
        info.shell_type = shell_adapter.detect_default_shell()
        return info

    def to_dict(self) -> Dict[str, Any]:
        """导出平台信息为字典"""
        return {
            "os_type": self.info.os_type.value,
            "os_name": self.info.os_name,
            "os_version": self.info.os_version,
            "machine": self.info.machine,
            "processor": self.info.processor,
            "python_version": self.info.python_version,
            "shell_type": self.info.shell_type.value,
            "home_dir": self.info.home_dir,
            "is_wsl": self.info.is_wsl,
            "is_64bit": self.info.is_64bit,
        }

    def run(self, cmd: str, **kwargs) -> Tuple[int, str, str]:
        """快捷执行命令"""
        return self.shell.execute(cmd, **kwargs)

    def check_dependency(self, name: str) -> Dict[str, Any]:
        """检查系统依赖是否安装"""
        path = shutil.which(name)
        if path:
            try:
                result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
                version = result.stdout.strip() or result.stderr.strip()
                return {"installed": True, "path": path, "version": version}
            except Exception:
                return {"installed": True, "path": path, "version": "unknown"}
        return {"installed": False, "path": None, "version": None}

    def check_dependencies(self, names: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量检查依赖"""
        return {name: self.check_dependency(name) for name in names}

# ── 模块初始化 ──────────────────────────────────────────────
adapter_instance: Optional[CrossPlatformAdapter] = None

def get_adapter() -> CrossPlatformAdapter:
    """获取全局单例"""
    global adapter_instance
    if adapter_instance is None:
        adapter_instance = CrossPlatformAdapter()
    return adapter_instance

__all__ = [
    "CrossPlatformAdapter",
    "PathAdapter",
    "ShellAdapter",
    "EnvAdapter",
    "SignalAdapter",
    "ProcessAdapter",
    "OSType",
    "ShellType",
    "PlatformInfo",
    "get_adapter",
]

module_class = CrossPlatformAdapterAnalyzer
