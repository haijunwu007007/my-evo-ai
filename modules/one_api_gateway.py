from __future__ import annotations
"""
AUTO-EVO-AI V0.1 — one-api LLM 统一网关模块
=========================================
集成 <https://github.com/songquanpeng/one-api>
通过 one-api 统一管理 20+ 中国大模型提供商（智谱/DeepSeek/文心/豆包等）
所有模块通过 OpenAI 兼容接口调用，无需单独配置每家 API Key。
"""

import json, time, os
from typing import Any, Dict, List, Optional
from datetime import datetime
from core.logging_config import get_logger
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

logger = get_logger("evo.one_api_gateway")

ONE_API_BASE = os.environ.get("ONE_API_BASE", "http://localhost:3000")
ONE_API_KEY = os.environ.get("ONE_API_KEY", "")


class OneApiGateway(EnterpriseModule):
    """one-api 统一网关封装 — 通过 OpenAI 兼容接口调用任意模型"""

    MODULE_ID = "one-api-gateway"
    MODULE_NAME = "one-api 统一网关"
    MODULE_VERSION = "V0.1"
    MODULE_LEVEL = "CORE"

    def __init__(self, config: dict | None = None):
        super().__init__(module_id=self.MODULE_ID, module_name=self.MODULE_NAME)
        self._base = (config or {}).get("base_url", ONE_API_BASE)
        self._key = (config or {}).get("api_key", ONE_API_KEY)
        self._models: list[dict] = []
        self._stats: dict = {"total_requests": 0, "total_tokens": 0, "failed": 0}
        self._cache: dict[str, Any] = {}

    def _api_call(self, method: str, path: str, data: dict | None = None) -> dict:
        """调用 one-api 管理 API"""
        import urllib.request, urllib.error
        url = f"{self._base}/api{path}"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data else None
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning(f"one-api call failed: {url} {e}")
            return {"success": False, "error": str(e)}

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info(f"[ONE-API] 网关已连接: {self._base}")

    def health_check(self) -> dict:
        try:
            r = self._api_call("GET", "/status")
            ok = r.get("success", False) if isinstance(r, dict) else False
        except Exception:
            ok = False
        return {
            "module_id": self.MODULE_ID,
            "status": "ok" if ok else "error",
            "healthy": ok,
            "base_url": self._base,
            "models": len(self._models),
        }

    def get_status(self) -> dict:
        return {
            "module_id": self.MODULE_ID,
            "status": self.status.value,
            "base_url": self._base,
            "models": len(self._models),
            "stats": self._stats,
            "healthy": self.status == ModuleStatus.RUNNING,
        }

    def _get_available_actions(self) -> list[dict]:
        return [
            {"name": "chat", "desc": "调用 one-api 中的任意模型"},
            {"name": "list_models", "desc": "获取可用模型列表"},
            {"name": "stats", "desc": "网关使用统计"},
        ]

    async def execute(self, action: str, params: dict | None = None) -> dict:
        p = params or {}
        if action == "list_models":
            return await self._list_models()
        if action == "chat":
            return await self._chat(p)
        if action == "stats":
            return {"success": True, "data": self._stats}
        return {"success": False, "error": f"unknown action: {action}"}

    async def _list_models(self) -> dict:
        """获取 one-api 中配置的所有模型"""
        r = self._api_call("GET", "/models")
        if isinstance(r, list):
            self._models = r
        elif isinstance(r, dict) and "data" in r:
            self._models = r["data"]
        else:
            return self._mock_models()
        return {"success": True, "models": self._models, "count": len(self._models)}

    def _mock_models(self) -> dict:
        """one-api 不在线时返回推荐的模型列表"""
        models = [
            {"id": "zhipu:glm-4-flash", "provider": "智谱", "name": "GLM-4-Flash"},
            {"id": "zhipu:glm-4-plus", "provider": "智谱", "name": "GLM-4-Plus"},
            {"id": "deepseek:chat", "provider": "DeepSeek", "name": "DeepSeek V3"},
            {"id": "openai:gpt-4o-mini", "provider": "OpenAI", "name": "GPT-4o-mini"},
            {"id": "claude:claude-3-haiku", "provider": "Anthropic", "name": "Claude 3 Haiku"},
        ]
        return {"success": True, "models": models, "count": len(models), "note": "离线模式"}

    async def _chat(self, params: dict) -> dict:
        """通过 one-api 调用聊天（OpenAI 兼容接口）"""
        model = params.get("model", "zhipu:glm-4-flash")
        messages = params.get("messages", [{"role": "user", "content": params.get("prompt", "")}])
        import urllib.request, urllib.error
        url = f"{self._base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        body = json.dumps({"model": model, "messages": messages, "temperature": params.get("temperature", 0.7)}).encode()
        self._stats["total_requests"] += 1
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            usage = result.get("usage", {})
            self._stats["total_tokens"] += usage.get("total_tokens", 0)
            return {
                "success": True,
                "model": model,
                "content": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "usage": usage,
            }
        except Exception as e:
            self._stats["failed"] += 1
            logger.warning(f"one-api chat failed: {model} {e}")
            return {"success": False, "error": str(e), "model": model}


module_class = OneApiGateway
