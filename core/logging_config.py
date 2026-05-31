"""
AUTO-EVO-AI V0.1 — 结构化日志配置
==================================
支持普通文本和 JSON 两种格式，通过 EVO_LOG_JSON 环境变量切换。

用法:
    from core.logging_config import get_logger
    logger = get_logger("evo.api")
    logger.info("模块加载完成", extra={"modules": 535, "mode": "lazy"})
"""

from __future__ import annotations

import os
import json
import logging
import sys
from datetime import datetime, timezone, UTC
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器 — 上市公司级日志标准"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


_classic_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s"
)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """获取配置好的 logger 实例"""
    logger = logging.getLogger(name)
    use_json = os.environ.get("EVO_LOG_JSON", "false").lower() == "true"

    if not level:
        level = os.environ.get("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter() if use_json else _classic_formatter)
        logger.addHandler(handler)

    return logger


class StructuredLogger:
    """结构化日志包装器，支持 extra_fields 传递"""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, msg: str, **extra):
        self._log(logging.INFO, msg, extra)

    def warning(self, msg: str, **extra):
        self._log(logging.WARNING, msg, extra)

    def error(self, msg: str, **extra):
        self._log(logging.ERROR, msg, extra)

    def debug(self, msg: str, **extra):
        self._log(logging.DEBUG, msg, extra)

    def _log(self, level: int, msg: str, extra: dict[str, Any]):
        record = self._logger.makeRecord(
            self._logger.name, level, "", 0, msg, (), None
        )
        record.extra_fields = extra
        self._logger.handle(record)
