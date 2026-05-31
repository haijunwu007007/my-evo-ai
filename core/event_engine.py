"""
AUTO-EVO-AI V0.1 — 事件驱动引擎 (Event Engine)
===============================================
上市公司级事件驱动架构:
- 事件总线: 发布/订阅模式, 异步事件分发
- 文件监听: 目录变化实时监测 (创建/修改/删除)
- Webhook接收: GitHub/GitLab/通用Webhook事件接收
- 模块事件: 模块执行成功/失败自动发出事件
- 事件→管线: 事件自动触发管线执行
- 事件规则引擎: 条件过滤 + 转换 + 路由
- 事件日志: 持久化 + 回放 + 审计
"""

from __future__ import annotations

import os
import re
import json
import time
import asyncio
import hashlib
from core.logging_config import get_logger
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import sqlite3

logger = get_logger("evo.events")


# ═══════════════════════════════════════════════════════════
# 事件类型定义
# ═══════════════════════════════════════════════════════════

class EventType(str, Enum):
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH = "system.health"

    # 模块事件
    MODULE_EXECUTED = "module.executed"
    MODULE_SUCCESS = "module.success"
    MODULE_FAILED = "module.failed"
    MODULE_INSTALLED = "module.installed"
    MODULE_REMOVED = "module.removed"

    # 管线事件
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_STEP = "pipeline.step"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"

    # 文件事件
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"

    # Webhook事件
    WEBHOOK_RECEIVED = "webhook.received"
    GITHUB_PUSH = "webhook.github.push"
    GITHUB_PR = "webhook.github.pull_request"
    GITLAB_PUSH = "webhook.gitlab.push"

    # 调度事件
    SCHEDULE_TRIGGERED = "schedule.triggered"
    SCHEDULE_COMPLETED = "schedule.completed"

    # 配置事件
    CONFIG_CHANGED = "config.changed"

    # 自定义
    CUSTOM = "custom"


# ═══════════════════════════════════════════════════════════
# 事件数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class Event:
    """事件对象"""
    id: str = ""
    type: str = "custom"
    source: str = ""                    # 事件来源
    data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""
    priority: int = 5                   # 1(最高) - 10(最低)

    def __post_init__(self) -> Any:
        if not self.id:
            self.id = hashlib.md5(
                f"{self.type}:{self.source}:{time.time()}".encode()
            ).hexdigest()[:16]
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════
# 事件规则
# ═══════════════════════════════════════════════════════════

@dataclass
class EventRule:
    """事件规则: 条件匹配 → 触发动作"""
    id: str = ""
    name: str = ""
    description: str = ""
    enabled: bool = True
    # 匹配条件
    event_type_pattern: str = "*"       # 事件类型通配符, 如 "module.*" 或 "webhook.github.*"
    source_pattern: str = "*"           # 来源通配符
    data_conditions: dict = field(default_factory=dict)  # {"status": "failed", "module": "cache_engine"}
    # 触发动作
    action_type: str = "notify"         # notify / pipeline / module / webhook / log
    action_config: dict = field(default_factory=dict)
    # 统计
    match_count: int = 0
    last_matched_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> Any:
        if not self.id:
            import secrets
            self.id = secrets.token_hex(8)
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def matches(self, event: Event) -> bool:
        """检查事件是否匹配规则"""
        if not self.enabled:
            return False

        # 类型匹配 (支持通配符)
        if self.event_type_pattern != "*":
            if not self._match_pattern(self.event_type_pattern, event.type):
                return False

        # 来源匹配
        if self.source_pattern != "*":
            if not self._match_pattern(self.source_pattern, event.source):
                return False

        # 数据条件匹配
        for key, expected in self.data_conditions.items():
            actual = event.data.get(key)
            if isinstance(expected, str) and expected.startswith("regex:"):
                pattern = expected[6:]
                if not re.search(pattern, str(actual or "")):
                    return False
            elif isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    @staticmethod
    def _match_pattern(pattern: str, value: str) -> bool:
        """通配符匹配: module.* 匹配 module.success"""
        regex = pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.fullmatch(regex, value))


# ═══════════════════════════════════════════════════════════
# 事件持久化
# ═══════════════════════════════════════════════════════════

class EventStore:
    """SQLite事件存储"""

    def __init__(self, data_dir: str = ".evo_data/events") -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "events.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> Any:
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    data TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    timestamp TEXT,
                    priority INTEGER DEFAULT 5
                );
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
                CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);

                CREATE TABLE IF NOT EXISTS event_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    event_type_pattern TEXT DEFAULT '*',
                    source_pattern TEXT DEFAULT '*',
                    data_conditions TEXT DEFAULT '{}',
                    action_type TEXT DEFAULT 'notify',
                    action_config TEXT DEFAULT '{}',
                    match_count INTEGER DEFAULT 0,
                    last_matched_at TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def save_event(self, event: Event) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO events (id, type, source, data, metadata, timestamp, priority)
                VALUES (?,?,?,?,?,?,?)
            """, (event.id, event.type, event.source,
                  json.dumps(event.data, ensure_ascii=False),
                  json.dumps(event.metadata, ensure_ascii=False),
                  event.timestamp, event.priority))
            conn.commit()
        finally:
            conn.close()

    def list_events(self, event_type: Optional[str] = None, source: Optional[str] = None,
                    limit: int = 100, offset: int = 0) -> List[dict]:
        conn = self._get_conn()
        try:
            conditions = []
            params = []
            if event_type:
                conditions.append("type LIKE ?")
                params.append(f"%{event_type}%")
            if source:
                conditions.append("source LIKE ?")
                params.append(f"%{source}%")

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = conn.execute(
                f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset]).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                d['data'] = json.loads(d.get('data') or '{}')
                d['metadata'] = json.loads(d.get('metadata') or '{}')
                result.append(d)
            return result
        finally:
            conn.close()

    def save_rule(self, rule: EventRule) -> EventRule:
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO event_rules
                (id, name, description, enabled, event_type_pattern, source_pattern,
                 data_conditions, action_type, action_config, match_count, last_matched_at,
                 created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (rule.id, rule.name, rule.description, int(rule.enabled),
                  rule.event_type_pattern, rule.source_pattern,
                  json.dumps(rule.data_conditions, ensure_ascii=False),
                  rule.action_type, json.dumps(rule.action_config, ensure_ascii=False),
                  rule.match_count, rule.last_matched_at, rule.created_at, rule.updated_at))
            conn.commit()
        finally:
            conn.close()
        return rule

    def get_rule(self, rule_id: str) -> Optional[EventRule]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM event_rules WHERE id=?", (rule_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d['enabled'] = bool(d['enabled'])
            d['data_conditions'] = json.loads(d.get('data_conditions') or '{}')
            d['action_config'] = json.loads(d.get('action_config') or '{}')
            return EventRule(**{k: v for k, v in d.items() if k in EventRule.__dataclass_fields__})
        finally:
            conn.close()

    def list_rules(self, enabled_only: bool = False) -> List[EventRule]:
        conn = self._get_conn()
        try:
            if enabled_only:
                rows = conn.execute("SELECT * FROM event_rules WHERE enabled=1").fetchall()
            else:
                rows = conn.execute("SELECT * FROM event_rules ORDER BY created_at DESC").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['enabled'] = bool(d['enabled'])
                d['data_conditions'] = json.loads(d.get('data_conditions') or '{}')
                d['action_config'] = json.loads(d.get('action_config') or '{}')
                result.append(EventRule(**{k: v for k, v in d.items() if k in EventRule.__dataclass_fields__}))
            return result
        finally:
            conn.close()

    def delete_rule(self, rule_id: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM event_rules WHERE id=?", (rule_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_rule_match(self, rule_id: str):
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE event_rules SET match_count = match_count + 1,
                last_matched_at = ?, updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), rule_id))
            conn.commit()
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._get_conn()
        try:
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_rules = conn.execute("SELECT COUNT(*) FROM event_rules").fetchone()[0]
            active_rules = conn.execute("SELECT COUNT(*) FROM event_rules WHERE enabled=1").fetchone()[0]
            # 最近1小时事件数
            recent = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-1 hour')"
            ).fetchone()[0]
            # 按类型分组统计
            type_counts = {}
            for row in conn.execute(
                "SELECT type, COUNT(*) as cnt FROM events GROUP BY type ORDER BY cnt DESC LIMIT 10"
            ).fetchall():
                type_counts[row['type']] = row['cnt']
            return {
                "total_events": total_events,
                "total_rules": total_rules,
                "active_rules": active_rules,
                "events_last_hour": recent,
                "top_event_types": type_counts
            }
        finally:
            conn.close()

    def cleanup(self, keep_days: int = 7):
        """清理过期事件"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM events WHERE timestamp < datetime('now', ?)",
                (f'-{keep_days} days',)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════
# 文件监听器
# ═══════════════════════════════════════════════════════════

class FileWatcher:
    """目录文件变化监听 (基于轮询, 跨平台兼容)"""

    def __init__(self, emit_callback: Callable[[Event], None]) -> None:
        self._emit = emit_callback
        self._watches: Dict[str, dict] = {}  # path -> {mtime_map, patterns, recursive}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 2.0  # 秒

    def watch(self, directory: str, patterns: Optional[List[str]] = None,
              recursive: bool = True, event_prefix: str = "file"):
        """添加目录监听"""
        abs_path = str(Path(directory).resolve())
        self._watches[abs_path] = {
            "patterns": patterns or ["*"],
            "recursive": recursive,
            "event_prefix": event_prefix,
            "mtimes": {}  # file_path → last_mtime
        }
        # 初始化快照
        self._snapshot(abs_path)
        logger.info("[FileWatcher] 开始监听: %s", abs_path)

    def unwatch(self, directory: str):
        self._watches.pop(str(Path(directory).resolve()), None)

    def _snapshot(self, abs_path: str) -> Any:
        """记录当前文件快照"""
        watch = self._watches.get(abs_path)
        if not watch:
            return
        watch["mtimes"] = {}
        root = Path(abs_path)
        for pattern in watch["patterns"]:
            for fp in root.rglob(pattern) if watch["recursive"] else root.glob(pattern):
                if fp.is_file():
                    try:
                        watch["mtimes"][str(fp)] = fp.stat().st_mtime
                    except OSError:
                        pass

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[FileWatcher] 已启动, 监听 %d 个目录", len(self._watches))

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _poll_loop(self) -> Any:
        while self._running:
            try:
                self._check_all()
            except Exception as e:
                logger.error("[FileWatcher] 检查异常: %s", e)
            await asyncio.sleep(self._check_interval)

    def _check_all(self) -> Any:
        for abs_path, watch in list(self._watches.items()):
            try:
                self._check_directory(abs_path, watch)
            except Exception as e:
                logger.error("[FileWatcher] 检查 %s 异常: %s", abs_path, e)

    def _check_directory(self, abs_path: str, watch: dict) -> Any:
        root = Path(abs_path)
        if not root.exists():
            return

        current_files = {}
        for pattern in watch["patterns"]:
            for fp in root.rglob(pattern) if watch["recursive"] else root.glob(pattern):
                if fp.is_file():
                    try:
                        mtime = fp.stat().st_mtime
                        fstr = str(fp)
                        current_files[fstr] = mtime

                        if fstr not in watch["mtimes"]:
                            # 新文件
                            self._emit(Event(
                                type=f"{watch['event_prefix']}.created",
                                source="file_watcher",
                                data={"path": fstr, "name": fp.name, "size": fp.stat().st_size},
                                priority=6
                            ))
                        elif mtime > watch["mtimes"][fstr] + 1:
                            # 文件修改
                            self._emit(Event(
                                type=f"{watch['event_prefix']}.modified",
                                source="file_watcher",
                                data={"path": fstr, "name": fp.name, "size": fp.stat().st_size},
                                priority=6
                            ))
                    except OSError:
                        pass

        # 检查删除的文件
        for fstr in watch["mtimes"]:
            if fstr not in current_files:
                self._emit(Event(
                    type=f"{watch['event_prefix']}.deleted",
                    source="file_watcher",
                    data={"path": fstr, "name": Path(fstr).name},
                    priority=6
                ))

        watch["mtimes"] = current_files


# ═══════════════════════════════════════════════════════════
# 事件总线核心
# ═══════════════════════════════════════════════════════════

class EventEngine:
    """
    事件驱动引擎 — 上市公司级事件总线
    """

    def __init__(self, data_dir: str = ".evo_data/events") -> None:
        self._store = EventStore(data_dir)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)  # type → [callbacks]
        self._global_subscribers: List[Callable] = []
        self._rules: List[EventRule] = self._store.list_rules()
        self._file_watcher = FileWatcher(self.emit)
        self._running = False
        self._event_count = 0
        logger.info("[EventEngine] 初始化 | 规则: %d", len(self._rules))

    @property
    def store(self) -> EventStore:
        return self._store

    @property
    def file_watcher(self) -> FileWatcher:
        return self._file_watcher

    # ─── 生命周期 ───

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._file_watcher.start()
        self.emit(Event(type=EventType.SYSTEM_STARTUP, source="event_engine",
                       data={"version": "V0.1"}, priority=2))
        logger.info("[EventEngine] 已启动")

    def stop(self) -> None:
        self._running = False
        self._file_watcher.stop()
        self.emit(Event(type=EventType.SYSTEM_SHUTDOWN, source="event_engine", priority=2))
        logger.info("[EventEngine] 已停止")

    # ─── 发布/订阅 ───

    def emit(self, event: Event) -> str:
        """发布事件 (同步, 线程安全)"""
        self._event_count += 1
        # 持久化
        self._store.save_event(event)

        # 通知匹配的订阅者
        for pattern, callbacks in self._subscribers.items():
            if EventRule._match_pattern(pattern, event.type):
                for cb in callbacks:
                    try:
                        cb(event)
                    except Exception as e:
                        logger.error("[EventEngine] 订阅回调异常: %s", e)

        # 全局订阅者
        for cb in self._global_subscribers:
            try:
                cb(event)
            except Exception:
                pass

        # 规则引擎
        self._process_rules(event)

        return event.id

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件 (支持通配符)"""
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable):
        """订阅所有事件"""
        self._global_subscribers.append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if callback in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(callback)

    # ─── 规则引擎 ───

    def _process_rules(self, event: Event) -> Any:
        for rule in self._rules:
            if rule.matches(event):
                rule.match_count += 1
                rule.last_matched_at = datetime.now().isoformat()
                self._store.update_rule_match(rule.id)
                # 异步执行动作
                asyncio.create_task(self._execute_rule_action(rule, event))

    async def _execute_rule_action(self, rule: EventRule, event: Event) -> Any:
        """执行规则动作"""
        try:
            action = rule.action_type
            config = rule.action_config

            if action == "pipeline":
                # 触发管线
                pipeline_id = config.get("pipeline_id", "")
                if pipeline_id:
                    try:
                        from core.pipeline_engine import get_pipeline_engine
                        engine = get_pipeline_engine()
                        params = {**config.get("params", {}), "_event": event.to_dict()}
                        await engine.execute(pipeline_id, params=params)
                        logger.info("[EventEngine] 规则 %s 触发管线 %s", rule.name, pipeline_id)
                    except Exception as e:
                        logger.error("[EventEngine] 管线触发失败: %s", e)

            elif action == "module":
                # 执行模块
                module_name = config.get("module_name", "")
                if module_name:
                    logger.info("[EventEngine] 规则 %s 触发模块 %s", rule.name, module_name)
                    # 由调度引擎执行
                    try:
                        from core.scheduler_engine import get_scheduler_engine
                        scheduler = get_scheduler_engine()
                        task = ScheduledTask(
                            name=f"event:{rule.name}", target_type="module",
                            target_id=module_name, target_params=config.get("params", {}),
                            schedule_type="once", once_time=datetime.now().isoformat()
                        )
                        await scheduler._execute_task(task)
                    except Exception as e:
                        logger.error("[EventEngine] 模块触发失败: %s", e)

            elif action == "webhook":
                # 转发Webhook
                url = config.get("url", "")
                if url:
                    import aiohttp
                    try:
                        async with aiohttp.ClientSession() as session:
                            await session.post(url, json={
                                "event": event.to_dict(),
                                "rule": rule.name,
                                "timestamp": datetime.now().isoformat()
                            }, timeout=aiohttp.ClientTimeout(total=10))
                    except Exception as e:
                        logger.error("[EventEngine] Webhook转发失败: %s", e)

            elif action == "notify":
                # 发送通知
                try:
                    from core.external_services import get_notification_service
                    svc = get_notification_service()
                    channel = config.get("channel", "webhook")
                    message = config.get("message", f"事件: {event.type} 来源: {event.source}")
                    await svc.send(channel=channel, message=message,
                                  title=config.get("title", "事件通知"))
                except Exception as e:
                    logger.error("[EventEngine] 通知发送失败: %s", e)

        except Exception as e:
            logger.error("[EventEngine] 规则动作执行异常: %s", e)

    # ─── 规则管理 ───

    def add_rule(self, rule: EventRule) -> EventRule:
        rule = self._store.save_rule(rule)
        self._rules.append(rule)
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        if self._store.delete_rule(rule_id):
            self._rules = [r for r in self._rules if r.id != rule_id]
            return True
        return False

    def get_rules(self) -> List[EventRule]:
        self._rules = self._store.list_rules()
        return self._rules

    # ─── Webhook接收 ───

    def handle_webhook(self, payload: dict, source: str = "webhook",
                       headers: Optional[dict] = None) -> Event:
        """处理接收到的Webhook"""
        # GitHub事件识别
        event_type = EventType.WEBHOOK_RECEIVED
        if source == "github" or (headers and "X-GitHub-Event" in headers):
            gh_event = (headers or {}).get("X-GitHub-Event", "")
            if gh_event == "push":
                event_type = EventType.GITHUB_PUSH
            elif gh_event in ("pull_request", "pull_request_review"):
                event_type = EventType.GITHUB_PR

        elif source == "gitlab":
            gl_event = (headers or {}).get("X-Gitlab-Event", "")
            if "Push" in gl_event:
                event_type = EventType.GITLAB_PUSH

        event = Event(
            type=event_type, source=f"webhook.{source}",
            data=payload, metadata={"headers": headers or {}}, priority=4
        )
        self.emit(event)
        return event

    # ─── 统计 ───

    def stats(self) -> dict:
        s = self._store.stats()
        s["total_emitted"] = self._event_count
        s["watches"] = len(self._file_watcher._watches)
        s["subscribers"] = sum(len(cbs) for cbs in self._subscribers.values())
        return s


# ─── 全局单例 ───

_engine: Optional[EventEngine] = None

def get_event_engine() -> EventEngine:
    global _engine
    if _engine is None:
        _engine = EventEngine()
    return _engine
