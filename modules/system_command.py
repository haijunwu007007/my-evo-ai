"""
AUTO-EVO-AI V0.1 — 系统命令执行器
Grade: A (生产级) | Category: 工具链
职责：安全执行系统命令、输出捕获、超时控制、命令历史、权限验证
"""

__module_meta__ = {
        "id": "system-command",
        "name": "System Command",
        "version": "V0.1",
        "group": "system",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_3",
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
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "adapter",
            "system"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — 系统命令执行器 Grade: A (生产级) | Category: 工具链"
    }

import re
import asyncio
import time
import uuid
import os
import platform
import subprocess
import logging
import shlex
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
    from _base.circuit_breaker import CircuitBreakerMixin
    from _base.rate_limiter import RateLimiterMixin

logger = logging.getLogger("system_command")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

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

class CommandStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class RiskLevel(Enum):
    SAFE = "safe"  # 只读命令
    LOW = "low"  # 低风险操作
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    BLOCKED = "blocked"  # 禁止执行

@dataclass
class CommandRule:
    """命令规则"""

    pattern: str
    risk_level: RiskLevel
    description: str
    require_approval: bool = False
    max_timeout: int = 300

@dataclass
class CommandResult:
    """命令执行结果"""

    execution_id: str
    command: str
    status: CommandStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    working_dir: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE
    approved: bool = False

@dataclass
class CommandHistory:
    """命令历史记录"""

    execution_id: str
    command: str
    status: str
    exit_code: int | None
    duration_ms: float
    risk_level: str
    executed_at: float
    executed_by: str

class CommandSafetyEvaluator:
    """命令安全检查器 — 风险评估、黑名单过滤、参数净化"""

    DANGEROUS_PATTERNS = [
        (r"rm\s+(-rf|-r)\s+/", 10, "recursive delete root"),
        (r"mkfs\b", 10, "format filesystem"),
        (r"dd\s+.*of=/dev/", 10, "direct device write"),
        (r">\s*/dev/sd[a-z]", 10, "overwrite disk"),
        (r"chmod\s+777\s+/", 9, "world-writable root"),
        (r"shutdown\b", 8, "system shutdown"),
        (r"reboot\b", 7, "system reboot"),
        (r"curl\b.*\|\s*bash", 9, "pipe to shell"),
        (r"wget\b.*\|\s*sh", 9, "pipe to shell"),
        (r":\(\)\{\s*:\|:\s*&\s*\};:", 10, "fork bomb"),
    ]

    def __init__(self):
        self._blocked_commands: list[dict[str, Any]] = []
        self._allowed_commands: list[dict[str, Any]] = []
        self._whitelist_patterns: list[str] = []

    def add_whitelist(self, pattern: str) -> None:
        self._whitelist_patterns.append(pattern)

    def check_command(self, command: str, user: str = "", source_ip: str = "") -> dict[str, Any]:
        for wp in self._whitelist_patterns:
            if re.search(wp, command):
                self._allowed_commands.append(
                    {"cmd": command[:100], "user": user, "matched_whitelist": wp, "timestamp": time.time()}
                )
                return {"allowed": True, "risk": 0, "reason": "whitelist_match"}
        risk_score = 0
        matched_rules = []
        cmd_lower = command.lower()
        for pattern, severity, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
                risk_score = max(risk_score, severity)
                matched_rules.append({"severity": severity, "description": description})
        if risk_score >= 8:
            self._blocked_commands.append(
                {
                    "cmd": command[:100],
                    "user": user,
                    "source_ip": source_ip,
                    "risk": risk_score,
                    "timestamp": time.time(),
                }
            )
            return {"allowed": False, "risk": risk_score, "reason": "dangerous_command", "matched_rules": matched_rules}
        if risk_score >= 5:
            return {
                "allowed": True,
                "risk": risk_score,
                "reason": "elevated_risk",
                "matched_rules": matched_rules,
                "requires_approval": True,
            }
        self._allowed_commands.append(
            {"cmd": command[:100], "user": user, "risk": risk_score, "timestamp": time.time()}
        )
        return {"allowed": True, "risk": risk_score, "reason": "safe"}

    def sanitize_args(self, args: list[str]) -> list[str]:
        sanitized = []
        for arg in args:
            cleaned = re.sub(r"[;&|`$]", "", arg)
            cleaned = re.sub(r"\.\.", "", cleaned)
            sanitized.append(cleaned)
        return sanitized

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_blocked": len(self._blocked_commands),
            "total_allowed": len(self._allowed_commands),
            "whitelist_count": len(self._whitelist_patterns),
            "recent_blocked": self._blocked_commands[-5:],
        }

class SystemCommand(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """系统命令执行器"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._rules: list[CommandRule] = []
        self._history: list[CommandHistory] = []
        self._active_commands: dict[str, asyncio.Task] = {}
        self._max_output_length = 1024 * 1024  # 1MB
        self._max_concurrent = 5
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._default_timeout = 60
        self._blocked_commands = [
            "rm -rf /",
            "del /S /Q C:\\",
            "mkfs",
            "dd if=/dev/zero",
            ":(){ :|:& };:",
            "shutdown -h now",
            "format ",
            "chkdsk /f",
        ]

    def initialize(self) -> None:
        self._register_default_rules()
        logger.info("系统命令执行器初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _register_default_rules(self) -> None:
        """注册默认命令规则"""
        safe_commands = [
            (r"^(ls|dir|cat|type|head|tail|wc|echo|pwd|cd|date|whoami|hostname|uname)$", "列出/显示文件"),
            (r"^(git (status|log|diff|branch|remote|tag|stash))", "Git只读命令"),
            (r"^(python|node|java|go|rustc) --version$", "版本检查"),
            (r"^(pip|npm|yarn|cargo) (list|show|version)", "包管理只读"),
            (r"^(df|free|top|ps|uptime|vmstat|mpstat)", "系统信息查看"),
            (r"^(ping|nslookup|dig|traceroute|curl -I|wget --spider)", "网络诊断"),
            (r"^(docker (ps|images|logs|inspect))", "Docker只读"),
            (r"^(kubectl (get|describe|top|logs))", "K8s只读"),
        ]
        for pattern, desc in safe_commands:
            self._rules.append(CommandRule(pattern, RiskLevel.SAFE, desc))

        low_commands = [
            (r"^(mkdir|touch|cp|mv|rename)$", "文件创建/复制/移动"),
            (r"^(git (add|commit|push|pull|merge|checkout))", "Git写操作"),
            (r"^(pip|npm|yarn|cargo) (install|update|uninstall)", "包管理安装"),
            (r"^(docker (run|build|pull|push))", "Docker操作"),
            (r"^(kubectl (apply|create|delete|scale|rollout))", "K8s操作"),
        ]
        for pattern, desc in low_commands:
            self._rules.append(CommandRule(pattern, RiskLevel.LOW, desc, require_approval=False))

        medium_commands = [
            (r"^(rm|del|rmdir) ", "文件删除"),
            (r"^(chmod|chown|icacls) ", "权限修改"),
            (r"^(systemctl|service) (start|stop|restart)", "服务管理"),
            (r"^(docker (stop|rm|rmi|network|volume))", "Docker写操作"),
        ]
        for pattern, desc in medium_commands:
            self._rules.append(CommandRule(pattern, RiskLevel.MEDIUM, desc, require_approval=True))

        high_commands = [
            (r"^(sudo|su )", "提权命令"),
            (r"^(apt|yum|dnf|brew) (install|remove|upgrade)", "系统包管理"),
            (r"^(systemctl|service) (enable|disable|mask)", "系统服务配置"),
            (r"^(iptables|ufw|firewall) ", "防火墙配置"),
        ]
        for pattern, desc in high_commands:
            self._rules.append(CommandRule(pattern, RiskLevel.HIGH, desc, require_approval=True))

        # 阻止的命令
        for cmd in self._blocked_commands:
            self._rules.append(CommandRule(f".*{re.escape(cmd)}.*", RiskLevel.BLOCKED, f"危险命令: {cmd}"))

    def _assess_risk(self, command: str) -> tuple[RiskLevel, CommandRule | None]:
        """评估命令风险"""
        cmd_base = command.strip().split()[0] if command.strip() else ""

        # 检查阻止命令
        for rule in self._rules:
            if rule.risk_level == RiskLevel.BLOCKED:
                import re

                if re.search(rule.pattern, command, re.IGNORECASE):
                    return RiskLevel.BLOCKED, rule

        # 按风险等级匹配
        for risk in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.SAFE]:
            for rule in self._rules:
                if rule.risk_level == risk:
                    import re

                    if re.search(rule.pattern, command, re.IGNORECASE):
                        return risk, rule

        return RiskLevel.MEDIUM, None  # 默认中等风险

    @trace_operation("execute_command")
    def execute(
        self,
        command: str,
        timeout: int | None = None,
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        """执行系统命令"""
        _ = self.trace("execute")
        execution_id = f"cmd_{uuid.uuid4().hex[:10]}"

        # 风险评估
        risk_level, rule = self._assess_risk(command)

        if risk_level == RiskLevel.BLOCKED:
            self.stats["blocked"] = self.stats.get("blocked", 0) + 1
            audit_logger.log(action="command_blocked", resource=execution_id, details=f"阻止执行: {command[:200]}")
            return {
                "execution_id": execution_id,
                "status": "blocked",
                "command": command,
                "reason": rule.description if rule else "安全策略",
            }

        if rule and rule.require_approval and not approved:
            return {
                "execution_id": execution_id,
                "status": "approval_required",
                "command": command,
                "risk_level": risk_level.value,
                "reason": rule.description if rule else "需要审批",
            }

        # 执行
        cmd_timeout = timeout or self._default_timeout
        if rule and rule.max_timeout:
            cmd_timeout = min(cmd_timeout, rule.max_timeout)

        try:
            with self._semaphore:
                result = self._run_command(execution_id, command, cmd_timeout, working_dir, env or {}, risk_level)
        except TimeoutError:
            result = CommandResult(
                execution_id=execution_id,
                command=command,
                status=CommandStatus.TIMEOUT,
                risk_level=risk_level,
                duration_ms=cmd_timeout * 1000,
            )
        except Exception as e:
            result = CommandResult(
                execution_id=execution_id,
                command=command,
                status=CommandStatus.FAILED,
                stderr=str(e),
                risk_level=risk_level,
            )

        # 记录历史
        self._history.append(
            CommandHistory(
                execution_id=result.execution_id,
                command=command,
                status=result.status.value,
                exit_code=result.exit_code,
                duration_ms=result.duration_ms,
                risk_level=risk_level.value,
                executed_at=time.time(),
                executed_by="system",
            )
        )

        metrics_collector.counter(f"cmd_{result.status.value}")
        audit_logger.log(
            action="command_executed",
            resource=execution_id,
            details=f"命令: {command[:200]}, 状态: {result.status.value}, 风险: {risk_level.value}",
        )

        return {
            "execution_id": result.execution_id,
            "command": result.command,
            "status": result.status.value,
            "exit_code": result.exit_code,
            "stdout": result.stdout[: self._max_output_length],
            "stderr": result.stderr[: self._max_output_length],
            "duration_ms": round(result.duration_ms, 2),
            "risk_level": result.risk_level.value,
        }

    def _run_command(
        self,
        execution_id: str,
        command: str,
        timeout: int,
        working_dir: str | None,
        env: dict,
        risk_level: RiskLevel,
    ) -> CommandResult:
        """执行命令"""
        start = time.time()

        is_windows = platform.system() == "Windows"
        shell = True if is_windows else False

        if not is_windows:
            parts = shlex.split(command)
        else:
            parts = command

        proc = asyncio.create_subprocess_shell(
            parts if is_windows else command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir or os.getcwd(),
            env={**os.environ, **env} if env else None,
        )

        try:
            stdout, stderr = asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            proc.wait()
            raise

        stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

        duration = (time.time() - start) * 1000
        status = CommandStatus.COMPLETED if proc.returncode == 0 else CommandStatus.FAILED

        self.stats["commands_executed"] = self.stats.get("commands_executed", 0) + 1

        return CommandResult(
            execution_id=execution_id,
            command=command,
            status=status,
            exit_code=proc.returncode,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=duration,
            working_dir=working_dir or os.getcwd(),
            risk_level=risk_level,
        )

    def execute_batch(self, commands: list[dict]) -> list[dict]:
        """批量执行命令"""
        results = []
        for cmd_config in commands:
            try:
                result = self.execute(
                    command=cmd_config["command"],
                    timeout=cmd_config.get("timeout"),
                    working_dir=cmd_config.get("working_dir"),
                    approved=cmd_config.get("approved", False),
                )
                results.append(result)
            except Exception as e:
                results.append({"command": cmd_config.get("command", ""), "status": "error", "error": str(e)})
        return results

    def get_history(self, limit: int = 100, risk_level: str | None = None) -> list[dict]:
        """获取命令历史"""
        history = self._history
        if risk_level:
            history = [h for h in history if h.risk_level == risk_level]
        return [
            {
                "execution_id": h.execution_id,
                "command": h.command,
                "status": h.status,
                "exit_code": h.exit_code,
                "duration_ms": round(h.duration_ms, 2),
                "risk_level": h.risk_level,
                "executed_at": datetime.fromtimestamp(h.executed_at).isoformat(),
            }
            for h in reversed(history[-limit:])
        ]

    def get_system_info(self) -> dict[str, Any]:
        """获取系统信息"""
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "home": os.path.expanduser("~"),
        }
        try:
            import psutil

            info["memory_total_gb"] = round(psutil.virtual_memory().total / 1073741824, 2)
            info["memory_available_gb"] = round(psutil.virtual_memory().available / 1073741824, 2)
            info["disk_total_gb"] = round(psutil.disk_usage("/").total / 1073741824, 2)
            info["disk_free_gb"] = round(psutil.disk_usage("/").free / 1073741824, 2)
        except ImportError:
            pass
            return info

    def assess_command(self, command: str) -> dict[str, Any]:
        """预评估命令风险"""
        risk, rule = self._assess_risk(command)
        return {
            "command": command,
            "risk_level": risk.value,
            "requires_approval": rule.require_approval if rule else False,
            "rule_description": rule.description if rule else "无匹配规则",
            "max_timeout": rule.max_timeout if rule else self._default_timeout,
            "blocked": risk == RiskLevel.BLOCKED,
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict[str, Any]:
        """统一执行入口 — 根据action路由到对应业务方法"""
        params = params or {}
        actions = {
            "status": lambda: {
                "status": "running",
                "commands_executed": len(self._history),
                "active_commands": len(self._active_commands),
                "rules_loaded": len(self._rules),
                "platform": platform.system(),
                "success_rate": round(
                    sum(1 for h in self._history if h.status == "completed") / max(len(self._history), 1), 4
                ),
            },
            "run": lambda: self._execute_command(params.get("command", ""), params.get("timeout", 30)),
            "history": lambda: [
                {"cmd": h.command, "status": h.status, "risk": h.risk_level, "time": h.timestamp}
                for h in self._history[-20:]
            ],
            "rules": lambda: [
                {"pattern": r.pattern, "level": r.risk_level.value, "desc": r.description} for r in self._rules.values()
            ],
            "add_rule": lambda: self._add_rule(
                params.get("pattern", ""), params.get("level", "MEDIUM"), params.get("description", "")
            ),
            "remove_rule": lambda: self._remove_rule(params.get("pattern", "")),
            "clear_history": lambda: self._clear_history(),
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }
        handler = actions.get(action)
        if not handler:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}
        try:
            result = handler()
            if isinstance(result, dict) and "status" not in result:
                return {"status": "success", **result}
            return result if isinstance(result, dict) else {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _execute_command(self, command: str, timeout: int = 30) -> dict[str, Any]:
        if not command:
            return {"status": "error", "message": "No command provided"}
        risk, rule = self._assess_risk(command)
        if risk == RiskLevel.BLOCKED:
            return {
                "status": "blocked",
                "command": command,
                "reason": rule.description if rule else "Blocked by policy",
            }
        history = CommandHistory(command=command, risk_level=risk.value)
        self._history.append(history)
        import asyncio

        def _run():
            try:
                proc = asyncio.create_subprocess_shell(
                    command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = asyncio.wait_for(proc.communicate(), timeout=timeout)
                history.status = "completed" if proc.returncode == 0 else "failed"
                history.output = stdout.decode(errors="ignore")[:2000]
                history.return_code = proc.returncode
            except TimeoutError:
                history.status = "timeout"
            except Exception as e:
                history.status = "error"
                history.output = str(e)[:500]

        task = asyncio.ensure_future(_run())
        self._active_commands[command[:50]] = task
        return {"status": "running", "command": command, "risk": risk.value}

    def _add_rule(self, pattern: str, level: str, description: str) -> dict[str, Any]:
        from fnmatch import fnmatch

        risk = RiskLevel(level.upper()) if level.upper() in [r.value for r in RiskLevel] else RiskLevel.MEDIUM
        self._rules[pattern] = CommandRule(pattern=pattern, risk_level=risk, description=description)
        return {"status": "success", "rules_count": len(self._rules)}

    def _remove_rule(self, pattern: str) -> dict[str, Any]:
        if pattern in self._rules:
            del self._rules[pattern]
            return {"status": "success", "rules_count": len(self._rules)}
        return {"status": "not_found", "pattern": pattern}

    def _clear_history(self) -> dict[str, Any]:
        count = len(self._history)
        self._history.clear()
        return {"status": "success", "cleared": count}

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        total = len(self._history)
        success = sum(1 for h in self._history if h.status == "completed")
        base.update(
            {
                "commands_executed": total,
                "success_rate": round(success / max(total, 1), 4),
                "active_commands": len(self._active_commands),
                "by_risk": self._count_by_risk(),
                "rules_loaded": len(self._rules),
                "platform": platform.system(),
            }
        )
        return base

    def _count_by_risk(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for h in self._history:
            counts[h.risk_level] = counts.get(h.risk_level, 0) + 1
        return counts

    def shutdown(self) -> None:
        for task in self._active_commands.values():
            if not task.done():
                task.cancel()
        audit_logger.log(
            action="module_shutdown", resource="system_command", details=f"关闭，共执行 {len(self._history)} 条命令"
        )

module_class = SystemCommand
