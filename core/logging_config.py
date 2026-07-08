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
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器 — 上市公司级日志标准"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        # 控制台输出（始终保留）
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(JSONFormatter() if use_json else _classic_formatter)
        logger.addHandler(console)
        # 文件输出（自动轮转：每100MB切分，保留7天）
        _log_dir = os.environ.get("EVO_LOG_DIR", "logs")
        try:
            os.makedirs(_log_dir, exist_ok=True)
            _log_file = os.path.join(_log_dir, f"{name.replace('.', '_')}.log")
            file_handler = RotatingFileHandler(
                _log_file, maxBytes=100*1024*1024, backupCount=7, encoding="utf-8"
            )
            file_handler.setFormatter(JSONFormatter() if use_json else _classic_formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass  # 日志文件写入失败不影响程序运行

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
