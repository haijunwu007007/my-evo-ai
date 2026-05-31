"""
AUTO-EVO-AI V0.1 — 日志采集模块（真实业务逻辑）
Grade: A (生产级) | Category: 监控运维
职责：采集、解析、存储、搜索系统日志和应用日志，支持多源采集和实时过滤
"""

__module_meta__ = {
        "id": "log-collector",
        "name": "Log Collector",
        "version": "V0.1",
        "group": "logging",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "regex",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "field_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "extractor_fn",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "line",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "pattern_name",
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
            "logging",
            "monitor",
            "log",
            "engine"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — 日志采集模块（真实业务逻辑） Grade: A (生产级) | Category: 监控运维"
    }

import os
import re
import json
import time
import gzip
import asyncio
import logging
import threading
import fnmatch
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path

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
logger = logging.getLogger("log_collector")

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    """日志条目"""

    timestamp: str
    level: str
    source: str
    message: str
    raw: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    log_file: str = ""

@dataclass
class LogSource:
    """日志源配置"""

    source_id: str
    name: str
    path: str
    pattern: str = "*.log"
    enabled: bool = True
    encoding: str = "utf-8"
    max_lines_per_scan: int = 1000
    last_position: int = 0
    last_scan: float = 0.0
    lines_collected: int = 0
    errors: int = 0

@dataclass
class LogFilter:
    """日志过滤规则"""

    filter_id: str
    name: str
    level: Optional[str] = None
    source: Optional[str] = None
    keyword: Optional[str] = None
    regex: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None

class LogParserEngine(object):
    """日志解析引擎 - 支持多格式日志解析、字段提取和结构化输出"""

    def __init__(self):
        self._patterns: Dict[str, str] = {}
        self._parsed_count: int = 0
        self._field_extractors: Dict[str, callable] = {}

    def register_pattern(self, name: str, regex: str) -> None:
        """注册日志解析模式"""
        self._patterns[name] = regex

    def register_extractor(self, field_name: str, extractor_fn: callable) -> None:
        """注册字段提取器"""
        self._field_extractors[field_name] = extractor_fn

    def parse_line(self, line: str, pattern_name: str = "default") -> Optional[Dict]:
        """解析单行日志"""
        self._parsed_count += 1
        pattern = self._patterns.get(pattern_name, r"(\S+)\s+(\S+)\s+(\S+)\s+(.+)")
        import re

        m = re.match(pattern, line)
        if not m:
            return None
        groups = m.groups()
        result = {"raw": line, "groups": groups}
        for field_name, extractor in self._field_extractors.items():
            try:
                result[field_name] = extractor(line)
            except Exception:
                pass
        return result

    def parse_batch(self, lines: List[str], pattern_name: str = "default") -> List[Dict]:
        """批量解析日志行"""
        return [r for r in (self.parse_line(l, pattern_name) for l in lines) if r]

    def extract_timestamp(self, line: str) -> Optional[str]:
        """从日志行提取时间戳"""
        import re

        patterns = [
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
            r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})",
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})",
        ]
        for pat in patterns:
            m = re.search(pat, line)
            if m:
                return m.group(1)
        return None

    def extract_log_level(self, line: str) -> str:
        """从日志行提取日志级别"""
        import re

        m = re.search(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b", line, re.I)
        return m.group(1).upper() if m else "UNKNOWN"

    def categorize(self, parsed_lines: List[Dict]) -> Dict[str, int]:
        """按级别分类统计"""
        from collections import Counter

        levels = [self.extract_log_level(p.get("raw", "")) for p in parsed_lines]
        return dict(Counter(levels))

    def stats(self) -> Dict:
        return {
            "patterns": len(self._patterns),
            "extractors": len(self._field_extractors),
            "parsed": self._parsed_count,
        }

class LogCollectorModule(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """日志采集模块 - 多源采集、解析、存储、搜索"""

    # 常见日志格式正则
    LOG_PATTERNS = [
        # ISO timestamp: 2024-01-01T12:00:00 [INFO] message
        re.compile(
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s*[\[(](DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)[\])]\s*(.*)",
            re.IGNORECASE,
        ),
        # Syslog: Jan 01 12:00:00 hostname service[pid]: message
        re.compile(r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+(\S+?)(?:\[\d+\])?:\s*(.*)"),
        # Python: 2024-01-01 12:00:00 - module - INFO - message
        re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*[-|]\s*\S+\s*[-|]\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*[-|]\s*(.*)",
            re.IGNORECASE,
        ),
        # Generic: [timestamp] LEVEL message
        re.compile(
            r"\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]?\s*(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s*:?\s*(.*)",
            re.IGNORECASE,
        ),
    ]

    def __init__(self):

        super().__init__()
        self._sources: Dict[str, LogSource] = {}
        self._filters: Dict[str, LogFilter] = {}
        self._log_store: deque = deque(maxlen=50000)  # 内存存储最近5万条
        self._stats = {
            "total_collected": 0,
            "total_parsed": 0,
            "total_errors": 0,
            "scan_count": 0,
            "last_scan_time": None,
        }
        self._collect_thread: Optional[threading.Thread] = None
        self._collecting = False
        self._collect_interval = 10
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """初始化日志采集"""
        try:
            self._add_default_sources()
            self._collecting = True
            self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True, name="log-collector")
            self._collect_thread.start()
            self.record_metric("log_collector_initialized", 1)
            logger.info("日志采集模块初始化完成，源: %d", len(self._sources))
            return True
        except Exception as e:
            logger.error("日志采集初始化失败: %s", e)
            return False

    def _add_default_sources(self):
        """添加默认日志源"""
        # 系统日志（Windows事件日志不可直接读文件，用应用目录代替）
        app_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(app_dir)
        defaults = [
            LogSource("app_server", "API Server日志", project_dir, "server_*.log"),
            LogSource("app_error", "错误日志", project_dir, "*err*.log"),
        ]
        # Linux系统日志
        if os.path.exists("/var/log"):
            defaults.extend(
                [
                    LogSource("syslog", "系统日志", "/var/log", "syslog*"),
                    LogSource("auth", "认证日志", "/var/log", "auth.log*"),
                ]
            )
        for src in defaults:
            if os.path.exists(src.path):
                self._sources[src.source_id] = src

    def _collect_loop(self):
        """后台采集循环"""
        while self._collecting:
            try:
                self._scan_all_sources()
            except Exception as e:
                logger.debug("日志采集异常: %s", e)
            time.sleep(self._collect_interval)

    def _scan_all_sources(self):
        """扫描所有日志源"""
        for src in self._sources.values():
            if not src.enabled:
                continue
            try:
                self._scan_source(src)
            except Exception as e:
                src.errors += 1
                self._stats["total_errors"] += 1
                logger.debug("扫描源 %s 失败: %s", src.name, e)

    def _scan_source(self, src: LogSource):
        """扫描单个日志源"""
        path = Path(src.path)
        if not path.exists():
            return

        files = list(path.glob(src.pattern)) if src.pattern else [path]
        new_entries = []

        for f in files:
            if not f.is_file():
                continue
            try:
                size = f.stat().st_size
                if size <= src.last_position:
                    continue

                with open(f, "r", encoding=src.encoding, errors="replace") as fh:
                    # 如果文件变小了（被轮转），从头读
                    if size < src.last_position:
                        fh.seek(0)
                    else:
                        fh.seek(src.last_position)

                    lines = fh.readlines(src.max_lines_per_scan)
                    if lines:
                        src.last_position = fh.tell()

                    for line in lines:
                        line = line.rstrip("\n\r")
                        if not line.strip():
                            continue
                        entry = self._parse_line(line, src.source_id, f.name)
                        if entry:
                            new_entries.append(entry)
                            src.lines_collected += 1
            except (PermissionError, OSError) as e:
                src.errors += 1

        if new_entries:
            with self._lock:
                self._log_store.extend(new_entries)
                self._stats["total_collected"] += len(new_entries)
                self._stats["total_parsed"] += len(new_entries)
                self._stats["scan_count"] += 1
                self._stats["last_scan_time"] = datetime.now().isoformat()

        src.last_scan = time.time()

    def _parse_line(self, line: str, source: str, filename: str = "") -> Optional[LogEntry]:
        """解析单行日志"""
        for pattern in self.LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                timestamp = groups[0] if len(groups) > 0 else datetime.now().isoformat()
                level = groups[1] if len(groups) > 1 else "INFO"
                message = groups[2] if len(groups) > 2 else line
                # 标准化level
                level = level.upper()
                if level in ("WARN",):
                    level = "WARNING"
                elif level in ("FATAL",):
                    level = "CRITICAL"
                return LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=message.strip(),
                    raw=line,
                    log_file=filename,
                )
        # 无法解析的行
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            source=source,
            message=line,
            raw=line,
            log_file=filename,
        )

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        collecting = self._collect_thread and self._collect_thread.is_alive()
        with self._lock:
            store_size = len(self._log_store)
        return {
            "status": "healthy" if collecting else "degraded",
            "module_id": "log_collector",
            "sources": len(self._sources),
            "store_size": store_size,
            "collecting": collecting,
            "stats": dict(self._stats),
        }

    async def shutdown(self) -> bool:
        """关闭"""
        self._collecting = False
        if self._collect_thread:
            self._collect_thread.join(timeout=5)
        return True

    # ========== 业务方法 ==========

    def search(self, params: dict = None) -> dict:
        """搜索日志"""
        p = params or {}
        keyword = p.get("keyword", "")
        level = p.get("level", "")
        source = p.get("source", "")
        limit = min(p.get("limit", 50), 500)
        offset = p.get("offset", 0)

        with self._lock:
            entries = list(self._log_store)

        # 过滤
        filtered = entries
        if keyword:
            kw_lower = keyword.lower()
            filtered = [e for e in filtered if kw_lower in e.message.lower() or kw_lower in e.raw.lower()]
        if level:
            filtered = [e for e in filtered if e.level.upper() == level.upper()]
        if source:
            filtered = [e for e in filtered if source.lower() in e.source.lower()]

        total = len(filtered)
        results = filtered[offset : offset + limit]

        return {
            "success": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": [
                {
                    "timestamp": e.timestamp,
                    "level": e.level,
                    "source": e.source,
                    "message": e.message[:200],
                    "file": e.log_file,
                }
                for e in results
            ],
        }

    def get_stats(self, params: dict = None) -> dict:
        """获取采集统计"""
        with self._lock:
            sources_info = [
                {
                    "source_id": s.source_id,
                    "name": s.name,
                    "path": s.path,
                    "enabled": s.enabled,
                    "lines_collected": s.lines_collected,
                    "errors": s.errors,
                    "last_scan": datetime.fromtimestamp(s.last_scan).isoformat() if s.last_scan else "never",
                }
                for s in self._sources.values()
            ]

        # Level distribution
        level_dist = {}
        with self._lock:
            for entry in self._log_store:
                level_dist[entry.level] = level_dist.get(entry.level, 0) + 1

        return {
            "success": True,
            "stats": dict(self._stats),
            "sources": sources_info,
            "level_distribution": level_dist,
            "store_size": len(self._log_store),
        }

    def add_source(self, params: dict = None) -> dict:
        """添加日志源"""
        if not params:
            return {"success": False, "error": "params required"}
        src = LogSource(
            source_id=params.get("source_id", f"custom_{int(time.time())}"),
            name=params.get("name", ""),
            path=params.get("path", ""),
            pattern=params.get("pattern", "*.log"),
        )
        if not os.path.exists(src.path):
            return {"success": False, "error": f"path not found: {src.path}"}
        self._sources[src.source_id] = src
        return {"success": True, "source_id": src.source_id}

    def remove_source(self, params: dict = None) -> dict:
        """移除日志源"""
        if not params or "source_id" not in params:
            return {"success": False, "error": "source_id required"}
        return {"success": self._sources.pop(params["source_id"], None) is not None}

    def list_sources(self, params: dict = None) -> dict:
        """列出日志源"""
        return {
            "success": True,
            "sources": [
                {"source_id": s.source_id, "name": s.name, "path": s.path, "enabled": s.enabled}
                for s in self._sources.values()
            ],
        }

    def tail(self, params: dict = None) -> dict:
        """获取最新N条日志"""
        n = min((params or {}).get("n", 20), 200)
        with self._lock:
            entries = list(self._log_store)
        tail = entries[-n:] if len(entries) > n else entries
        return {
            "success": True,
            "count": len(tail),
            "entries": [
                {"timestamp": e.timestamp, "level": e.level, "source": e.source, "message": e.message[:200]}
                for e in tail
            ],
        }

    def get_errors(self, params: dict = None) -> dict:
        """获取错误日志"""
        limit = min((params or {}).get("limit", 50), 500)
        with self._lock:
            errors = [e for e in self._log_store if e.level in ("ERROR", "CRITICAL")]
        return {
            "success": True,
            "total": len(errors),
            "entries": [
                {"timestamp": e.timestamp, "level": e.level, "source": e.source, "message": e.message[:300]}
                for e in errors[-limit:]
            ],
        }

    def analyze(self, params: dict = None) -> dict:
        """日志分析：错误模式、频率统计"""
        with self._lock:
            entries = list(self._log_store)

        if not entries:
            return {"success": True, "message": "no logs collected yet"}

        # Level distribution
        levels = {}
        for e in entries:
            levels[e.level] = levels.get(e.level, 0) + 1

        # Source distribution
        sources = {}
        for e in entries:
            sources[e.source] = sources.get(e.source, 0) + 1

        # Error pattern extraction (simple keyword grouping)
        error_msgs = [e.message for e in entries if e.level in ("ERROR", "CRITICAL")]
        error_patterns = {}
        for msg in error_msgs:
            # 取前50字符作为模式key
            key = msg[:50].strip()
            error_patterns[key] = error_patterns.get(key, 0) + 1

        # Top error patterns
        top_errors = sorted(error_patterns.items(), key=lambda x: -x[1])[:10]

        return {
            "success": True,
            "total_entries": len(entries),
            "level_distribution": levels,
            "source_distribution": sources,
            "error_count": len(error_msgs),
            "top_error_patterns": [{"pattern": p, "count": c} for p, c in top_errors],
            "error_rate": round(len(error_msgs) / max(len(entries), 1) * 100, 2),
        }

    def detect_log_anomalies(self, window_seconds: int = 300) -> Dict[str, Any]:
        """检测日志异常：错误突增、新错误模式、沉默告警"""
        with self._lock:
            entries = list(self._log_store)
        if not entries:
            return {"anomalies": [], "status": "no_data"}
        now = time.time()
        recent = [e for e in entries if (now - e.timestamp) < window_seconds]
        baseline = [e for e in entries if (now - e.timestamp) >= window_seconds]
        recent_errors = sum(1 for e in recent if e.level in ("ERROR", "CRITICAL"))
        baseline_error_rate = sum(1 for e in baseline if e.level in ("ERROR", "CRITICAL")) / max(len(baseline), 1)
        recent_error_rate = recent_errors / max(len(recent), 1)
        anomalies = []
        if len(recent) > 10 and recent_error_rate > baseline_error_rate * 3:
            anomalies.append(
                {
                    "type": "error_spike",
                    "severity": "high",
                    "baseline_rate": round(baseline_error_rate, 4),
                    "current_rate": round(recent_error_rate, 4),
                    "multiplier": round(recent_error_rate / max(baseline_error_rate, 0.001), 1),
                }
            )
        recent_patterns = set(e.message[:50] for e in recent if e.level in ("ERROR", "CRITICAL"))
        baseline_patterns = set(e.message[:50] for e in baseline if e.level in ("ERROR", "CRITICAL"))
        new_patterns = recent_patterns - baseline_patterns
        if new_patterns:
            anomalies.append(
                {"type": "new_error_patterns", "severity": "warning", "new_patterns": list(new_patterns)[:5]}
            )
        return {
            "anomalies": anomalies,
            "window_seconds": window_seconds,
            "recent_entries": len(recent),
            "anomaly_count": len(anomalies),
        }

    # ========== Execute ==========

    async def execute(self, action: str, params: dict = None) -> dict:
        """执行操作"""
        _ = self.trace("execute")
        metrics_collector.counter("log_collector_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        actions = {
            "status": lambda: {"success": True, "status": "healthy", "module": "log_collector"},
            "search": lambda: self.search(params),
            "get_stats": lambda: self.get_stats(params),
            "stats": lambda: self.get_stats(params),
            "add_source": lambda: self.add_source(params),
            "remove_source": lambda: self.remove_source(params),
            "list_sources": lambda: self.list_sources(params),
            "tail": lambda: self.tail(params),
            "get_errors": lambda: self.get_errors(params),
            "errors": lambda: self.get_errors(params),
            "analyze": lambda: self.analyze(params),
        }
        handler = actions.get(action)
        if handler:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    result = result
                return result if isinstance(result, dict) else {"success": True, "result": result}
            except Exception as e:
                logger.error("log_collector execute %s error: %s", action, e)
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

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

module_class = LogCollectorModule
