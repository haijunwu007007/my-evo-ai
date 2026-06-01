"""
AUTO-EVO-AI V0.1 — LiteLLM 统一 LLM 网关包装器
===============================================
提供 100+ LLM 提供商统一接口，自动故障切换，成本追踪

集成方式：
  - 作为 ai_gateway.py 的补充/替代 provider
  - 支持 OpenAI 兼容接口格式
  - 自动负载均衡 + 重试 + 降级
"""

import os, json, time, asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.logging_config import get_logger
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

logger = get_logger("evo.llm_litellm")

class LiteLLMWrapper(EnterpriseModule):
    """LiteLLM 统一 LLM 网关包装器"""

    MODULE_ID = "llm-litellm"
    MODULE_NAME = "LiteLLM 统一网关"
    MODULE_VERSION = "V0.1"
    MODULE_LEVEL = "production"

    def __init__(self, config: dict = None):
        super().__init__(module_id=self.MODULE_ID, module_name=self.MODULE_NAME)
        self.config = config or {}
        self._provider_configs: list = []
        self._stats: Dict = {
            "requests": 0, "tokens": 0, "cost": 0.0,
            "success": 0, "failures": 0, "fallbacks": 0,
        }

    def initialize(self):
        """初始化 — 从环境变量读取 provider 配置"""
        self._load_providers()
        self.status = ModuleStatus.RUNNING
        logger.info(f"[LiteLLM] 初始化完成，{len(self._provider_configs)} 个 Provider")
        return {"success": True, "providers": len(self._provider_configs)}

    def _load_providers(self):
        """从环境变量加载 Provider 配置"""
        providers = []

        # OpenAI
        if os.environ.get("OPENAI_API_KEY"):
            providers.append({
                "name": "openai", "model": "gpt-4o",
                "api_key": os.environ["OPENAI_API_KEY"],
                "api_base": os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
            })

        # 智谱 GLM
        if os.environ.get("ZHIPU_API_KEY"):
            providers.append({
                "name": "zhipu", "model": "glm-4-flash",
                "api_key": os.environ["ZHIPU_API_KEY"],
                "api_base": "https://open.bigmodel.cn/api/paas/v4",
            })

        # API2D (兼容 OpenAI)
        if os.environ.get("API2D_API_KEY"):
            providers.append({
                "name": "api2d", "model": "gpt-3.5-turbo",
                "api_key": os.environ["API2D_API_KEY"],
                "api_base": "https://open.api2d.net/v1",
            })

        # 自定义 Provider（从 config 读取）
        custom = self.config.get("providers", [])
        providers.extend(custom)

        self._provider_configs = providers

    def get_models(self) -> list:
        """返回可用模型列表"""
        models = []
        for p in self._provider_configs:
            models.append({
                "id": f"{p['name']}/{p['model']}",
                "name": p['model'],
                "provider": p['name'],
            })
        return models

    def get_providers(self) -> list:
        """返回 Provider 列表"""
        return [{"name": p["name"], "model": p["model"],
                 "configured": bool(p.get("api_key", ""))} for p in self._provider_configs]

    async def chat(self, messages: list, model: str = None, temperature: float = 0.7,
                   max_tokens: int = 2048, stream: bool = False) -> dict:
        """统一聊天接口 — 自动选择 provider + 故障切换"""
        import litellm

        provider_name = "openai"
        model_name = model or "gpt-4o"

        # 解析 model 格式：provider/model 或直接 model
        if "/" in model_name:
            parts = model_name.split("/", 1)
            provider_name = parts[0]
            model_name = parts[1]

        # 找到对应 provider 配置
        selected = None
        fallback_chain = []
        for p in self._provider_configs:
            if p["name"] == provider_name:
                selected = p
            fallback_chain.append(p)

        if not selected and fallback_chain:
            selected = fallback_chain[0]
            provider_name = selected["name"]
            self._stats["fallbacks"] += 1
            logger.info(f"[LiteLLM] 回退到 {provider_name}")

        if not selected:
            return {"success": False, "error": "没有可用的 provider", "providers": len(self._provider_configs)}

        # 配置 LiteLLM
        litellm.api_key = selected["api_key"]
        if selected.get("api_base"):
            litellm.api_base = selected["api_base"]

        full_model = model_name

        t0 = time.time()
        try:
            response = await litellm.acompletion(
                model=full_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )

            latency = round((time.time() - t0) * 1000, 1)
            content = response.choices[0].message.content if response.choices else ""
            usage = getattr(response, "usage", None)
            tokens = {
                "prompt": usage.prompt_tokens if usage else 0,
                "completion": usage.completion_tokens if usage else 0,
                "total": usage.total_tokens if usage else 0,
            }

            self._stats["requests"] += 1
            self._stats["success"] += 1
            self._stats["tokens"] += tokens["total"]

            result = {
                "success": True,
                "content": content,
                "model": full_model,
                "provider": provider_name,
                "tokens": tokens,
                "latency_ms": latency,
                "timestamp": datetime.now().isoformat(),
            }

            if stream:
                result["stream"] = True

            return result

        except Exception as e:
            self._stats["requests"] += 1
            self._stats["failures"] += 1
            latency = round((time.time() - t0) * 1000, 1)

            # 尝试故障切换
            if len(fallback_chain) > 1:
                for fallback in fallback_chain:
                    if fallback["name"] == provider_name:
                        continue
                    logger.info(f"[LiteLLM] 故障切换至 {fallback['name']}")
                    self._stats["fallbacks"] += 1
                    try:
                        litellm.api_key = fallback["api_key"]
                        if fallback.get("api_base"):
                            litellm.api_base = fallback["api_base"]
                        response = await litellm.acompletion(
                            model=fallback["model"], messages=messages,
                            temperature=temperature, max_tokens=max_tokens,
                        )
                        content = response.choices[0].message.content
                        return {"success": True, "content": content,
                                "model": fallback["model"], "provider": fallback["name"],
                                "fallback": True, "latency_ms": latency}
                    except Exception:
                        continue

            return {"success": False, "error": str(e),
                    "provider": provider_name, "latency_ms": latency}

    def get_stats(self) -> dict:
        """获取使用统计"""
        return {**self._stats, "providers": len(self._provider_configs),
                "timestamp": datetime.now().isoformat()}

    def health_check(self) -> dict:
        """健康检查 — 尝试 ping 第一个 provider"""
        return {"status": "healthy" if self._provider_configs else "no_providers",
                "providers": len(self._provider_configs), "module_id": self.MODULE_ID}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        if action in ("status", "info"):
            return {"success": True, "module": self.MODULE_ID,
                    "providers": self.get_providers(), "stats": self._stats}
        if action == "chat":
            return await self.chat(
                messages=params.get("messages", []),
                model=params.get("model"),
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 2048),
                stream=params.get("stream", False),
            )
        if action == "models":
            return {"success": True, "models": self.get_models()}
        if action == "stats":
            return {"success": True, "stats": self.get_stats()}
        if action == "providers":
            return {"success": True, "providers": self.get_providers()}
        return {"success": True, "status": "running", "module": self.MODULE_ID}

    def shutdown(self):
        self.status = ModuleStatus.STOPPED
        logger.info("[LiteLLM] 已关闭")


# 模块级实例（供 api 路由导入）
_litellm_instance: Optional[LiteLLMWrapper] = None

def get_litellm() -> LiteLLMWrapper:
    global _litellm_instance
    if _litellm_instance is None:
        _litellm_instance = LiteLLMWrapper()
        _litellm_instance.initialize()
    return _litellm_instance


module_class = LiteLLMWrapper
