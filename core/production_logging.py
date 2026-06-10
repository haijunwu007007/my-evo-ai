"""AUTO-EVO-AI V0.1 — 生产日志配置"""
import logging, logging.handlers, os
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

def setup_production_logging(name="evo.api", level=logging.INFO):
    """生产级日志：按大小轮转 + 保留30天"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 文件输出 — 每天100MB自动轮转，保留30份
    handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "evo.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s"
    ))
    logger.addHandler(console)

    return logger
