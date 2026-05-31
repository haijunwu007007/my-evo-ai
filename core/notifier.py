"""
AUTO-EVO-AI V0.1 — 通知发送器
上市公司级: 多通道通知，失败吞静默，env配置webhook地址
"""
from __future__ import annotations

import json
from core.logging_config import get_logger
import os
import urllib.request
from typing import Any

logger = get_logger("evo.notifier")

_DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
_DINGTALK_ENABLED = bool(_DINGTALK_WEBHOOK)


def send_dingtalk(title: str, content: str, msgtype: str = "markdown") -> bool:
    """
    发送钉钉群机器人消息。
    依赖环境变量 DINGTALK_WEBHOOK，不配置则静默跳过。
    """
    if not _DINGTALK_ENABLED:
        logger.debug("[DingTalk] 未配置 DINGTALK_WEBHOOK，跳过通知")
        return False
    try:
        payload = {
            "msgtype": msgtype,
            msgtype: {"title": title, "text": content},
        }
        req = urllib.request.Request(
            _DINGTALK_WEBHOOK,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read())
        if result.get("errcode") != 0:
            logger.error("[DingTalk] 发送失败: %s", result.get("errmsg", ""))
            return False
        logger.info("[DingTalk] 通知发送成功: %s", title[:40])
        return True
    except Exception as e:
        logger.error("[DingTalk] 发送异常: %s", str(e)[:100])
        return False


def notify_failure(task_name: str, error: str, module: str = "") -> None:
    """调度任务失败时调用"""
    title = f"⚠️ 调度任务失败: {task_name}"
    content = (
        f"### {title}\n"
        f"- **任务**: {task_name}\n"
        f"- **模块**: {module or '未知'}\n"
        f"- **时间**: 2026-05-24\n"
        f"- **错误**: {error[:200]}\n"
    )
    send_dingtalk(title, content)


def notify_success(task_name: str, summary: str = "", count: int = 0) -> None:
    """调度任务成功时调用"""
    title = f"✅ 调度任务完成: {task_name}"
    content = (
        f"### {title}\n"
        f"- **任务**: {task_name}\n"
        f"- **结果**: {summary[:200]}\n"
        f"- **数量**: {count}\n"
    )
    send_dingtalk(title, content)
