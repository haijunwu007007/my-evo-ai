"""
AUTO-EVO-AI V0.1 — 日志分析引擎
Grade: A (生产级) | Category: 工具链
职责：日志采集、解析、分析、异常检测、模式识别、报告生成
"""

__module_meta__ = {
        "id": "log-analyzer",
        "name": "Log Analyzer",
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
                "name": "results_2",
                "type": "list[dict]",
                "description": "结果列表"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "logging",
            "monitor",
            "log",
            "adapter"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 日志分析引擎 Grade: A (生产级) | Category: 工具链"
    }

import asyncio
import time
import uuid
import re
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict

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
logger = logging.getLogger("log_analyzer")

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

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class LogFormat(Enum):
    STANDARD = "standard"  # 标准格式: LEVEL message
    APACHE = "apache"  # Apache/Nginx access log
    JSON = "json"  # JSON格式日志
    SYSLOG = "syslog"  # syslog格式
    GCP = "gcp"  # Google Cloud Logging
    CUSTOM = "custom"  # 自定义正则

@dataclass
class LogEntry:
    """日志条目"""

    timestamp: float | None
    level: LogLevel
    message: str
    source: str = ""
    line_number: int = 0
    raw: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

@dataclass
class Anomaly:
    """异常检测结果"""

    anomaly_id: str
    type: str
    severity: str
    description: str
    affected_entries: int = 0
    first_seen: float | None = None
    last_seen: float | None = None
    sample_entries: list[str] = field(default_factory=list)
    confidence: float = 0.0

@dataclass
class LogPattern:
    """日志模式"""

    pattern_id: str
    name: str
    regex: str
    category: str
    severity: LogLevel = LogLevel.WARNING
    description: str = ""

class LogAnalyzer(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """日志分析引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._entries: list[LogEntry] = []
        self._anomalies: list[Anomaly] = []
        self._patterns: list[LogPattern] = []
        self._sources: dict[str, dict] = {}
        self._stats_cache: dict[str, Any] = {}
        self._max_entries = 1000000
        self._retention_hours = 24
        self._log_level_weights = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
            LogLevel.UNKNOWN: 1,
        }

    def initialize(self) -> None:
        self._register_builtin_patterns()
        logger.info("日志分析引擎初始化完成")
        self.record_metrics("unknown.init", 1)
        self.audit("initialized", "Unknown初始化完成")

    def _register_builtin_patterns(self) -> None:
        """注册内置检测模式"""
        patterns = [
            LogPattern(
                "pat_oom",
                "内存溢出",
                r"(OutOfMemory|OOM|killed|memory exhausted)",
                "resource",
                LogLevel.CRITICAL,
                "系统或进程内存耗尽",
            ),
            LogPattern(
                "pat_timeout",
                "超时",
                r"(timeout|timed out|connection timed|deadline exceeded)",
                "network",
                LogLevel.ERROR,
                "操作超时",
            ),
            LogPattern(
                "pat_auth_fail",
                "认证失败",
                r"(authentication failed|unauthorized|401|403|invalid token)",
                "security",
                LogLevel.ERROR,
                "认证或授权失败",
            ),
            LogPattern(
                "pat_sql_error",
                "SQL错误",
                r"(SQL error|sqlalchemy|psycopg|mysql.*error|duplicate key)",
                "database",
                LogLevel.ERROR,
                "数据库错误",
            ),
            LogPattern(
                "pat_circuit_open",
                "熔断器打开",
                r"(circuit.*open|breaker.*tripped|half.*open)",
                "resilience",
                LogLevel.WARNING,
                "熔断器状态变更",
            ),
            LogPattern(
                "pat_rate_limit",
                "限流触发",
                r"(rate limit|too many requests|429|throttl)",
                "traffic",
                LogLevel.WARNING,
                "触发限流",
            ),
            LogPattern(
                "pat_conn_refused",
                "连接拒绝",
                r"(connection refused|ECONNREFUSED|no route to host)",
                "network",
                LogLevel.ERROR,
                "网络连接被拒绝",
            ),
            LogPattern(
                "pat_file_error",
                "文件错误",
                r"(No such file|permission denied|disk full|ENOSPC)",
                "storage",
                LogLevel.ERROR,
                "文件系统错误",
            ),
            LogPattern(
                "pat_dep_crash",
                "依赖崩溃",
                r"(dependency.*down|service.*unavailable|503|502)",
                "availability",
                LogLevel.CRITICAL,
                "下游服务不可用",
            ),
            LogPattern(
                "pat_slow_query",
                "慢查询",
                r"(slow query|query took|execution time.*exceeded)",
                "performance",
                LogLevel.WARNING,
                "数据库慢查询",
            ),
        ]
        self._patterns = patterns

    @trace_operation("ingest_logs")
    def ingest_logs(
        self, content: str, source: str = "inline", format: LogFormat = LogFormat.STANDARD
    ) -> dict[str, Any]:
        """采集日志"""
        try:
            start = time.time()
            entries = self._parse_logs(content, format, source)

            for entry in entries:
                entry.tags = self._match_patterns(entry)
                self._entries.append(entry)

            # 超出限制时清理旧日志
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]

            self._sources[source] = {
                "total_entries": self._sources.get(source, {}).get("total_entries", 0) + len(entries),
                "last_ingest": time.time(),
                "format": format.value,
            }
            self.stats["entries_ingested"] = self.stats.get("entries_ingested", 0) + len(entries)
            self._stats_cache.clear()

            metrics_collector.counter("log_entries_ingested", len(entries))

            return {
                "source": source,
                "entries_parsed": len(entries),
                "total_entries": len(self._entries),
                "duration_ms": round((time.time() - start) * 1000, 2),
            }
        except Exception as e:
            logger.error(f"日志采集失败: {e}")
            self.stats["errors"] += 1
            raise

    def _parse_logs(self, content: str, format: LogFormat, source: str) -> list[LogEntry]:
        """解析日志"""
        entries = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            entry = self._parse_line(line, format, source, i + 1)
            if entry:
                entries.append(entry)
        return entries

    def _parse_line(self, line: str, format: LogFormat, source: str, line_num: int) -> LogEntry | None:
        """解析单行日志"""
        try:
            if format == LogFormat.JSON:
                return self._parse_json_line(line, source, line_num)
            elif format == LogFormat.APACHE:
                return self._parse_apache_line(line, source, line_num)
            elif format == LogFormat.SYSLOG:
                return self._parse_syslog_line(line, source, line_num)
            else:
                return self._parse_standard_line(line, source, line_num)
        except Exception:
            return LogEntry(
                timestamp=time.time(),
                level=LogLevel.UNKNOWN,
                message=line,
                source=source,
                line_number=line_num,
                raw=line,
            )

    def _parse_standard_line(self, line: str, source: str, line_num: int) -> LogEntry:
        """解析标准格式日志"""
        level = LogLevel.UNKNOWN
        timestamp = time.time()
        message = line

        # 匹配时间戳
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})", line)
        if ts_match:
            try:
                ts_str = ts_match.group(1).replace("T", " ")
                timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp()
                message = line[ts_match.end() :].strip()
            except ValueError:
                pass

        # 匹配日志级别
        for lvl in [LogLevel.CRITICAL, LogLevel.ERROR, LogLevel.WARNING, LogLevel.INFO, LogLevel.DEBUG]:
            if lvl.value in line.upper():
                level = lvl
                break

        return LogEntry(
            timestamp=timestamp, level=level, message=message, source=source, line_number=line_num, raw=line
        )

    def _parse_json_line(self, line: str, source: str, line_num: int) -> LogEntry | None:
        """解析JSON格式日志"""
        try:
            data = json.loads(line)
            level = LogLevel.UNKNOWN
            if "level" in data:
                level_str = data["level"].upper()
                for lvl in LogLevel:
                    if lvl.value == level_str:
                        level = lvl
                        break
            ts = data.get("timestamp") or data.get("time") or data.get("@timestamp")
            timestamp = None
            if ts:
                try:
                    if isinstance(ts, (int, float)):
                        timestamp = float(ts)
                    else:
                        timestamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
                except (ValueError, OSError):
                    timestamp = time.time()
            return LogEntry(
                timestamp=timestamp or time.time(),
                level=level,
                message=data.get("message", data.get("msg", "")),
                source=source,
                line_number=line_num,
                raw=line,
                metadata={k: v for k, v in data.items() if k not in ("level", "message", "msg", "timestamp", "time")},
            )
        except json.JSONDecodeError:
            return None

    def _parse_apache_line(self, line: str, source: str, line_num: int) -> LogEntry:
        """解析Apache/Nginx日志"""
        match = re.match(r'(\S+) (\S+) (\S+) \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\d+) "([^"]*)" "([^"]*)"', line)
        if match:
            ip, identity, user, ts_str, method, path, protocol, status, size, referer, ua = match.groups()
            status_int = int(status)
            level = LogLevel.INFO
            if status_int >= 500:
                level = LogLevel.ERROR
            elif status_int >= 400:
                level = LogLevel.WARNING
            return LogEntry(
                timestamp=time.time(),
                level=level,
                message=f"{method} {path} {status}",
                source=source,
                line_number=line_num,
                raw=line,
                metadata={
                    "ip": ip,
                    "method": method,
                    "path": path,
                    "status": status_int,
                    "size": int(size),
                    "user_agent": ua,
                },
            )
        return LogEntry(
            timestamp=time.time(), level=LogLevel.INFO, message=line, source=source, line_number=line_num, raw=line
        )

    def _parse_syslog_line(self, line: str, source: str, line_num: int) -> LogEntry:
        """解析syslog格式"""
        match = re.match(r"(\w+ \d+ \d+:\d+:\d+) (\S+) (\S+?)(?:\[(\d+)\])?: (.*)", line)
        if match:
            ts_str, host, app, pid, message = match.groups()
            level = LogLevel.INFO
            for lvl in [LogLevel.CRITICAL, LogLevel.ERROR, LogLevel.WARNING]:
                if lvl.value.lower() in message.lower():
                    level = lvl
                    break
            return LogEntry(
                timestamp=time.time(),
                level=level,
                message=message,
                source=source,
                line_number=line_num,
                raw=line,
                metadata={"host": host, "app": app, "pid": pid},
            )
        return self._parse_standard_line(line, source, line_num)

    def _match_patterns(self, entry: LogEntry) -> list[str]:
        """匹配异常模式"""
        tags = []
        for pattern in self._patterns:
            if re.search(pattern.regex, entry.message, re.IGNORECASE):
                tags.append(pattern.pattern_id)
        return tags

    @trace_operation("analyze_logs")
    def analyze_logs(
        self, source: str | None = None, time_range: dict | None = None, min_level: LogLevel = LogLevel.WARNING
    ) -> dict[str, Any]:
        """分析日志"""
        entries = self._entries
        if source:
            entries = [e for e in entries if e.source == source]
        if time_range:
            start = time_range.get("start", 0)
            end = time_range.get("end", time.time())
            entries = [e for e in entries if e.timestamp and start <= e.timestamp <= end]

        min_weight = self._log_level_weights.get(min_level, 0)
        filtered = [e for e in entries if self._log_level_weights.get(e.level, 0) >= min_weight]

        # 统计
        level_counts = Counter(e.level.value for e in entries)
        source_counts = Counter(e.source for e in entries)
        hourly_counts = defaultdict(int)
        for e in entries:
            if e.timestamp:
                hour_key = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:00")
                hourly_counts[hour_key] += 1

        # 异常检测
        anomalies = self._detect_anomalies(entries)
        self._anomalies.extend(anomalies)

        # 错误分析
        error_messages = [e.message for e in filtered]
        top_errors = Counter(error_messages).most_common(20)

        # 标签统计
        tag_counts = Counter()
        for e in entries:
            for tag in e.tags:
                tag_counts[tag] += 1

        return {
            "summary": {
                "total_entries": len(entries),
                "filtered_entries": len(filtered),
                "error_rate": round(len(filtered) / max(len(entries), 1), 4),
                "sources": len(source_counts),
                "time_range": f"{min(e.timestamp for e in entries if e.timestamp) or 0:.0f} - {max(e.timestamp for e in entries if e.timestamp) or 0:.0f}"
                if entries
                else "N/A",
            },
            "level_distribution": dict(level_counts),
            "source_distribution": dict(source_counts.most_common(20)),
            "top_errors": [{"message": msg, "count": cnt} for msg, cnt in top_errors],
            "anomalies": len(anomalies),
            "tag_distribution": dict(tag_counts.most_common(10)),
            "hourly_volume": dict(list(hourly_counts.items())[-24:]),
        }

    def _detect_anomalies(self, entries: list[LogEntry]) -> list[Anomaly]:
        """异常检测"""
        anomalies = []

        # 1. 错误突增检测
        if len(entries) > 100:
            error_entries = [e for e in entries if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]
            error_rate = len(error_entries) / len(entries)
            if error_rate > 0.1:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                        type="error_spike",
                        severity="high",
                        description=f"错误率异常: {error_rate:.1%} (阈值: 10%)",
                        affected_entries=len(error_entries),
                        confidence=0.95,
                    )
                )

        # 2. 模式匹配异常
        pattern_hits = defaultdict(list)
        for entry in entries:
            for tag in entry.tags:
                pattern_hits[tag].append(entry)

        for pattern in self._patterns:
            hits = pattern_hits.get(pattern.pattern_id, [])
            if len(hits) > 10:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                        type="pattern_match",
                        severity=pattern.severity.value,
                        description=f"模式 '{pattern.name}' 频繁出现: {len(hits)} 次",
                        affected_entries=len(hits),
                        confidence=0.85,
                        sample_entries=[h.message[:200] for h in hits[:3]],
                    )
                )

        # 3. 重复错误检测
        error_msgs = [e.message for e in entries if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]
        msg_counts = Counter(error_msgs)
        for msg, count in msg_counts.most_common(5):
            if count > 5:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                        type="repeated_error",
                        severity="medium",
                        description=f"重复错误 '{msg[:50]}...' 出现 {count} 次",
                        affected_entries=count,
                        confidence=0.9,
                        sample_entries=[msg[:200]],
                    )
                )

        return anomalies

    @trace_operation("get_anomalies")
    def get_anomalies(self, severity: str | None = None, limit: int = 50) -> list[dict]:
        """获取异常列表"""
        anomalies = self._anomalies
        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]
        return [
            {
                "anomaly_id": a.anomaly_id,
                "type": a.type,
                "severity": a.severity,
                "description": a.description,
                "affected_entries": a.affected_entries,
                "confidence": round(a.confidence, 2),
                "samples": a.sample_entries[:3],
            }
            for a in anomalies[-limit:]
        ]

    @trace_operation("search_logs")
    def search_logs(
        self, query: str, level: LogLevel | None = None, source: str | None = None, limit: int = 100
    ) -> list[dict]:
        """搜索日志"""
        results = self._entries
        if source:
            results = [e for e in results if e.source == source]
        if level:
            results = [e for e in results if e.level == level]
        if query:
            results = [e for e in results if query.lower() in e.message.lower() or query.lower() in e.raw.lower()]

        return [
            {
                "source": e.source,
                "level": e.level.value,
                "message": e.message[:500],
                "tags": e.tags,
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat() if e.timestamp else None,
                "line": e.line_number,
            }
            for e in results[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        """获取日志统计"""
        if not self._entries:
            return {"total_entries": 0}

        total = len(self._entries)
        level_counts = Counter(e.level.value for e in self._entries)
        error_entries = [e for e in self._entries if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]
        tagged = sum(1 for e in self._entries if e.tags)

        return {
            "total_entries": total,
            "level_distribution": dict(level_counts),
            "error_rate": round(len(error_entries) / max(total, 1), 4),
            "tagged_entries": tagged,
            "sources": len(self._sources),
            "patterns_loaded": len(self._patterns),
            "anomalies_detected": len(self._anomalies),
        }

    def add_pattern(
        self, name: str, regex: str, category: str, severity: LogLevel = LogLevel.WARNING, description: str = ""
    ) -> dict[str, Any]:
        """添加自定义检测模式"""
        pattern = LogPattern(
            pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
            name=name,
            regex=regex,
            category=category,
            severity=severity,
            description=description,
        )
        self._patterns.append(pattern)
        return {"pattern_id": pattern.pattern_id, "name": name}

    def clear_logs(self, source: str | None = None) -> dict[str, int]:
        """清理日志"""
        before = len(self._entries)
        if source:
            self._entries = [e for e in self._entries if e.source != source]
        else:
            self._entries.clear()
            self._anomalies.clear()
        removed = before - len(self._entries)
        self._stats_cache.clear()
        return {"removed": removed, "remaining": len(self._entries)}

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        trace_id = f"log_analyzer-execute-{int(time.time() * 1000)}"
        params = params or {}
        actions = {
            "ingest_logs": self.ingest_logs,
            "analyze_logs": self.analyze_logs,
            "get_anomalies": self.get_anomalies,
            "search_logs": self.search_logs,
            "get_stats": self.get_stats,
            "add_pattern": self.add_pattern,
            "clear_logs": self.clear_logs,
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

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "entries_stored": len(self._entries),
                "sources_active": len(self._sources),
                "patterns_loaded": len(self._patterns),
                "anomalies_active": len(self._anomalies),
                "max_entries": self._max_entries,
                "utilization": round(len(self._entries) / self._max_entries, 4),
            }
        )
        return base

    def shutdown(self) -> None:
        self._entries.clear()
        self._anomalies.clear()
        audit_logger.log(action="module_shutdown", resource="log_analyzer", details="关闭，日志数据已清理")

module_class = LogAnalyzer
