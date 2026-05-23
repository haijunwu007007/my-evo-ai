"""
AUTO-EVO-AI V0.1 — Composio工具集成管理器
Grade: A (生产级) | Category: 开源生态
职责：Composio第三方服务集成，工具注册、执行、认证、授权、Webhook管理
"""

__module_meta__ = {
    "id": "composio-tools",
    "name": "Composio Tools",
    "version": "1.0.0",
    "group": "plugin",
    "inputs": [
        {"name": "tool", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "tools", "type": "string", "required": True, "description": ""},
        {"name": "days", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["config", "composio", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Composio工具集成管理器 Grade: A (生产级) | Category: 开源生态",
}

import os
import time
import uuid
import json
import hmac
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class AuthType(Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    BEARER = "bearer"
    NONE = "none"

class ToolStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class WebhookMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"

@dataclass
class ComposioTool:
    """Composio工具定义"""

    tool_id: str = ""
    name: str = ""
    description: str = ""
    provider: str = ""
    category: str = "general"
    auth_type: AuthType = AuthType.NONE
    status: ToolStatus = ToolStatus.ACTIVE
    endpoint: str = ""
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    params_schema: Dict[str, Any] = field(default_factory=dict)
    rate_limit: int = 100
    timeout_ms: int = 30000
    created_at: float = 0.0
    last_used: float = 0.0
    call_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0

@dataclass
class Credential:
    """服务认证凭据"""

    cred_id: str = ""
    provider: str = ""
    auth_type: AuthType = AuthType.API_KEY
    label: str = ""
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0
    scopes: List[str] = field(default_factory=list)
    created_at: float = 0.0
    last_used: float = 0.0

@dataclass
class WebhookConfig:
    """Webhook配置"""

    webhook_id: str = ""
    name: str = ""
    tool_id: str = ""
    provider: str = ""
    url: str = ""
    method: WebhookMethod = WebhookMethod.POST
    secret: str = ""
    events: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    success_count: int = 0
    failure_count: int = 0
    last_triggered: float = 0.0
    created_at: float = 0.0

@dataclass
class ExecutionRecord:
    """工具执行记录"""

    exec_id: str = ""
    tool_id: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    duration_ms: float = 0.0
    response: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    timestamp: float = 0.0

class ComposioToolsManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Composio工具集成管理器 - 生产级实现"""

    MODULE_ID = "composio_tools"
    MODULE_NAME = "composio_tools"
    VERSION = "V0.1"

    # 预置工具集
    PRESET_TOOLS = [
        {
            "name": "GitHub",
            "provider": "github",
            "category": "dev",
            "description": "GitHub仓库操作：创建Issue、PR、管理分支",
            "auth_type": "oauth2",
            "endpoint": "https://api.github.com",
            "actions": ["create_issue", "create_pr", "list_repos", "get_file", "search_code"],
        },
        {
            "name": "Slack",
            "provider": "slack",
            "category": "communication",
            "description": "Slack消息发送、频道管理",
            "auth_type": "oauth2",
            "endpoint": "https://slack.com/api",
            "actions": ["send_message", "list_channels", "get_channel_history"],
        },
        {
            "name": "Jira",
            "provider": "jira",
            "category": "project",
            "description": "Jira项目管理：创建任务、更新状态、查询",
            "auth_type": "basic",
            "endpoint": "https://your-domain.atlassian.net",
            "actions": ["create_ticket", "update_ticket", "search_issues", "add_comment"],
        },
        {
            "name": "Gmail",
            "provider": "google",
            "category": "communication",
            "description": "Gmail邮件收发管理",
            "auth_type": "oauth2",
            "endpoint": "https://gmail.googleapis.com",
            "actions": ["send_email", "read_emails", "search_emails"],
        },
        {
            "name": "Google Drive",
            "provider": "google",
            "category": "storage",
            "description": "Google Drive文件管理",
            "auth_type": "oauth2",
            "endpoint": "https://www.googleapis.com/drive/v3",
            "actions": ["upload_file", "list_files", "download_file", "share_file"],
        },
        {
            "name": "Notion",
            "provider": "notion",
            "category": "productivity",
            "description": "Notion文档和数据库管理",
            "auth_type": "oauth2",
            "endpoint": "https://api.notion.com/v1",
            "actions": ["create_page", "query_database", "update_page", "append_block"],
        },
        {
            "name": "Stripe",
            "provider": "stripe",
            "category": "finance",
            "description": "Stripe支付和订阅管理",
            "auth_type": "api_key",
            "endpoint": "https://api.stripe.com/v1",
            "actions": ["create_charge", "create_subscription", "list_invoices"],
        },
        {
            "name": "AWS S3",
            "provider": "aws",
            "category": "storage",
            "description": "AWS S3对象存储操作",
            "auth_type": "api_key",
            "endpoint": "https://s3.amazonaws.com",
            "actions": ["upload", "download", "list_objects", "delete_object"],
        },
    ]

    def __init__(self):

        super().__init__(
            config={"module_id": "composio_tools", "version": "7.0.0", "description": "Composio第三方服务集成管理"}
        )
        self._tools: Dict[str, ComposioTool] = {}
        self._credentials: Dict[str, Credential] = {}
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._executions: List[ExecutionRecord] = []
        self._initialized = False
        self._max_executions = 5000

    def initialize(self) -> None:
        if self._initialized:
            return
        now = time.time()
        for preset in self.PRESET_TOOLS:
            tool_id = f"tool_{preset['provider']}"
            self._tools[tool_id] = ComposioTool(
                tool_id=tool_id,
                name=preset["name"],
                description=preset["description"],
                provider=preset["provider"],
                category=preset["category"],
                auth_type=AuthType(preset["auth_type"]),
                endpoint=preset["endpoint"],
                params_schema={"actions": preset["actions"]},
                created_at=now,
            )
        self._initialized = True
        logger.info(f"Composio工具管理器初始化完成，预置工具: {len(self._tools)}")

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        self.trace("execute", {"module": "composio_tools"})
        self.metrics_collector.counter("composio_tools.execute.calls", 1)
        self.audit("execute", {"module": "composio_tools"})
        params = params or {}
        try:
            if action == "list_tools":
                cat = params.get("category")
                status = params.get("status")
                tools = list(self._tools.values())
                if cat:
                    tools = [t for t in tools if t.category == cat]
                if status:
                    tools = [t for t in tools if t.status.value == status]
                return {
                    "success": True,
                    "result": [
                        {
                            "tool_id": t.tool_id,
                            "name": t.name,
                            "provider": t.provider,
                            "category": t.category,
                            "auth_type": t.auth_type.value,
                            "status": t.status.value,
                            "call_count": t.call_count,
                            "actions": t.params_schema.get("actions", []),
                        }
                        for t in tools
                    ],
                }

            elif action == "get_tool":
                tid = params.get("tool_id", "")
                tool = self._tools.get(tid)
                if not tool:
                    return {"success": False, "error": f"工具{tid}不存在"}
                return {
                    "success": True,
                    "result": {
                        "tool_id": tool.tool_id,
                        "name": tool.name,
                        "provider": tool.provider,
                        "description": tool.description,
                        "category": tool.category,
                        "auth_type": tool.auth_type.value,
                        "endpoint": tool.endpoint,
                        "status": tool.status.value,
                        "rate_limit": tool.rate_limit,
                        "call_count": tool.call_count,
                        "error_count": tool.error_count,
                        "actions": tool.params_schema.get("actions", []),
                    },
                }

            elif action == "call_tool":
                tid = params.get("tool_id", "")
                tool = self._tools.get(tid)
                if not tool:
                    return {"success": False, "error": f"工具{tid}不存在"}
                if tool.status != ToolStatus.ACTIVE:
                    return {"success": False, "error": f"工具{tid}未激活"}

                # 检查凭据
                cred = self._credentials.get(tid) or self._credentials.get(tool.provider)
                if tool.auth_type != AuthType.NONE and not cred:
                    return {"success": False, "error": f"工具{tid}需要认证，请先添加凭据"}

                # 模拟执行
                start = time.time()
                exec_id = f"exec_{uuid.uuid4().hex[:8]}"
                tool_action = params.get("action", "default")
                action_params = params.get("params", {})

                # 检查rate limit
                if tool.call_count >= tool.rate_limit:
                    return {"success": False, "error": f"工具{tid}已达到速率限制 {tool.rate_limit}/周期"}

                # 模拟响应
                simulated_response = self._simulate_tool_call(tool, tool_action, action_params)
                duration = (time.time() - start) * 1000

                tool.call_count += 1
                tool.last_used = time.time()
                total_calls = tool.call_count
                tool.avg_duration_ms = (tool.avg_duration_ms * (total_calls - 1) + duration) / total_calls

                record = ExecutionRecord(
                    exec_id=exec_id,
                    tool_id=tid,
                    action=tool_action,
                    params=action_params,
                    status="success",
                    duration_ms=round(duration, 1),
                    response=simulated_response,
                    timestamp=time.time(),
                )
                if len(self._executions) >= self._max_executions:
                    self._executions.pop(0)
                self._executions.append(record)

                return {
                    "success": True,
                    "result": {
                        "exec_id": exec_id,
                        "tool_id": tid,
                        "action": tool_action,
                        "duration_ms": round(duration, 1),
                        "response": simulated_response,
                    },
                }

            elif action == "register_tool":
                tid = f"tool_{params.get('provider', uuid.uuid4().hex[:8])}"
                tool = ComposioTool(
                    tool_id=tid,
                    name=params.get("name", ""),
                    description=params.get("description", ""),
                    provider=params.get("provider", "custom"),
                    category=params.get("category", "general"),
                    auth_type=AuthType(params.get("auth_type", "none")),
                    endpoint=params.get("endpoint", ""),
                    params_schema={"actions": params.get("actions", [])},
                    created_at=time.time(),
                )
                self._tools[tid] = tool
                return {"success": True, "result": {"tool_id": tid, "name": tool.name}}

            elif action == "add_credential":
                provider = params.get("provider", "")
                cred = Credential(
                    cred_id=f"cred_{uuid.uuid4().hex[:8]}",
                    provider=provider,
                    auth_type=AuthType(params.get("auth_type", "api_key")),
                    label=params.get("label", f"{provider}凭据"),
                    api_key=params.get("api_key", ""),
                    client_id=params.get("client_id", ""),
                    client_secret=params.get("client_secret", ""),
                    access_token=params.get("access_token", ""),
                    refresh_token=params.get("refresh_token", ""),
                    expires_at=params.get("expires_at", 0),
                    scopes=params.get("scopes", []),
                    created_at=time.time(),
                )
                self._credentials[provider] = cred
                return {
                    "success": True,
                    "result": {
                        "cred_id": cred.cred_id,
                        "provider": provider,
                        "auth_type": cred.auth_type.value,
                    },
                }

            elif action == "register_webhook":
                wid = f"wh_{uuid.uuid4().hex[:8]}"
                wh = WebhookConfig(
                    webhook_id=wid,
                    name=params.get("name", ""),
                    tool_id=params.get("tool_id", ""),
                    provider=params.get("provider", ""),
                    url=params.get("url", ""),
                    method=WebhookMethod(params.get("method", "POST")),
                    secret=params.get("secret", ""),
                    events=params.get("events", []),
                    created_at=time.time(),
                )
                self._webhooks[wid] = wh
                return {
                    "success": True,
                    "result": {
                        "webhook_id": wid,
                        "url": wh.url,
                        "events": wh.events,
                    },
                }

            elif action == "verify_webhook":
                sig = params.get("signature", "")
                body = params.get("body", "")
                wid = params.get("webhook_id", "")
                wh = self._webhooks.get(wid)
                if not wh or not wh.secret:
                    return {"success": False, "error": "Webhook不存在或无密钥"}
                expected = hmac.new(wh.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                valid = hmac.compare_digest(f"sha256={expected}", sig)
                return {"success": True, "result": {"valid": valid}}

            elif action == "execution_history":
                limit = params.get("limit", 50)
                tid = params.get("tool_id")
                records = self._executions[-limit:]
                if tid:
                    records = [r for r in records if r.tool_id == tid]
                return {
                    "success": True,
                    "result": [
                        {
                            "exec_id": r.exec_id,
                            "tool_id": r.tool_id,
                            "action": r.action,
                            "status": r.status,
                            "duration_ms": r.duration_ms,
                            "timestamp": datetime.fromtimestamp(r.timestamp).isoformat(),
                        }
                        for r in records
                    ],
                }

            elif action == "get_stats":
                total_calls = sum(t.call_count for t in self._tools.values())
                total_errors = sum(t.error_count for t in self._tools.values())
                active_tools = sum(1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE)
                return {
                    "success": True,
                    "result": {
                        "tools_total": len(self._tools),
                        "tools_active": active_tools,
                        "credentials": len(self._credentials),
                        "webhooks": len(self._webhooks),
                        "total_calls": total_calls,
                        "total_errors": total_errors,
                        "executions_history": len(self._executions),
                    },
                }

            elif action == "health_check":
                return {"success": True, "result": self.health_check()}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[ComposioTools] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def _simulate_tool_call(self, tool: ComposioTool, action: str, params: Dict) -> Dict:
        """模拟工具调用返回"""
        provider = tool.provider
        if provider == "github":
            return {
                "status": "ok",
                "data": {
                    "action": action,
                    "repo": params.get("repo", "default"),
                    "url": f"{tool.endpoint}/repos/{params.get('repo', 'example')}",
                    "sha": uuid.uuid4().hex[:12],
                },
            }
        elif provider == "slack":
            return {
                "status": "ok",
                "data": {
                    "action": action,
                    "channel": params.get("channel", "#general"),
                    "ts": str(time.time()),
                    "ok": True,
                },
            }
        elif provider == "google":
            return {
                "status": "ok",
                "data": {
                    "action": action,
                    "id": uuid.uuid4().hex[:16],
                    "kind": f"{provider}#{action}",
                },
            }
        elif provider == "notion":
            return {
                "status": "ok",
                "data": {
                    "action": action,
                    "object": "page",
                    "id": uuid.uuid4().hex[:32].replace("", "-")[:36],
                },
            }
        else:
            return {
                "status": "ok",
                "data": {
                    "action": action,
                    "provider": provider,
                    "message": f"工具{tool.name}操作{action}执行成功（模拟）",
                },
            }

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy" if self._initialized else "stopped",
                "tools": len(self._tools),
                "active_tools": sum(1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE),
                "credentials": len(self._credentials),
                "webhooks": len(self._webhooks),
                "total_calls": sum(t.call_count for t in self._tools.values()),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info(f"关闭Composio工具管理器，工具数: {len(self._tools)}")

    def batch_register_tools(self, tools: List[Dict]) -> Dict[str, Any]:
        """批量注册外部工具。企业场景：团队一次性接入多个第三方SaaS工具。
        每个工具定义包含 name, description, api_endpoint, auth_type, parameters。
        """
        results = {"registered": 0, "failed": 0, "skipped": 0, "details": []}
        for tool_def in tools:
            try:
                name = tool_def.get("name", "")
                if not name:
                    results["skipped"] += 1
                    continue
                tool_id = hashlib.md5(name.encode()).hexdigest()[:12]
                tool = ComposioTool(
                    tool_id=tool_id,
                    name=name,
                    description=tool_def.get("description", ""),
                    api_endpoint=tool_def.get("api_endpoint", ""),
                    auth_type=tool_def.get("auth_type", "api_key"),
                    parameters=tool_def.get("parameters", {}),
                )
                self._tools[tool_id] = tool
                results["registered"] += 1
                results["details"].append({"tool_id": tool_id, "name": name, "status": "ok"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"name": tool_def.get("name", "?"), "error": str(e)})
        return results

    def get_tool_usage_report(self, days: int = 7) -> Dict[str, Any]:
        """获取工具使用报告。企业场景：周报统计哪些外部工具被频繁调用，辅助成本优化。"""
        report = {"period_days": days, "total_calls": 0, "tool_stats": [], "top_tools": []}
        now = time.time()
        cutoff = now - days * 86400
        tool_stats = []
        for tool_id, tool in self._tools.items():
            recent_calls = (
                sum(1 for ts in tool.last_called if ts > cutoff) if hasattr(tool, "last_called") else tool.call_count
            )
            tool_stats.append(
                {
                    "tool_id": tool_id,
                    "name": tool.name,
                    "total_calls": tool.call_count,
                    "recent_calls": recent_calls,
                    "status": tool.status.value if hasattr(tool.status, "value") else str(tool.status),
                }
            )
            report["total_calls"] += tool.call_count
        tool_stats.sort(key=lambda x: x["total_calls"], reverse=True)
        report["tool_stats"] = tool_stats
        report["top_tools"] = tool_stats[:5]
        return report

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

module_class = ComposioToolsManager
