"""
AUTO-EVO-AI V0.1 — 命令统计管理器
Grade: A (生产级) | Category: 运维工具
职责：命令执行统计、历史记录、频率分析、安全审计、成本计算
"""

__module_meta__ = {
        "id": "command-stats",
        "name": "Command Stats",
        "version": "V0.1",
        "group": "system",
        "inputs": [
            {
                "name": "cmd",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "cmd_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "cmd_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "is_dangerous",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "exit_code",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "duration_ms",
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
            "manager",
            "command"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 命令统计管理器 Grade: A (生产级) | Category: 运维工具"
    }

import os
import time
import uuid
import json
import re
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

# 危险命令模式
DANGEROUS_PATTERNS = [
    (r"rm\s+(-[rfRF]+\s+)*\/", "危险：递归删除根目录"),
    (r"rm\s+(-[rfRF]+\s+)*\*", "危险：递归删除所有文件"),
    (r"dd\s+.*of=/dev/", "危险：直接写入设备"),
    (r"mkfs\.", "危险：格式化文件系统"),
    (r">\s*/dev/sd", "危险：覆盖块设备"),
    (r"chmod\s+777\s+/", "危险：全局开放权限"),
    (r"DROP\s+TABLE", "危险：删除数据库表"),
    (r"DROP\s+DATABASE", "危险：删除数据库"),
    (r"shutdown\s+(-[h]+\s+)?now", "危险：立即关机"),
    (r"reboot\s+(-[f]+\s+)?now", "危险：强制重启"),
    (r":\(\)\{.*\};:", "危险：Fork炸弹"),
    (r"curl.*\|\s*(ba)?sh", "危险：远程执行脚本"),
]

@dataclass
class CommandRecord:
    """命令执行记录"""

    command_id: str = ""
    command: str = ""
    working_dir: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    user: str = "system"
    host: str = "localhost"
    shell: str = "powershell"
    timestamp: float = 0.0
    is_dangerous: bool = False
    danger_reason: str = ""
    risk_level: str = "low"  # low, medium, high, critical
    tags: list[str] = field(default_factory=list)

@dataclass
class CommandStats:
    """命令统计"""

    total_commands: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    dangerous_count: int = 0
    unique_commands: int = 0
    top_commands: list[dict] = field(default_factory=list)
    by_shell: dict[str, int] = field(default_factory=dict)
    by_user: dict[str, int] = field(default_factory=dict)
    by_hour: dict[int, int] = field(default_factory=dict)

@dataclass
class CostEstimate:
    """成本估算"""

    command: str
    avg_duration_ms: float
    executions: int
    total_time_min: float
    estimated_cost_usd: float  # 按$0.05/小时计算

class CommandStatsManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """命令统计管理器 - 生产级实现"""

    MODULE_ID = "command_stats"
    MODULE_NAME = "command_stats"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "command_stats",
                "version": "7.0.0",
                "description": "命令执行统计管理，支持历史记录、频率分析、安全审计、成本估算",
            }
        )
        self._records: list[CommandRecord] = []
        self._command_index: dict[str, list[int]] = defaultdict(list)  # cmd_hash -> record indices
        self._alerts: list[dict] = []
        self._initialized = False
        self._max_records = 10000

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

    def _hash_command(self, cmd: str) -> str:
        """标准化并哈希命令（去除参数值）"""
        normalized = re.sub(r"\b\d+\.\d+\.\d+\b", "VER", cmd)
        normalized = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "EMAIL", normalized)
        normalized = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP", normalized)
        normalized = re.sub(r"([\"'])(?:(?=(\\?))\\2.)*?\\1", "ARG", normalized)
        return hashlib.md5(normalized.strip().lower().encode()).hexdigest()[:12]

    def _check_danger(self, cmd: str) -> tuple:
        """检查命令是否危险"""
        cmd_lower = cmd.lower()
        for pattern, reason in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower):
                return True, reason
        if cmd_lower.startswith("sudo") or cmd_lower.startswith("runas"):
            return False, ""  # sudo本身不危险
        return False, ""

    def _assess_risk(self, cmd: str, is_dangerous: bool, exit_code: int, duration_ms: float) -> str:
        """评估风险等级"""
        if is_dangerous:
            return "critical"
        if exit_code != 0 and "error" in cmd.lower() and duration_ms > 10000:
            return "high"
        if cmd.strip().startswith("sudo") or cmd.strip().startswith("runas"):
            return "medium"
        if exit_code != 0:
            return "medium"
        return "low"

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """统一execute入口"""
        self.trace("execute", {"module": "command_stats"})
        self.metrics_collector.counter("command_stats.execute.calls", 1)
        self.audit("execute", {"module": "command_stats"})
        params = params or {}
        try:
            if action == "record":
                cmd = params.get("command", "").strip()
                if not cmd:
                    return {"success": False, "error": "命令不能为空"}
                is_danger, danger_reason = self._check_danger(cmd)
                record = CommandRecord(
                    command_id=f"cmd_{uuid.uuid4().hex[:8]}",
                    command=cmd,
                    working_dir=params.get("working_dir", ""),
                    exit_code=params.get("exit_code", 0),
                    duration_ms=params.get("duration_ms", 0.0),
                    user=params.get("user", "system"),
                    host=params.get("host", "localhost"),
                    shell=params.get("shell", "powershell"),
                    timestamp=params.get("timestamp", time.time()),
                    is_dangerous=is_danger,
                    danger_reason=danger_reason,
                    risk_level=self._assess_risk(
                        cmd, is_danger, params.get("exit_code", 0), params.get("duration_ms", 0.0)
                    ),
                    tags=params.get("tags", []),
                )
                # 存储记录
                if len(self._records) >= self._max_records:
                    removed = self._records.pop(0)
                self._records.append(record)
                self._command_index[self._hash_command(cmd)].append(len(self._records) - 1)

                # 危险命令告警
                if is_danger:
                    self._alerts.append(
                        {
                            "alert_id": f"alert_{uuid.uuid4().hex[:8]}",
                            "type": "dangerous_command",
                            "command": cmd,
                            "reason": danger_reason,
                            "user": record.user,
                            "timestamp": record.timestamp,
                        }
                    )

                return {
                    "success": True,
                    "result": {
                        "command_id": record.command_id,
                        "is_dangerous": is_danger,
                        "risk_level": record.risk_level,
                        "danger_reason": danger_reason,
                    },
                }

            elif action == "batch_record":
                commands = params.get("commands", [])
                results = []
                for cmd_data in commands:
                    r = self.execute("record", cmd_data)
                    results.append(r)
                return {
                    "success": True,
                    "result": {
                        "total": len(results),
                        "recorded": sum(1 for r in results if r.get("success")),
                        "dangerous": sum(1 for r in results if r.get("result", {}).get("is_dangerous")),
                    },
                }

            elif action == "get_stats":
                total = len(self._records)
                if total == 0:
                    return {
                        "success": True,
                        "result": CommandStats().to_dict()
                        if hasattr(CommandStats(), "to_dict")
                        else {
                            "total_commands": 0,
                            "success_count": 0,
                            "error_count": 0,
                            "avg_duration_ms": 0,
                            "dangerous_count": 0,
                            "unique_commands": 0,
                            "top_commands": [],
                            "by_shell": {},
                            "by_user": {},
                            "by_hour": {},
                        },
                    }
                success = sum(1 for r in self._records if r.exit_code == 0)
                error = total - success
                durations = [r.duration_ms for r in self._records]
                cmd_counter = Counter(self._hash_command(r.command) for r in self._records)

                # Top commands (by normalized hash)
                cmd_name_map = {}
                for r in self._records:
                    h = self._hash_command(r.command)
                    if h not in cmd_name_map:
                        cmd_name_map[h] = r.command[:80]
                top = [(cmd_name_map[h], cnt) for h, cnt in cmd_counter.most_common(10)]

                by_shell = Counter(r.shell for r in self._records)
                by_user = Counter(r.user for r in self._records)
                by_hour = Counter(datetime.fromtimestamp(r.timestamp).hour for r in self._records)

                return {
                    "success": True,
                    "result": {
                        "total_commands": total,
                        "success_count": success,
                        "error_count": error,
                        "success_rate": round(success / total * 100, 1),
                        "avg_duration_ms": round(sum(durations) / total, 1),
                        "total_duration_min": round(sum(durations) / 60000, 2),
                        "dangerous_count": sum(1 for r in self._records if r.is_dangerous),
                        "unique_commands": len(cmd_counter),
                        "top_commands": [{"command": c, "count": n} for c, n in top],
                        "by_shell": dict(by_shell),
                        "by_user": dict(by_user),
                        "by_hour": {str(h): c for h, c in sorted(by_hour.items())},
                    },
                }

            elif action == "history":
                limit = params.get("limit", 50)
                user = params.get("user")
                risk = params.get("risk_level")
                records = self._records[-limit:] if limit else self._records
                if user:
                    records = [r for r in records if r.user == user]
                if risk:
                    records = [r for r in records if r.risk_level == risk]

                return {
                    "success": True,
                    "result": [
                        {
                            "command_id": r.command_id,
                            "command": r.command[:200],
                            "exit_code": r.exit_code,
                            "duration_ms": round(r.duration_ms, 1),
                            "user": r.user,
                            "shell": r.shell,
                            "risk_level": r.risk_level,
                            "is_dangerous": r.is_dangerous,
                            "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                        }
                        for r in records
                    ],
                }

            elif action == "search":
                query = params.get("query", "").lower()
                if not query:
                    return {"success": False, "error": "搜索关键词不能为空"}
                limit = params.get("limit", 20)
                matches = [r for r in self._records if query in r.command.lower()][-limit:]
                return {
                    "success": True,
                    "result": {
                        "query": query,
                        "total_matches": len(matches),
                        "results": [
                            {
                                "command_id": r.command_id,
                                "command": r.command[:200],
                                "exit_code": r.exit_code,
                                "user": r.user,
                                "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                            }
                            for r in matches
                        ],
                    },
                }

            elif action == "cost_estimate":
                # 估算命令执行时间成本
                cmd_counter = Counter(self._hash_command(r.command) for r in self._records)
                cmd_data = defaultdict(lambda: {"durations": [], "count": 0, "cmd": ""})
                for r in self._records:
                    h = self._hash_command(r.command)
                    cmd_data[h]["durations"].append(r.duration_ms)
                    cmd_data[h]["count"] += 1
                    if not cmd_data[h]["cmd"]:
                        cmd_data[h]["cmd"] = r.command[:80]

                estimates = []
                hourly_rate = params.get("hourly_rate_usd", 0.05)  # $0.05/hour
                for h, data in sorted(cmd_data.items(), key=lambda x: sum(x[1]["durations"]), reverse=True)[:10]:
                    total_ms = sum(data["durations"])
                    total_min = total_ms / 60000
                    cost = total_min / 60 * hourly_rate
                    estimates.append(
                        {
                            "command": data["cmd"],
                            "executions": data["count"],
                            "avg_duration_ms": round(total_ms / data["count"], 1),
                            "total_time_min": round(total_min, 2),
                            "estimated_cost_usd": round(cost, 6),
                        }
                    )

                return {"success": True, "result": estimates}

            elif action == "get_alerts":
                limit = params.get("limit", 50)
                alerts = self._alerts[-limit:] if limit else self._alerts
                return {"success": True, "result": alerts}

            elif action == "clear":
                self._records.clear()
                self._command_index.clear()
                self._alerts.clear()
                return {"success": True, "result": {"cleared": True}}

            elif action == "health_check":
                return {"success": True, "result": self.health_check()}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[CommandStats] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy" if self._initialized else "stopped",
                "records": len(self._records),
                "unique_commands": len(self._command_index),
                "alerts": len(self._alerts),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info(f"关闭命令统计管理器，记录数: {len(self._records)}")

    def get_slow_commands(self, threshold_ms: float = 1000, limit: int = 20) -> dict[str, Any]:
        """慢命令排行。企业场景：性能优化团队识别耗时的系统命令，
        优化脚本执行效率。
        """
        records = sorted(getattr(self, "_records", []), key=lambda x: -x.get("duration_ms", 0))
        slow = [r for r in records if r.get("duration_ms", 0) > threshold_ms][:limit]
        return {
            "success": True,
            "threshold_ms": threshold_ms,
            "total_slow": len([r for r in records if r.get("duration_ms", 0) > threshold_ms]),
            "returned": len(slow),
            "commands": slow,
        }

    def get_error_commands(self, limit: int = 20) -> dict[str, Any]:
        """错误命令统计。企业场景：运维排查频繁失败的系统命令。"""
        records = getattr(self, "_records", [])
        errors = [r for r in records if r.get("exit_code", 0) != 0]
        # 按命令分组统计
        cmd_errors = {}
        for e in errors:
            cmd = e.get("command", "unknown")
            cmd_errors[cmd] = cmd_errors.get(cmd, 0) + 1
        top_errors = sorted(cmd_errors.items(), key=lambda x: -x[1])[:limit]
        return {
            "success": True,
            "total_errors": len(errors),
            "unique_error_commands": len(cmd_errors),
            "top_commands": [{"command": c, "count": n} for c, n in top_errors],
        }

    def get_command_trend(self, command: str, hours: int = 24) -> dict[str, Any]:
        """命令执行趋势。企业场景：查看某个命令在最近N小时的执行频率和耗时变化，
        检测异常波动。
        """
        records = getattr(self, "_records", [])
        cutoff = time.time() - hours * 3600
        filtered = [r for r in records if r.get("command") == command and r.get("timestamp", 0) > cutoff]
        if not filtered:
            return {"success": True, "command": command, "message": "指定时间段内无执行记录"}
        durations = [r.get("duration_ms", 0) for r in filtered]
        return {
            "success": True,
            "command": command,
            "hours": hours,
            "total_executions": len(filtered),
            "avg_duration_ms": round(sum(durations) / len(durations), 1),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
        }

    def get_command_frequency_ranking(self, hours: int = 24, limit: int = 20) -> dict[str, Any]:
        """命令频次排行。企业场景：运维了解系统最常执行的命令，
        识别可优化的重复操作（如定时任务替代手动执行）。
        """
        records = getattr(self, "_records", [])
        cutoff = time.time() - hours * 3600
        recent = [r for r in records if r.get("timestamp", 0) > cutoff]
        cmd_counts = {}
        for r in recent:
            cmd = r.get("command", "unknown")
            cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
        ranking = sorted(cmd_counts.items(), key=lambda x: -x[1])[:limit]
        return {
            "success": True,
            "hours": hours,
            "total_commands": len(recent),
            "unique_commands": len(cmd_counts),
            "ranking": [{"command": c, "count": n} for c, n in ranking],
        }

    def get_hourly_distribution(self, command: str = "", days: int = 1) -> dict[str, Any]:
        """按小时分布。企业场景：发现命令执行的时间规律，
        识别异常时段的异常命令执行（安全审计）。
        """
        records = getattr(self, "_records", [])
        cutoff = time.time() - days * 86400
        filtered = [r for r in records if r.get("timestamp", 0) > cutoff]
        if command:
            filtered = [r for r in filtered if r.get("command") == command]
        hourly = [0] * 24
        for r in filtered:
            hour = time.strftime("%H", time.localtime(r.get("timestamp", 0)))
            hourly[int(hour)] += 1
        return {
            "success": True,
            "command": command or "all",
            "days": days,
            "total": len(filtered),
            "hourly": hourly,
            "peak_hour": hourly.index(max(hourly)),
            "off_peak_hour": hourly.index(min(hourly)),
        }

    def export_stats_csv(self, hours: int = 24) -> dict[str, Any]:
        """导出统计数据为CSV。企业场景：运维团队导出命令执行统计做周报，
        包含命令名、执行次数、平均耗时、错误率。
        """
        records = getattr(self, "_records", [])
        cutoff = time.time() - hours * 3600
        recent = [r for r in records if r.get("timestamp", 0) > cutoff]
        cmd_stats = {}
        for r in recent:
            cmd = r.get("command", "unknown")
            if cmd not in cmd_stats:
                cmd_stats[cmd] = {"count": 0, "total_ms": 0, "errors": 0}
            cmd_stats[cmd]["count"] += 1
            cmd_stats[cmd]["total_ms"] += r.get("duration_ms", 0)
            if r.get("exit_code", 0) != 0:
                cmd_stats[cmd]["errors"] += 1
        lines = ["command,count,avg_ms,error_rate"]
        for cmd, s in sorted(cmd_stats.items(), key=lambda x: -x[1]["count"]):
            avg = round(s["total_ms"] / max(s["count"], 1), 1)
            err_rate = round(s["errors"] / max(s["count"], 1) * 100, 1)
            lines.append(f"{cmd},{s['count']},{avg},{err_rate}")
        return {"success": True, "hours": hours, "total_commands": len(recent), "csv_content": "\n".join(lines)}

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

module_class = CommandStatsManager
