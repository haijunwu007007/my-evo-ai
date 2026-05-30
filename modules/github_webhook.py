"""
AUTO-EVO-AI V0.1 — GitHub Webhook 接收与事件处理模块
======================================================
上市公司生产级实现 - HMAC签名验证 / 事件解析 / 自动通知 / 事件历史

功能:
  1. 接收 GitHub Webhook (push/pull_request/workflow_run/issues/release)
  2. HMAC-SHA256 签名验证
  3. 事件解析与结构化存储
  4. 自动通知 (企微/钉钉/飞书)
  5. 事件历史查询/筛选/统计
  6. 安全审计日志
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# ── 模块元数据 ──
MODULE_ID = "github_webhook"
MODULE_NAME = "GitHub Webhook Handler"
VERSION = "V0.1"
MODULE_LEVEL = "A"
# ── 模块导出 ──

# 事件存储 (进程内，生产环境可替换为 Redis/DB)
_events: List[Dict[str, Any]] = []
_events_lock = False
_MAX_EVENTS = 5000

# 通知配置
_notify_config: Dict[str, Any] = {
    "enabled": True,
    "channels": [],          # [{"type":"wechat_work","webhook_url":"..."}, ...]
    "events": ["push", "workflow_run", "pull_request", "release"],
    "min_priority": 0,       # 0=all, 1=high only
}

logger = logging.getLogger(f"evo.{MODULE_ID}")


# ═══════════════════════════════════════════════════════
# 签名验证
# ═══════════════════════════════════════════════════════

def verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """验证 GitHub HMAC-SHA256 签名"""
    if not secret or not signature_header:
        return False
    # 兼容 sha256=xxx 和 sha1=xxx 格式
    prefix = "sha256="
    sha1_prefix = "sha1="
    if signature_header.startswith(sha1_prefix):
        expected = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
        return hmac.compare_digest(f"{sha1_prefix}{expected}", signature_header)
    if not signature_header.startswith(prefix):
        return False
    sig = signature_header[len(prefix):]
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


# ═══════════════════════════════════════════════════════
# 事件解析
# ═══════════════════════════════════════════════════════

def parse_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 GitHub Webhook 事件为统一格式
    返回: {type, action, repo, ref, sender, title, description, url, timestamp, raw}
    """
    repo = (payload.get("repository") or {}).get("full_name", "unknown")
    sender = (payload.get("sender") or {}).get("login", "unknown")
    sender_url = (payload.get("sender") or {}).get("html_url", "")
    now = datetime.now(timezone.utc).isoformat()

    base = {
        "event_type": event_type,
        "repo": repo,
        "sender": sender,
        "sender_url": sender_url,
        "timestamp": now,
        "raw": payload,
    }

    if event_type == "push":
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
        commits = payload.get("commits", [])
        base.update({
            "action": "push",
            "ref": ref,
            "branch": branch,
            "title": f"[push] {branch} ({len(commits)} commits)",
            "description": f"{sender} pushed {len(commits)} commit(s) to {repo}:{branch}",
            "url": payload.get("compare", ""),
            "commits": [{"id": c["id"][:7], "message": c["message"].split("\n")[0], "author": c["author"]["name"]} for c in commits[:10]],
            "priority": 0,
        })

    elif event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        action = payload.get("action", "opened")
        base.update({
            "action": action,
            "ref": pr.get("head", {}).get("ref", ""),
            "branch": pr.get("head", {}).get("ref", ""),
            "title": f"[PR] #{pr.get('number','?')} {pr.get('title','')} ({action})",
            "description": pr.get("body", "")[:500] if pr.get("body") else "",
            "url": pr.get("html_url", ""),
            "pr_number": pr.get("number"),
            "priority": 1 if action in ("opened", "review_requested") else 0,
        })

    elif event_type == "workflow_run":
        run = payload.get("workflow_run") or {}
        conclusion = run.get("conclusion", "pending")
        status = run.get("status", "unknown")
        base.update({
            "action": conclusion or status,
            "title": f"[CI] {run.get('name','')} - {conclusion or status}",
            "description": f"Workflow '{run.get('name','')}' on {run.get('head_branch','')}: {conclusion or status}",
            "url": run.get("html_url", ""),
            "workflow": run.get("name", ""),
            "branch": run.get("head_branch", ""),
            "priority": 2 if conclusion == "failure" else (1 if conclusion == "success" else 0),
        })

    elif event_type == "issues":
        issue = payload.get("issue") or {}
        action = payload.get("action", "opened")
        base.update({
            "action": action,
            "title": f"[Issue] #{issue.get('number','?')} {issue.get('title','')} ({action})",
            "description": issue.get("body", "")[:500] if issue.get("body") else "",
            "url": issue.get("html_url", ""),
            "issue_number": issue.get("number"),
            "priority": 1 if action in ("opened", "reopened") else 0,
        })

    elif event_type == "release":
        release = payload.get("release") or {}
        action = payload.get("action", "published")
        base.update({
            "action": action,
            "title": f"[Release] {release.get('tag_name','')} ({action})",
            "description": release.get("name", "") or release.get("tag_name", ""),
            "url": release.get("html_url", ""),
            "tag": release.get("tag_name", ""),
            "priority": 1,
        })

    elif event_type == "ping":
        base.update({
            "action": "ping",
            "title": "[Ping] Webhook 已连通",
            "description": f"GitHub Webhook 配置验证成功 - {repo}",
            "url": "",
            "priority": 0,
        })

    else:
        base.update({
            "action": payload.get("action", "unknown"),
            "title": f"[{event_type}] Unknown event",
            "description": f"Unhandled event type: {event_type}",
            "url": "",
            "priority": 0,
        })

    return base


# ═══════════════════════════════════════════════════════
# 事件存储
# ═══════════════════════════════════════════════════════

def store_event(event: Dict[str, Any]) -> str:
    """存储事件，返回事件ID"""
    event_id = hashlib.md5(f"{event['timestamp']}{event['title']}{time.time_ns()}".encode()).hexdigest()[:12]
    event["id"] = event_id
    _events.insert(0, event)
    if len(_events) > _MAX_EVENTS:
        _events.pop()
    return event_id


def list_events(
    event_type: Optional[str] = None,
    repo: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """查询事件历史"""
    filtered = _events
    if event_type:
        filtered = [e for e in filtered if e.get("event_type") == event_type]
    if repo:
        filtered = [e for e in filtered if repo.lower() in e.get("repo", "").lower()]
    return filtered[offset:offset + limit]


def get_event_stats() -> Dict[str, Any]:
    """获取事件统计"""
    total = len(_events)
    by_type: Dict[str, int] = defaultdict(int)
    by_repo: Dict[str, int] = defaultdict(int)
    by_priority: Dict[str, int] = defaultdict(int)
    failures = 0

    for e in _events:
        by_type[e.get("event_type", "unknown")] += 1
        by_repo[e.get("repo", "unknown")] += 1
        p = e.get("priority", 0)
        if p >= 2:
            by_priority["high"] += 1
            failures += 1
        elif p == 1:
            by_priority["medium"] += 1
        else:
            by_priority["low"] += 1

    return {
        "total": total,
        "by_type": dict(by_type),
        "by_repo": dict(by_repo),
        "by_priority": dict(by_priority),
        "recent_failures": failures,
    }


def clear_events(older_than_hours: int = 0) -> int:
    """清理事件历史，返回删除数"""
    global _events
    if older_than_hours <= 0:
        n = len(_events)
        _events.clear()
        return n
    cutoff = time.time() - older_than_hours * 3600
    before = len(_events)
    _events = [e for e in _events if _parse_ts(e.get("timestamp", "")) > cutoff]
    return before - len(_events)


def _parse_ts(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except (ValueError, TypeError):
        return 0


# ═══════════════════════════════════════════════════════
# 通知
# ═══════════════════════════════════════════════════════

async def send_notification(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据事件发送通知到已配置的渠道
    返回发送结果列表
    """
    if not _notify_config.get("enabled"):
        return []
    if event.get("event_type") not in _notify_config.get("events", []):
        return []
    if event.get("priority", 0) < _notify_config.get("min_priority", 0):
        return []

    results = []
    title = event.get("title", "GitHub Event")
    description = event.get("description", "")
    url = event.get("url", "")

    for channel in _notify_config.get("channels", []):
        ctype = channel.get("type", "")
        try:
            if ctype == "wechat_work":
                r = await _send_wechat_work(channel.get("webhook_url", ""), title, description, url)
            elif ctype == "dingtalk":
                r = await _send_dingtalk(channel.get("webhook_url", ""), title, description, channel.get("secret", ""), url)
            elif ctype == "feishu":
                r = await _send_feishu(channel.get("webhook_url", ""), title, description, url)
            else:
                r = {"channel": ctype, "status": "skipped", "reason": "unsupported"}
            results.append(r)
        except Exception as e:
            results.append({"channel": ctype, "status": "error", "error": str(e)[:200]})
            logger.error(f"通知发送失败 [{ctype}]: {e}")

    return results


async def _send_wechat_work(webhook_url: str, title: str, description: str, url: str) -> Dict[str, Any]:
    """发送企业微信消息"""
    if not webhook_url:
        return {"channel": "wechat_work", "status": "skipped", "reason": "no webhook_url"}
    content = f"**{title}**\n{description[:2000]}"
    if url:
        content += f"\n[查看详情]({url})"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json={"msgtype": "markdown", "markdown": {"content": content}})
        return {"channel": "wechat_work", "status": "ok" if resp.is_success else "error", "code": resp.status_code}


async def _send_dingtalk(webhook_url: str, title: str, description: str, secret: str, url: str) -> Dict[str, Any]:
    """发送钉钉消息"""
    if not webhook_url:
        return {"channel": "dingtalk", "status": "skipped", "reason": "no webhook_url"}
    text = f"{title}\n{description[:2000]}"
    if url:
        text += f"\n{url}"

    # 签名
    params = {}
    if secret:
        timestamp = str(round(time.time() * 1000))
        sign_str = f"{timestamp}\n{secret}"
        sign = hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()
        import base64 as _b64
        params["timestamp"] = timestamp
        params["sign"] = _b64.b64encode(sign).decode()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, params=params, json={"msgtype": "text", "text": {"content": text}})
        return {"channel": "dingtalk", "status": "ok" if resp.is_success else "error", "code": resp.status_code}


async def _send_feishu(webhook_url: str, title: str, description: str, url: str) -> Dict[str, Any]:
    """发送飞书消息"""
    if not webhook_url:
        return {"channel": "feishu", "status": "skipped", "reason": "no webhook_url"}
    content = f"**{title}**\n{description[:2000]}"
    if url:
        content += f"\n[查看详情]({url})"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json={"msg_type": "interactive", "card": {"header": {"title": {"tag": "plain_text", "content": title[:100]}}, "elements": [{"tag": "markdown", "content": content}]}})
        return {"channel": "feishu", "status": "ok" if resp.is_success else "error", "code": resp.status_code}


# ═══════════════════════════════════════════════════════
# 配置管理
# ═══════════════════════════════════════════════════════

def get_config() -> Dict[str, Any]:
    """获取当前通知配置"""
    return dict(_notify_config)


def update_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新通知配置"""
    for key in ("enabled", "channels", "events", "min_priority"):
        if key in config:
            _notify_config[key] = config[key]
    logger.info(f"通知配置已更新: channels={len(_notify_config['channels'])} events={_notify_config['events']}")
    return dict(_notify_config)


# ═══════════════════════════════════════════════════════
# 模块入口
# ═══════════════════════════════════════════════════════

async def process_webhook(
    event_type: str,
    payload: Dict[str, Any],
    signature: str = "",
    secret: str = "",
) -> Dict[str, Any]:
    """处理 GitHub Webhook 请求——完整流程: 验证→解析→存储→通知"""
    # 1. 签名验证
    if secret:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        if not verify_signature(raw, signature, secret):
            logger.warning(f"签名验证失败: event={event_type} sig={signature[:20]}")
            return {"success": False, "error": "signature_mismatch", "message": "HMAC 签名验证失败"}

    # 2. 解析事件
    try:
        event = parse_event(event_type, payload)
    except Exception as e:
        logger.error(f"事件解析失败: {e}\n{traceback.format_exc()}")
        return {"success": False, "error": "parse_error", "message": f"事件解析失败: {e}"}

    # 3. 存储
    event_id = store_event(event)
    event["id"] = event_id

    # 4. 发送通知
    try:
        notify_results = await send_notification(event)
    except Exception as e:
        logger.error(f"通知发送异常: {e}")
        notify_results = []

    # 5. 审计日志
    logger.info(f"Webhook 处理完成: {event_type} repo={event.get('repo','')} id={event_id}")

    return {
        "success": True,
        "event_id": event_id,
        "event": event,
        "notifications": notify_results,
    }


# ═══════════════════════════════════════════════════════
# execute 接口 (兼容模块调度器)
# ═══════════════════════════════════════════════════════

async def execute(action: str, **kwargs) -> Any:
    """模块执行入口 — 供调度器调用"""
    if action == "process":
        return await process_webhook(
            event_type=kwargs.get("event_type", "unknown"),
            payload=kwargs.get("payload", {}),
            signature=kwargs.get("signature", ""),
            secret=kwargs.get("secret", ""),
        )
    elif action == "list_events":
        return {"success": True, "events": list_events(
            event_type=kwargs.get("event_type"),
            repo=kwargs.get("repo"),
            limit=kwargs.get("limit", 50),
            offset=kwargs.get("offset", 0),
        )}
    elif action == "stats":
        return {"success": True, "stats": get_event_stats()}
    elif action == "config":
        return {"success": True, "config": get_config()}
    elif action == "update_config":
        return {"success": True, "config": update_config(kwargs.get("config", {}))}
    elif action == "clear_events":
        n = clear_events(older_than_hours=kwargs.get("older_than", 0))
        return {"success": True, "deleted": n}
    elif action == "ping":
        return {"success": True, "message": f"{MODULE_NAME} {VERSION} 运行中", "events_stored": len(_events)}
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# ── 模块自检 ──
def health_check() -> Dict[str, Any]:
    """健康检查"""
    return {
        "module": MODULE_ID,
        "status": "healthy",
        "version": VERSION,
        "events_stored": len(_events),
        "notify_enabled": _notify_config.get("enabled", False),
    }


# ── 兼容性导出 ──
module_class = type("GitHubWebhookModule", (), {
    "MODULE_ID": MODULE_ID,
    "MODULE_NAME": MODULE_NAME,
    "VERSION": VERSION,
    "MODULE_LEVEL": MODULE_LEVEL,
    "execute": execute,
    "health_check": health_check,
})

__all__ = ["execute", "health_check", "process_webhook", "list_events", "get_event_stats", "get_config", "update_config", "module_class"]
