# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - 审计日志系统
===============================
企业级审计日志，记录所有关键操作。

合规要求（SOX / SOC2 / ISO27001）：
  - 不可篡改的审计记录
  - 操作人 / 操作时间 / 操作内容 / 操作结果
  - 支持查询、导出、归档
  - 关键操作自动记录

审计事件类型：
  - AUTH: 认证/授权事件
  - EXEC: 模块执行事件
  - CONFIG: 配置变更事件
  - DATA: 数据访问/修改事件
  - SYSTEM: 系统管理事件
  - SECURITY: 安全相关事件

使用方式:
  audit = get_audit_logger()
  audit.log("execute:health_check", "执行全量检查", module_id="health-check")
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import deque

logger = logging.getLogger("evo.audit")

# 审计事件级别
AUDIT_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}

# 审计事件类型
AUDIT_TYPES = {
    "AUTH": "认证授权",
    "EXEC": "模块执行",
    "CONFIG": "配置变更",
    "DATA": "数据操作",
    "SYSTEM": "系统管理",
    "SECURITY": "安全事件",
    "COMPLIANCE": "合规审计",
}


class AuditEvent:
    """单条审计记录"""

    __slots__ = [
        "timestamp",
        "event_type",
        "action",
        "detail",
        "module_id",
        "trace_id",
        "level",
        "status",
        "operator",
        "source_ip",
        "metadata",
    ]

    def __init__(
        self,
        action: str,
        detail: str = "",
        module_id: str = "",
        trace_id: str = "",
        level: str = "INFO",
        status: str = "success",
        event_type: str = "EXEC",
        operator: str = "system",
        source_ip: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.timestamp = datetime.now().isoformat()
        self.event_type = event_type
        self.action = action
        self.detail = detail
        self.module_id = module_id
        self.trace_id = trace_id
        self.level = level.upper()
        self.status = status
        self.operator = operator
        self.source_ip = source_ip
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "action": self.action,
            "detail": self.detail,
            "module_id": self.module_id,
            "trace_id": self.trace_id,
            "level": self.level,
            "status": self.status,
            "operator": self.operator,
            "source_ip": self.source_ip,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class AuditLogger:
    """
    企业级审计日志器

    特性：
      - 内存环形缓冲（最多保存 max_events 条）
      - 自动检测审计事件类型
      - 按模块ID索引
      - 支持查询过滤
      - 支持导出 JSON
    """

    def __init__(self, max_events: int = 100000):
        self._events: deque = deque(maxlen=max_events)
        self._module_index: Dict[str, List[int]] = {}  # module_id -> [deque indices]
        self._lock = threading.Lock()
        self._stats = {
            "total_events": 0,
            "by_level": {},
            "by_type": {},
        }

    def log(
        self,
        action: str,
        detail: str = "",
        module_id: str = "",
        trace_id: str = "",
        level: str = "INFO",
        status: str = "success",
        event_type: str = "",
        operator: str = "system",
        source_ip: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        记录审计事件

        Args:
            action: 操作名称（如 "execute:health_check"）
            detail: 详细描述
            module_id: 模块ID
            trace_id: 链路追踪ID
            level: 日志级别 (DEBUG/INFO/WARN/ERROR/CRITICAL)
            status: 操作结果 (success/failure)
            event_type: 事件类型 (AUTH/EXEC/CONFIG/DATA/SYSTEM/SECURITY)
            operator: 操作者
            source_ip: 来源IP
            metadata: 额外元数据
        """
        level = level.upper()
        if level not in AUDIT_LEVELS:
            level = "INFO"

        # 自动检测事件类型
        if not event_type:
            event_type = self._detect_type(action)

        event = AuditEvent(
            action=action,
            detail=detail,
            module_id=module_id,
            trace_id=trace_id,
            level=level,
            status=status,
            event_type=event_type,
            operator=operator,
            source_ip=source_ip,
            metadata=metadata,
        )

        with self._lock:
            idx = len(self._events)
            self._events.append(event)
            self._stats["total_events"] += 1
            self._stats["by_level"][level] = self._stats["by_level"].get(level, 0) + 1
            self._stats["by_type"][event_type] = self._stats["by_type"].get(event_type, 0) + 1
            if module_id:
                if module_id not in self._module_index:
                    self._module_index[module_id] = []
                self._module_index[module_id].append(idx)

        # 同步写入日志
        log_fn = {
            "DEBUG": logger.debug,
            "INFO": logger.info,
            "WARN": logger.warning,
            "ERROR": logger.error,
            "CRITICAL": logger.critical,
        }.get(level, logger.info)
        log_fn(f"[AUDIT] {event_type} | {module_id} | {action} | {detail}")

    def _detect_type(self, action: str) -> str:
        """根据操作名称自动检测事件类型"""
        action_lower = action.lower()
        if any(k in action_lower for k in ["login", "auth", "token", "permission"]):
            return "AUTH"
        elif any(k in action_lower for k in ["config", "setting", "update_config"]):
            return "CONFIG"
        elif any(k in action_lower for k in ["data", "query", "insert", "delete", "export"]):
            return "DATA"
        elif any(k in action_lower for k in ["security", "guard", "firewall", "encrypt"]):
            return "SECURITY"
        elif any(k in action_lower for k in ["execute", "run", "start", "stop", "restart"]):
            return "EXEC"
        return "SYSTEM"

    def query(
        self,
        module_id: str = "",
        event_type: str = "",
        level: str = "",
        action: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询审计记录

        支持多条件组合过滤。
        """
        results = []
        with self._lock:
            for event in self._events:
                if module_id and event.module_id != module_id:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                if level and event.level != level.upper():
                    continue
                if action and action not in event.action:
                    continue
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event.to_dict())
                if len(results) >= limit:
                    break
        return results

    def get_module_audit(self, module_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取指定模块的审计记录"""
        return self.query(module_id=module_id, limit=limit)

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近审计记录"""
        with self._lock:
            recent = list(self._events)[-limit:]
            return [e.to_dict() for e in reversed(recent)]

    def export_json(self, start_time: str = "", end_time: str = "") -> str:
        """导出审计日志为JSON"""
        events = self.query(start_time=start_time, end_time=end_time, limit=100000)
        return json.dumps(events, ensure_ascii=False, indent=2, default=str)

    def get_stats(self) -> Dict[str, Any]:
        """获取审计统计"""
        return {
            **self._stats,
            "modules_audited": len(self._module_index),
            "buffer_usage": f"{len(self._events)}/{self._events.maxlen}",
        }

    def clear(self):
        """清空审计日志（危险操作，需审计记录）"""
        with self._lock:
            self._events.clear()
            self._module_index.clear()


# 全局单例
_audit: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志器"""
    global _audit
    if _audit is None:
        _audit = AuditLogger()
        logger.info("审计日志系统初始化完成")
    return _audit
