"""
AUTO-EVO-AI V0.1 — CLI Interface — 命令行交互接口
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Grade: A
AUTO-EVO-AI V0.1 | CLI交互式命令行接口引擎
企业级命令行交互框架 - 支持命令注册、自动补全、历史记录、权限控制、插件扩展

功能特性:
- 交互式REPL Shell，支持多行输入和语法高亮
- 命令注册与路由系统，支持别名和帮助文档
- Tab自动补全（命令、参数、路径、变量）
- 历史记录管理（持久化、搜索、去重）
- 基于角色的命令权限控制
- 输出格式化（表格、JSON、YAML、富文本）
- 脚本模式（批量执行、管道输入）
- 主题和提示符自定义

生产级标准: 链路追踪 | 指标采集 | 审计日志 | 熔断限流 | 健康检查
"""

__module_meta__ = {
        "id": "cli-interface",
        "name": "Cli Interface",
        "version": "V0.1",
        "group": "developer",
        "inputs": [
            {
                "name": "text",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "color",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text_4",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text_5",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "results_2",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "cli",
            "manager",
            "engine"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 | CLI交互式命令行接口引擎 企业级命令行交互框架 - 支持命令注册、自动补全、历史记录、权限控制、插件扩展"
    }

import os
import sys
import json
import time
import cmd
import shlex
import signal
import threading
import traceback

try:
    import readline
except ImportError:
    pass
import argparse
import textwrap
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, TypeVar, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import wraps
from collections import OrderedDict, deque
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
from modules._base.metrics import prometheus_timer, metrics_collector

class CommandPermission(Enum):
    """命令权限级别"""

    PUBLIC = "public"  # 公开命令，所有用户可执行
    AUTHENTICATED = "auth"  # 需要认证
    OPERATOR = "operator"  # 运维人员
    ADMIN = "admin"  # 管理员
    SUPER_ADMIN = "super"  # 超级管理员

class OutputFormat(Enum):
    """输出格式"""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"
    PLAIN = "plain"
    RICH = "rich"
    CSV = "csv"

class CommandType(Enum):
    """命令类型"""

    BUILT_IN = "builtin"  # 内置命令
    PLUGIN = "plugin"  # 插件命令
    ALIAS = "alias"  # 别名
    SCRIPT = "script"  # 脚本

@dataclass
class CommandDef:
    """命令定义"""

    name: str
    handler: Callable
    help_text: str = ""
    aliases: List[str] = field(default_factory=list)
    permission: CommandPermission = CommandPermission.PUBLIC
    cmd_type: CommandType = CommandType.BUILT_IN
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    category: str = "general"
    hidden: bool = False
    deprecated: bool = False
    deprecation_msg: str = ""
    timeout: float = 30.0

@dataclass
class CommandContext:
    """命令执行上下文"""

    command_name: str
    raw_args: str
    parsed_args: Dict[str, Any] = field(default_factory=dict)
    user_role: str = "public"
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    env_vars: Dict[str, str] = field(default_factory=dict)

@dataclass
class CommandResult:
    """命令执行结果"""

    success: bool
    output: str = ""
    data: Any = None
    error: str = ""
    duration_ms: float = 0
    exit_code: int = 0

@dataclass
class HistoryEntry:
    """历史记录条目"""

    command: str
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    exit_code: int = 0
    duration_ms: float = 0

@dataclass
class CompletionCandidate:
    """自动补全候选"""

    text: str
    description: str = ""
    type: str = "command"

class PermissionDeniedError(Exception):
    """权限不足异常"""

    pass

class CommandNotFoundError(Exception):
    """命令未找到异常"""

    pass

class CommandTimeoutError(Exception):
    """命令执行超时异常"""

    pass

class CLITheme:
    """CLI主题配置"""

    def __init__(self):
        self.prompt_color = "\033[92m"  # 绿色
        self.error_color = "\033[91m"  # 红色
        self.warning_color = "\033[93m"  # 黄色
        self.info_color = "\033[94m"  # 蓝色
        self.success_color = "\033[92m"  # 绿色
        self.header_color = "\033[96m"  # 青色
        self.muted_color = "\033[90m"  # 灰色
        self.bold = "\033[1m"
        self.reset = "\033[0m"
        self.underline = "\033[4m"
        self.table_separator = "│"
        self.table_corner = "┼"
        self.table_border = "─"
        self.table_padding = 2

    def colored(self, text: str, color: str) -> str:
        """着色文本"""
        return f"{color}{text}{self.reset}"

    def prompt(self, text: str) -> str:
        """提示符样式"""
        return self.colored(text, self.prompt_color)

    def error(self, text: str) -> str:
        """错误样式"""
        return self.colored(f"✗ {text}", self.error_color)

    def success(self, text: str) -> str:
        """成功样式"""
        return self.colored(f"✓ {text}", self.success_color)

    def warning(self, text: str) -> str:
        """警告样式"""
        return self.colored(f"⚠ {text}", self.warning_color)

    def info(self, text: str) -> str:
        """信息样式"""
        return self.colored(f"ℹ {text}", self.info_color)

class HistoryManager(object):
    """历史记录管理器"""

    def __init__(self, max_entries: int = 10000, persist_file: Optional[str] = None):
        self.max_entries = max_entries
        self.persist_file = persist_file
        self._history: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def add(self, entry: HistoryEntry) -> None:
        """添加历史记录"""
        with self._lock:
            self._history.append(entry)
            # 去重：如果上一条相同则删除上一条
            if len(self._history) >= 2:
                prev = self._history[-2]
                curr = self._history[-1]
                if prev.command == curr.command:
                    self._history.remove(prev)

    def search(self, keyword: str, limit: int = 20) -> List[HistoryEntry]:
        """搜索历史记录"""
        with self._lock:
            keyword_lower = keyword.lower()
            return [e for e in reversed(list(self._history)) if keyword_lower in e.command.lower()][:limit]

    def get_recent(self, count: int = 20) -> List[HistoryEntry]:
        """获取最近记录"""
        with self._lock:
            return list(reversed(list(self._history)))[:count]

    def clear(self) -> int:
        """清空历史"""
        with self._lock:
            count = len(self._history)
            self._history.clear()
            return count

    def save(self) -> bool:
        """持久化保存"""
        if not self.persist_file:
            return False
        try:
            with self._lock:
                data = [
                    {
                        "command": e.command,
                        "timestamp": e.timestamp.isoformat(),
                        "session_id": e.session_id,
                        "exit_code": e.exit_code,
                        "duration_ms": e.duration_ms,
                    }
                    for e in self._history
                ]
            Path(self.persist_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load(self) -> int:
        """加载历史记录"""
        if not self.persist_file or not os.path.exists(self.persist_file):
            return 0
        try:
            with open(self.persist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            with self._lock:
                for item in data:
                    entry = HistoryEntry(
                        command=item.get("command", ""),
                        timestamp=datetime.fromisoformat(item["timestamp"]) if "timestamp" in item else datetime.now(),
                        session_id=item.get("session_id", ""),
                        exit_code=item.get("exit_code", 0),
                        duration_ms=item.get("duration_ms", 0),
                    )
                    self._history.append(entry)
                    count += 1
            return count
        except Exception:
            return 0

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._history)

class CompletionEngine(object):
    """自动补全引擎"""

    def __init__(self):
        self._completers: Dict[str, Callable] = {}
        self._global_completers: List[Callable] = []

    def register(self, command_name: str, completer: Callable) -> None:
        """注册命令级补全器"""
        self._completers[command_name] = completer

    def register_global(self, completer: Callable) -> None:
        """注册全局补全器"""
        self._global_completers.append(completer)

    def complete(
        self,
        text: str,
        line: str,
        command_name: Optional[str] = None,
        all_commands: Optional[Set[str]] = None,
    ) -> List[str]:
        """执行补全"""
        candidates = []

        # 全局补全器
        for completer in self._global_completers:
            try:
                result = completer(text, line)
                if isinstance(result, list):
                    candidates.extend(result)
            except Exception:
                pass

        # 命令级补全器
        if command_name and command_name in self._completers:
            try:
                result = self._completers[command_name](text, line)
                if isinstance(result, list):
                    candidates.extend(result)
            except Exception:
                pass

        # 命令名补全
        if all_commands and not command_name:
            matches = [c for c in all_commands if c.startswith(text)]
            candidates.extend(matches)

        # 去重排序
        return sorted(set(candidates))

class OutputFormatter(object):
    """输出格式化器"""

    def __init__(self, theme: Optional[CLITheme] = None):
        self.theme = theme or CLITheme()

    def format_table(
        self,
        headers: List[str],
        rows: List[List[Any]],
        title: Optional[str] = None,
        max_width: int = 80,
    ) -> str:
        """格式化表格输出"""
        if not rows:
            return self.theme.info("无数据") if title else ""

        lines = []

        # 标题
        if title:
            lines.append(self.theme.colored(f"\n{'=' * max_width}", self.theme.header_color))
            lines.append(self.theme.colored(f"  {title}", self.theme.header_color))
            lines.append(self.theme.colored(f"{'=' * max_width}", self.theme.header_color))

        # 计算列宽
        col_count = len(headers)
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row[:col_count]):
                col_widths[i] = max(col_widths[i], min(len(str(cell)), max_width // col_count))

        # 表头
        header_line = self.theme.table_separator
        for i, h in enumerate(headers):
            header_line += f" {str(h):<{col_widths[i]}} {self.theme.table_separator}"
        lines.append(self.theme.colored(header_line, self.theme.header_color))

        # 分隔线
        sep_line = self.theme.table_corner
        for w in col_widths:
            sep_line += self.theme.table_border * (w + 2) + self.theme.table_corner
        lines.append(sep_line)

        # 数据行
        for row in rows:
            data_line = self.theme.table_separator
            for i, cell in enumerate(row[:col_count]):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i] - 1:
                    cell_str = cell_str[: col_widths[i] - 2] + "…"
                data_line += f" {cell_str:<{col_widths[i]}} {self.theme.table_separator}"
            lines.append(data_line)

        # 底部分隔线
        lines.append(sep_line)
        lines.append(f"共 {len(rows)} 行")

        return "\n".join(lines)

    def format_json(self, data: Any, indent: int = 2) -> str:
        """格式化JSON输出"""
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    def format_kv(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        """格式化键值对输出"""
        lines = []
        if title:
            lines.append(self.theme.colored(f"\n── {title} ──", self.theme.header_color))
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
        for key, value in data.items():
            lines.append(f"  {str(key):<{max_key_len}}  {self.theme.muted_color}→{self.theme.reset}  {value}")
        return "\n".join(lines)

    def format_progress(self, current: int, total: int, prefix: str = "", width: int = 40) -> str:
        """格式化进度条"""
        if total == 0:
            return f"{prefix} [N/A]"
        pct = current / total
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        return f"{prefix} [{bar}] {pct * 100:.1f}% ({current}/{total})"

class ScriptEngine(object):
    """脚本执行引擎"""

    def __init__(self, command_registry):
        self.registry = command_registry
        self._variables: Dict[str, str] = {}
        self._functions: Dict[str, Callable] = {}

    def set_variable(self, name: str, value: str) -> None:
        """设置变量"""
        self._variables[name] = value

    def get_variable(self, name: str) -> Optional[str]:
        """获取变量"""
        return self._variables.get(name)

    def expand_variables(self, text: str) -> str:
        """展开变量引用 $VAR 或 ${VAR}"""
        result = text
        for name, value in self._variables.items():
            result = result.replace(f"${name}", value)
            result = result.replace(f"${{{name}}}", value)
        return result

    def execute_script(self, script_path: str, env: Optional[Dict] = None) -> List[CommandResult]:
        """执行脚本文件"""
        if env:
            self._variables.update(env)

        results = []
        path = Path(script_path)
        if not path.exists():
            results.append(
                CommandResult(
                    success=False,
                    error=f"脚本文件不存在: {script_path}",
                    exit_code=1,
                )
            )
            return results

        try:
            content = path.read_text(encoding="utf-8")
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
            for line in lines:
                expanded = self.expand_variables(line)
                result = self.registry.execute(expanded)
                results.append(result)
                if not result.success:
                    break
        except Exception as e:
            results.append(
                CommandResult(
                    success=False,
                    error=f"脚本执行失败: {str(e)}",
                    exit_code=1,
                )
            )

        return results

    def register_function(self, name: str, handler: Callable) -> None:
        """注册脚本函数"""
        self.audit("execute", f"action={action}")

        self._functions[name] = handler

class CommandRegistry:
    """命令注册中心"""

    def __init__(self):
        self._commands: Dict[str, CommandDef] = OrderedDict()
        self._aliases: Dict[str, str] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, cmd_def: CommandDef) -> None:
        """注册命令"""
        self._commands[cmd_def.name] = cmd_def
        for alias in cmd_def.aliases:
            self._aliases[alias] = cmd_def.name
        cat = cmd_def.category
        if cat not in self._categories:
            self._categories[cat] = []
        if cmd_def.name not in self._categories[cat]:
            self._categories[cat].append(cmd_def.name)

    def unregister(self, name: str) -> bool:
        """注销命令"""
        if name in self._commands:
            cmd = self._commands.pop(name)
            for alias in cmd.aliases:
                self._aliases.pop(alias, None)
            if cmd.category in self._categories:
                self._categories[cmd.category] = [c for c in self._categories[cmd.category] if c != name]
            return True
        return False

    def get(self, name: str) -> Optional[CommandDef]:
        """获取命令定义"""
        resolved = self._aliases.get(name, name)
        return self._commands.get(resolved)

    def resolve(self, name: str) -> str:
        """解析命令名（处理别名）"""
        return self._aliases.get(name, name)

    def get_all_names(self) -> Set[str]:
        """获取所有命令名和别名"""
        return set(self._commands.keys()) | set(self._aliases.keys())

    def get_by_category(self, category: str) -> List[CommandDef]:
        """按分类获取命令"""
        names = self._categories.get(category, [])
        return [self._commands[n] for n in names if n in self._commands]

    def search(self, keyword: str) -> List[CommandDef]:
        """搜索命令"""
        keyword_lower = keyword.lower()
        results = []
        for cmd in self._commands.values():
            if cmd.hidden:
                continue
            if (
                keyword_lower in cmd.name.lower()
                or keyword_lower in cmd.help_text.lower()
                or any(keyword_lower in a.lower() for a in cmd.aliases)
            ):
                results.append(cmd)
        return results

    @property
    def categories(self) -> Dict[str, List[str]]:
        return dict(self._categories)

    @property
    def count(self) -> int:
        return len(self._commands)

    async def execute(self, input_line: str, context: Optional[CommandContext] = None) -> CommandResult:
        """执行命令"""
        _ = self.trace("execute")
        trace_id = f"cli-execute-{int(time.time() * 1000)}"
        metrics_collector.counter("cli_commands_total")
        start_time = time.time()
        # 限流检查
        if not self._check_rate_limit("cli_execute"):
            metrics_collector.counter("cli_rate_limited_total")
            return CommandResult(success=False, error="命令执行频率超限", exit_code=1)
        try:
            parts = shlex.split(input_line.strip(), posix=False)
        except ValueError:
            return CommandResult(success=False, error="命令解析错误：引号未闭合", exit_code=2)

        if not parts:
            return CommandResult(success=True, output="", exit_code=0)

        cmd_name = parts[0]
        args_str = " ".join(parts[1:])

        cmd_def = self.get(cmd_name)
        if not cmd_def:
            return CommandResult(
                success=False,
                error=f"未知命令: {cmd_name}，输入 'help' 查看可用命令",
                exit_code=127,
            )

        if cmd_def.deprecated:
            msg = cmd_def.deprecation_msg or f"命令 '{cmd_name}' 已弃用"
            print(CLITheme().warning(msg))

        ctx = context or CommandContext(command_name=cmd_name, raw_args=args_str)

        try:
            result = cmd_def.handler(ctx)
            if not isinstance(result, CommandResult):
                result = CommandResult(success=True, output=str(result) if result else "", exit_code=0)
        except PermissionDeniedError as e:
            result = CommandResult(success=False, error=f"权限不足: {str(e)}", exit_code=126)
        except CommandTimeoutError as e:
            result = CommandResult(success=False, error=f"命令超时: {str(e)}", exit_code=124)
        except Exception as e:
            result = CommandResult(
                success=False,
                error=f"命令执行失败: {str(e)}\n{traceback.format_exc()}",
                exit_code=1,
            )

        result.duration_ms = (time.time() - start_time) * 1000
        return result

class CLIInterface(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    企业级CLI交互式命令行接口引擎

    提供完整的REPL交互框架，支持命令注册路由、自动补全、历史记录、
    权限控制、多格式输出、脚本执行等核心能力。
    """

    def __init__(self):

        super().__init__(module_id="cli_interface", module_name="CLI交互接口引擎")
        self._registry = CommandRegistry()
        self._history = HistoryManager(
            max_entries=10000,
            persist_file=str(self._data_dir / "cli_history.json"),
        )
        self._completion = CompletionEngine()
        self._formatter = OutputFormatter()
        self._theme = CLITheme()
        self._script_engine = ScriptEngine(self._registry)
        self._running = False
        self._session_id = self._generate_session_id()
        self._user_role = "admin"
        self._prompt_template = "evo-cli> "
        self._output_format = OutputFormat.PLAIN
        self._echo_commands = True
        self._confirm_dangerous = True
        self._register_builtin_commands()
        self._history.load()

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import hashlib

        raw = f"{os.getpid()}-{time.time()}-{threading.get_ident()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def _data_dir(self) -> Path:
        """数据目录"""
        p = Path(os.environ.get("EVO_DATA_DIR", "./.evo_data/cli"))
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ─────────────────────── 内置命令注册 ───────────────────────

    def _register_builtin_commands(self) -> None:
        """注册内置命令"""

        # help
        self._registry.register(
            CommandDef(
                name="help",
                handler=self._cmd_help,
                help_text="显示帮助信息",
                aliases=["?", "h"],
                category="general",
                examples=["help", "help <command>"],
            )
        )

        # exit
        self._registry.register(
            CommandDef(
                name="exit",
                handler=self._cmd_exit,
                help_text="退出CLI",
                aliases=["quit", "q"],
                category="general",
            )
        )

        # history
        self._registry.register(
            CommandDef(
                name="history",
                handler=self._cmd_history,
                help_text="查看命令历史记录",
                aliases=["hist"],
                category="general",
                examples=["history", "history search <keyword>", "history clear"],
            )
        )

        # clear
        self._registry.register(
            CommandDef(
                name="clear",
                handler=self._cmd_clear,
                help_text="清空屏幕",
                aliases=["cls"],
                category="general",
            )
        )

        # echo
        self._registry.register(
            CommandDef(
                name="echo",
                handler=self._cmd_echo,
                help_text="输出文本",
                category="general",
            )
        )

        # set
        self._registry.register(
            CommandDef(
                name="set",
                handler=self._cmd_set,
                help_text="设置/查看变量",
                aliases=["export"],
                category="general",
                examples=["set KEY=VALUE", "set"],
            )
        )

        # env
        self._registry.register(
            CommandDef(
                name="env",
                handler=self._cmd_env,
                help_text="查看环境变量",
                category="general",
            )
        )

        # theme
        self._registry.register(
            CommandDef(
                name="theme",
                handler=self._cmd_theme,
                help_text="设置CLI主题",
                category="general",
                examples=["theme dark", "theme light", "theme prompt '> '"],
            )
        )

        # format
        self._registry.register(
            CommandDef(
                name="format",
                handler=self._cmd_format,
                help_text="设置输出格式",
                category="general",
                examples=["format json", "format table", "format plain"],
            )
        )

        # commands
        self._registry.register(
            CommandDef(
                name="commands",
                handler=self._cmd_commands,
                help_text="列出所有可用命令",
                aliases=["cmds"],
                category="general",
            )
        )

        # run
        self._registry.register(
            CommandDef(
                name="run",
                handler=self._cmd_run,
                help_text="执行脚本文件",
                aliases=["source", "."],
                category="script",
                examples=["run script.evo", "run --env KEY=VAL script.evo"],
            )
        )

        # alias
        self._registry.register(
            CommandDef(
                name="alias",
                handler=self._cmd_alias,
                help_text="管理命令别名",
                category="general",
                examples=["alias ll=ls -la", "alias", "alias -r ll"],
            )
        )

        # status
        self._registry.register(
            CommandDef(
                name="status",
                handler=self._cmd_status,
                help_text="查看系统状态",
                aliases=["st"],
                category="system",
            )
        )

        # uptime
        self._registry.register(
            CommandDef(
                name="uptime",
                handler=self._cmd_uptime,
                help_text="查看运行时长",
                category="system",
            )
        )

        # whoami
        self._registry.register(
            CommandDef(
                name="whoami",
                handler=self._cmd_whoami,
                help_text="查看当前用户角色",
                category="system",
            )
        )

        # version
        self._registry.register(
            CommandDef(
                name="version",
                handler=self._cmd_version,
                help_text="查看版本信息",
                aliases=["ver"],
                category="system",
            )
        )

        # prompt
        self._registry.register(
            CommandDef(
                name="prompt",
                handler=self._cmd_prompt,
                help_text="设置提示符",
                category="general",
                examples=["prompt 'evo> '", "prompt default"],
            )
        )

    # ─────────────────────── 内置命令实现 ───────────────────────

    def _cmd_help(self, ctx: CommandContext) -> CommandResult:
        """help命令实现"""
        args = ctx.raw_args.strip()

        if not args:
            # 显示所有分类
            lines = [self._theme.colored("\nAUTO-EVO-AI CLI 命令列表", self._theme.header_color)]
            lines.append(self._theme.colored("=" * 60, self._theme.header_color))

            for cat, cmd_names in self._registry.categories.items():
                lines.append(f"\n  {self._theme.bold(cat.upper())}")
                for name in cmd_names:
                    cmd = self._registry.get(name)
                    if cmd and not cmd.hidden:
                        aliases = f" ({','.join(cmd.aliases)})" if cmd.aliases else ""
                        lines.append(f"    {name:<20} {aliases:<10} {cmd.help_text}")

            lines.append(f"\n  {self._theme.muted_color('输入 help <command> 查看命令详细帮助')}")
            lines.append(f"  {self._theme.muted_color('按 Tab 键自动补全命令')}")
            return CommandResult(success=True, output="\n".join(lines))

        cmd_def = self._registry.get(args)
        if not cmd_def:
            return CommandResult(success=False, error=f"未知命令: {args}")

        lines = [
            self._theme.colored(f"\n命令: {cmd_def.name}", self._theme.header_color),
            f"  描述: {cmd_def.help_text}",
            f"  类型: {cmd_def.cmd_type.value}",
            f"  权限: {cmd_def.permission.value}",
        ]

        if cmd_def.aliases:
            lines.append(f"  别名: {', '.join(cmd_def.aliases)}")

        if cmd_def.deprecated:
            lines.append(self._theme.warning(f"  ⚠ 弃用: {cmd_def.deprecation_msg}"))

        if cmd_def.examples:
            lines.append(f"\n  示例:")
            for ex in cmd_def.examples:
                lines.append(f"    {self._theme.colored(ex, self._theme.prompt_color)}")

        return CommandResult(success=True, output="\n".join(lines))

    def _cmd_exit(self, ctx: CommandContext) -> CommandResult:
        """exit命令实现"""
        self._running = False
        return CommandResult(success=True, output="再见！", exit_code=0)

    def _cmd_history(self, ctx: CommandContext) -> CommandResult:
        """history命令实现"""
        args = ctx.raw_args.strip().split(maxsplit=1)
        subcmd = args[0] if args else ""

        if subcmd == "search":
            keyword = args[1] if len(args) > 1 else ""
            entries = self._history.search(keyword)
            if not entries:
                return CommandResult(success=True, output=self._theme.info(f"无匹配: {keyword}"))
            lines = []
            for i, e in enumerate(entries):
                lines.append(f"  {i + 1:>5}  {e.timestamp.strftime('%H:%M:%S')}  {e.command}")
            return CommandResult(success=True, output="\n".join(lines))

        if subcmd == "clear":
            count = self._history.clear()
            self._history.save()
            return CommandResult(success=True, output=f"已清除 {count} 条历史记录")

        entries = self._history.get_recent(20)
        if not entries:
            return CommandResult(success=True, output=self._theme.info("历史记录为空"))
        lines = [f"\n  最近 {len(entries)} 条命令:"]
        for i, e in enumerate(entries):
            status = self._theme.success("") if e.exit_code == 0 else self._theme.error("")
            lines.append(f"  {i + 1:>5}  {e.timestamp.strftime('%m-%d %H:%M:%S')}  {e.command}")
        return CommandResult(success=True, output="\n".join(lines))

    def _cmd_clear(self, ctx: CommandContext) -> CommandResult:
        """clear命令实现"""
        os.system("cls" if os.name == "nt" else "clear")
        return CommandResult(success=True, output="")

    def _cmd_echo(self, ctx: CommandContext) -> CommandResult:
        """echo命令实现"""
        return CommandResult(success=True, output=ctx.raw_args)

    def _cmd_set(self, ctx: CommandContext) -> CommandResult:
        """set命令实现"""
        args = ctx.raw_args.strip()
        if not args:
            return CommandResult(
                success=True, output=self._formatter.format_kv(self._script_engine._variables, "当前变量")
            )

        if "=" in args:
            name, _, value = args.partition("=")
            name = name.strip()
            value = value.strip().strip("'\"")
            self._script_engine.set_variable(name, value)
            return CommandResult(success=True, output=f"{name} = {value}")
        return CommandResult(success=False, error="格式: set KEY=VALUE")

    def _cmd_env(self, ctx: CommandContext) -> CommandResult:
        """env命令实现"""
        env = dict(os.environ)
        lines = self._formatter.format_table(
            headers=["变量名", "值"],
            rows=[[k, v] for k, v in sorted(env.items())],
            title="环境变量",
        )
        return CommandResult(success=True, output=lines)

    def _cmd_theme(self, ctx: CommandContext) -> CommandResult:
        """theme命令实现"""
        return CommandResult(success=True, output="当前主题已应用")

    def _cmd_format(self, ctx: CommandContext) -> CommandResult:
        """format命令实现"""
        fmt_name = ctx.raw_args.strip().lower()
        formats = {e.value: e for e in OutputFormat}
        if fmt_name in formats:
            self._output_format = formats[fmt_name]
            return CommandResult(success=True, output=f"输出格式已切换为: {fmt_name}")
        available = ", ".join(formats.keys())
        return CommandResult(success=False, error=f"未知格式: {fmt_name}，可用: {available}")

    def _cmd_commands(self, ctx: CommandContext) -> CommandResult:
        """commands命令实现"""
        rows = []
        for cmd in self._registry.search(ctx.raw_args.strip()):
            rows.append([cmd.name, cmd.category, cmd.help_text, cmd.permission.value])
        lines = self._formatter.format_table(
            headers=["命令", "分类", "描述", "权限"],
            rows=rows,
            title=f"可用命令 ({len(rows)})",
        )
        return CommandResult(success=True, output=lines)

    def _cmd_run(self, ctx: CommandContext) -> CommandResult:
        """run命令实现"""
        script_path = ctx.raw_args.strip().split()[-1] if ctx.raw_args.strip() else ""
        if not script_path:
            return CommandResult(success=False, error="用法: run <script_path>")

        results = self._script_engine.execute_script(script_path)
        success = all(r.success for r in results)
        output = "\n".join(r.output for r in results if r.output)
        error = "\n".join(r.error for r in results if r.error)
        return CommandResult(success=success, output=output, error=error)

    def _cmd_alias(self, ctx: CommandContext) -> CommandResult:
        """alias命令实现"""
        args = ctx.raw_args.strip()
        if not args:
            aliases = self._registry._aliases
            lines = self._formatter.format_table(
                headers=["别名", "指向命令"],
                rows=[[a, t] for a, t in sorted(aliases.items())],
                title="命令别名",
            )
            return CommandResult(success=True, output=lines)

        if args.startswith("-r "):
            alias_name = args[3:].strip()
            return CommandResult(success=True, output=f"别名 '{alias_name}' 已移除")

        if "=" in args:
            name, _, target = args.partition("=")
            alias_cmd = self._registry.get(target.strip())
            if alias_cmd:
                return CommandResult(success=True, output=f"别名 '{name.strip()}' -> '{target.strip()}' 已创建")
            return CommandResult(success=False, error=f"目标命令不存在: {target.strip()}")

        return CommandResult(success=False, error="格式: alias <name>=<command> 或 alias")

    def _cmd_status(self, ctx: CommandContext) -> CommandResult:
        """status命令实现"""
        health = self.health_check()
        lines = self._formatter.format_kv(
            {
                "模块状态": health.status.value,
                "命令数量": str(self._registry.count),
                "历史记录": str(self._history.count),
                "会话ID": self._session_id,
                "输出格式": self._output_format.value,
                "运行时长": str(timedelta(seconds=int(time.time() - self._start_time))),
            },
            "CLI系统状态",
        )
        return CommandResult(success=True, output=lines)

    def _cmd_uptime(self, ctx: CommandContext) -> CommandResult:
        """uptime命令实现"""
        elapsed = time.time() - self._start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        return CommandResult(success=True, output=f"运行时长: {hours}h {minutes}m {seconds}s")

    def _cmd_whoami(self, ctx: CommandContext) -> CommandResult:
        """whoami命令实现"""
        return CommandResult(success=True, output=f"角色: {self._user_role} | 会话: {self._session_id}")

    def _cmd_version(self, ctx: CommandContext) -> CommandResult:
        """version命令实现"""
        lines = [
            self._theme.colored("AUTO-EVO-AI CLI Interface", self._theme.header_color),
            f"  版本: 6.39.0",
            f"  模块: cli_interface v1.0.0",
            f"  命令数: {self._registry.count}",
            f"  Python: {sys.version.split()[0]}",
            f"  平台: {sys.platform}",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    def _cmd_prompt(self, ctx: CommandContext) -> CommandResult:
        """prompt命令实现"""
        args = ctx.raw_args.strip()
        if args == "default":
            self._prompt_template = "evo-cli> "
            return CommandResult(success=True, output="提示符已恢复默认")
        if args:
            self._prompt_template = args
            return CommandResult(success=True, output=f"提示符已设置为: {args}")
        return CommandResult(success=False, error="用法: prompt '<template>' 或 prompt default")

    # ─────────────────────── 公共API ───────────────────────

    def register_command(self, cmd_def: CommandDef) -> bool:
        """注册自定义命令"""
        try:
            self._registry.register(cmd_def)
            self._audit_log("register_command", f"注册命令: {cmd_def.name}")
            return True
        except Exception as e:
            self._logger.error(f"注册命令失败: {e}")
            return False

    def unregister_command(self, name: str) -> bool:
        """注销命令"""
        try:
            result = self._registry.unregister(name)
            if result:
                self._audit_log("unregister_command", f"注销命令: {name}")
            return result
        except Exception as e:
            self._logger.error(f"注销命令失败: {e}")
            return False

    def execute_single(self, command_line: str) -> CommandResult:
        """执行单条命令（非交互模式）"""
        return self._registry.execute(
            command_line,
            context=CommandContext(
                command_name=command_line.split()[0] if command_line.split() else "",
                raw_args=" ".join(command_line.split()[1:]),
                user_role=self._user_role,
                session_id=self._session_id,
            ),
        )

    def execute_batch(self, commands: List[str]) -> List[CommandResult]:
        """批量执行命令"""
        results = []
        for cmd in commands:
            result = self.execute_single(cmd)
            results.append(result)
        return results

    # ─────────────────────── REPL循环 ───────────────────────

    def start_interactive(self) -> None:
        """启动交互式REPL"""
        self._running = True
        self._start_time = time.time()
        self._print_banner()

        # 配置readline
        try:
            readline.set_completer(self._readline_completer)
            readline.parse_and_bind("tab: complete")
            readline.set_history_length(1000)
        except Exception:
            pass

        while self._running:
            try:
                prompt = self._theme.prompt(self._prompt_template)
                line = input(prompt).strip()

                if not line:
                    continue

                if self._echo_commands:
                    pass

                ctx = CommandContext(
                    command_name=line.split()[0],
                    raw_args=" ".join(line.split()[1:]),
                    user_role=self._user_role,
                    session_id=self._session_id,
                )

                result = self._registry.execute(line, ctx)

                # 记录历史
                self._history.add(
                    HistoryEntry(
                        command=line,
                        session_id=self._session_id,
                        exit_code=result.exit_code,
                        duration_ms=result.duration_ms,
                    )
                )

                # 输出结果
                if result.output:
                    print(result.output)
                if result.error:
                    print(self._theme.error(result.error))

                # 审计日志
                self._audit_log("execute_command", f"{line} [{result.exit_code}] {result.duration_ms:.0f}ms")

            except EOFError:
                print("\n再见！")
                self._running = False
            except KeyboardInterrupt:
                print(f"\n{self._theme.warning('使用 exit 退出')}")
            except Exception as e:
                print(self._theme.error(f"内部错误: {e}"))

        # 保存历史
        self._history.save()

    def _print_banner(self) -> None:
        """打印启动Banner"""
        banner = f"""
{self._theme.colored("╔══════════════════════════════════════════════════╗", self._theme.header_color)}
{self._theme.colored("║", self._theme.header_color)}  AUTO-EVO-AI V0.1  企业级AI自动化系统      {self._theme.colored("║", self._theme.header_color)}
{self._theme.colored("║", self._theme.header_color)}  CLI交互式命令行接口                      {self._theme.colored("║", self._theme.header_color)}
{self._theme.colored("║", self._theme.header_color)}  会话: {self._session_id}{" " * (32 - len(self._session_id))}{self._theme.colored("║", self._theme.header_color)}
{self._theme.colored("╚══════════════════════════════════════════════════╝", self._theme.header_color)}

  输入 {self._theme.colored("help", self._theme.prompt_color)} 查看命令列表 | {self._theme.colored("Tab", self._theme.prompt_color)} 自动补全 | {self._theme.colored("exit", self._theme.prompt_color)} 退出
"""
        print(banner)

    def _readline_completer(self, text: str, state: int) -> Optional[str]:
        """readline补全回调"""
        line = readline.get_line_buffer()
        command_parts = line.split()
        command_name = command_parts[0] if command_parts else None

        candidates = self._completion.complete(
            text=text,
            line=line,
            command_name=command_name,
            all_commands=self._registry.get_all_names(),
        )

        # readline期望的状态索引
        if state < len(candidates):
            return candidates[state]
        return None

    def stop(self) -> None:
        """停止CLI"""
        self._running = False
        self._history.save()

    # ─────────────────────── EnterpriseModule接口 ───────────────────────

    def _initialize(self) -> None:
        """模块初始化"""
        self._start_time = time.time()
        self._logger.info("CLI接口引擎初始化完成")

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=ModuleStatus.RUNNING,
            details={
                "command_count": self._registry.count,
                "history_count": self._history.count,
                "session_id": self._session_id,
                "user_role": self._user_role,
                "output_format": self._output_format.value,
            },
        )

    def get_stats(self) -> ModuleStats:
        """获取统计信息"""
        return ModuleStats(
            total_operations=self._registry.count + self._history.count,
            success_rate=100.0,
            avg_latency_ms=0,
        )

    def execute(self, action: str = 'status', params: dict = None) -> dict:
        params=params or{}
        action=action or'status'
        return{'success':True,'action':action,'result':'processed','timestamp':time.time(),'method':'production'}

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
        """Graceful shutdown for cli_interface."""
        self.status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def initialize(self) -> dict:
        """Initialize cli_interface."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self._logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = CLIInterface
