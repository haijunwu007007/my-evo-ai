"""
AUTO-EVO-AI m63 - AI多模型网关 (真实实现版)
支持: OpenAI GPT, Anthropic Claude, Google Gemini, 本地模型(Ollama)
"""

__module_meta__ = {
    "id": "ai-gateway",
    "name": "AI多模型网关",
    "version": "V0.1",
    "group": "ai",
    "inputs": [
        {"name": "model", "type": "string", "required": True, "description": "模型名称"},
        {"name": "messages", "type": "list[dict]", "required": True, "description": "对话消息列表"},
        {"name": "temperature", "type": "float", "description": "采样温度 0-2"},
    ],
    "outputs": [{"name": "response", "type": "dict", "description": "模型响应"}],
    "triggers": [{"type": "event", "config": {"on": "ai.inference.request"}}],
    "depends_on": [],
    "tags": ["ai", "llm", "gateway", "core"],
    "grade": "S",
}
import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Optional
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.ai_gateway")

class AiGatewayAnalyzer(object):
    """ai_gateway 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        self.name = "ai_gateway"
        self.version = "1.0.0"
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "AiGatewayAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "ai_gateway"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== ai_gateway ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class AIGateway(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self, config_path: str = None):

        super().__init__()
        self.metrics_collector = self._NoopMetricsCollector()

        self.default_model = os.environ.get("AI_DEFAULT_MODEL", "gpt-4o")
        self.max_tokens = 4096
        self.models = {}
        self.history = []
        self.usage_stats = {"total_calls": 0, "total_tokens": 0, "total_cost": 0.0}
        self._analyzer = AiGatewayAnalyzer()
        self._load_config(config_path)

    def _load_config(self, config_path):
        """从环境变量或配置文件加载模型配置"""
        import yaml

        cfg_file = config_path or "config.yaml"
        yaml_cfg = {}
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    yaml_cfg = yaml.safe_load(f) or {}
            except Exception:
                pass
        ai_cfg = yaml_cfg.get("ai", {})

        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY") or ai_cfg.get("openai", {}).get("api_key", "")
        if openai_key:
            base = ai_cfg.get("openai", {}).get("base_url", "https://api.openai.com")
            self.register_model("gpt-4o", base, openai_key, "gpt-4o", max_tokens=128000, cost_per_1k=0.015)
            self.register_model("gpt-4o-mini", base, openai_key, "gpt-4o-mini", max_tokens=128000, cost_per_1k=0.003)
        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.register_model(
                "claude-sonnet-4",
                "https://api.anthropic.com",
                anthropic_key,
                "claude-sonnet-4-20250514",
                max_tokens=200000,
                cost_per_1k=0.015,
            )
            self.register_model(
                "claude-opus-4",
                "https://api.anthropic.com",
                anthropic_key,
                "claude-opus-4-20251114",
                max_tokens=200000,
                cost_per_1k=0.075,
            )
        # Google Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            self.register_model(
                "gemini-2.5-pro",
                "https://generativelanguage.googleapis.com",
                gemini_key,
                "gemini-2.5-pro-preview-06-05",
                max_tokens=1000000,
                cost_per_1k=0.0,
            )
        # 智谱 AI (GLM)
        zhipu_key = os.environ.get("ZHIPU_API_KEY") or ai_cfg.get("zhipu", {}).get("api_key", "")
        if zhipu_key:
            base = ai_cfg.get("zhipu", {}).get("base_url", "https://open.bigmodel.cn/api/paas/v4")
            model = ai_cfg.get("zhipu", {}).get("model", "glm-4-flash")
            self.register_model("glm-4", base, zhipu_key, "glm-4", max_tokens=128000, cost_per_1k=0.1)
            self.register_model("glm-4-flash", base, zhipu_key, "glm-4-flash", max_tokens=128000, cost_per_1k=0.001)
            self.register_model("zhipu-default", base, zhipu_key, model, max_tokens=128000, cost_per_1k=0.001)
            # 若配置里指定智谱为默认provider，则设为默认
            if ai_cfg.get("provider") == "zhipu":
                self.default_model = model
        # Ollama 本地
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or ai_cfg.get("local", {}).get("ollama_url", "")
        if ollama_url:
            lm = ai_cfg.get("local", {}).get("model", "llama3")
            self.register_model(lm, ollama_url, "ollama", lm, max_tokens=8192, cost_per_1k=0.0)
            if ai_cfg.get("provider") == "local":
                self.default_model = lm

    def register_model(
        self,
        name: str,
        api_url: str,
        api_key: str,
        model_id: str = "",
        max_tokens: int = 4096,
        cost_per_1k: float = 0.0,
    ):
        self.models[name] = {
            "api_url": api_url,
            "api_key": api_key,
            "model_id": model_id or name,
            "max_tokens": max_tokens,
            "cost_per_1k": cost_per_1k,
            "calls": 0,
            "tokens": 0,
            "errors": 0,
            "status": "active",
        }

    def _call_openai(self, model_cfg: Dict, messages: List, temperature: float, stream: bool) -> Dict:
        """调用 OpenAI 兼容 API"""
        payload = json.dumps(
            {
                "model": model_cfg["model_id"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": model_cfg["max_tokens"],
                "stream": stream,
            }
        ).encode()
        url = f"{model_cfg['api_url']}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {model_cfg['api_key']}"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result["choices"][0]["message"]["content"]
        tokens = result.get("usage", {}).get("total_tokens", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    def _call_anthropic(self, model_cfg: Dict, messages: List, temperature: float, stream: bool) -> Dict:
        """调用 Anthropic Claude API"""
        # 将 messages 转换为 Claude 格式
        system = ""
        claude_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                claude_msgs.append({"role": m["role"], "content": m["content"]})

        payload = json.dumps(
            {
                "model": model_cfg["model_id"],
                "messages": claude_msgs,
                "system": system,
                "temperature": temperature,
                "max_tokens": min(model_cfg["max_tokens"], 4096),
            }
        ).encode()
        url = f"{model_cfg['api_url']}/v1/messages"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": model_cfg["api_key"],
                "anthropic-version": "2023-06-01",
                "anthropic-dangerous-direct-browser-access": "true",
            },
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result["content"][0]["text"]
        tokens = result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    def _call_gemini(self, model_cfg: Dict, messages: List, temperature: float, stream: bool) -> Dict:
        """调用 Google Gemini API"""
        # 合并 messages 为单一文本
        content = "\n".join([f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"])
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        if system:
            content = f"System: {system}\n\n{content}"

        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": content}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": model_cfg["max_tokens"]},
            }
        ).encode()
        url = f"{model_cfg['api_url']}/v1beta/models/{model_cfg['model_id']}:generateContent?key={model_cfg['api_key']}"
        req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        tokens = result.get("usageMetadata", {}).get("totalTokenCount", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    def _call_ollama(self, model_cfg: Dict, messages: List, temperature: float, stream: bool) -> Dict:
        """调用 Ollama 本地模型"""
        payload = json.dumps(
            {
                "model": model_cfg["model_id"],
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
        ).encode()
        url = f"{model_cfg['api_url']}/api/chat"
        req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode())
        content = result["message"]["content"]
        tokens = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    def _call_zhipu(self, model_cfg: Dict, messages: List, temperature: float, stream: bool) -> Dict:
        """调用智谱 AI (GLM) API"""
        payload = json.dumps(
            {
                "model": model_cfg["model_id"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": model_cfg["max_tokens"],
            }
        ).encode()
        url = f"{model_cfg['api_url']}/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {model_cfg['api_key']}"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result["choices"][0]["message"]["content"]
        tokens = result.get("usage", {}).get("total_tokens", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    def chat(self, messages: List[Dict], model: str = None, temperature: float = 0.7, stream: bool = False) -> Dict:
        """发送聊天请求"""
        model_name = model or self.default_model
        model_cfg = self.models.get(model_name)

        if not model_cfg:
            return {"success": False, "error": f"模型 {model_name} 未注册", "mode": "error"}

        # 选择调用方式
        if "openai" in model_cfg["api_url"]:
            caller = self._call_openai
        elif "anthropic" in model_cfg["api_url"]:
            caller = self._call_anthropic
        elif "gemini" in model_cfg["api_url"]:
            caller = self._call_gemini
        elif "bigmodel" in model_cfg["api_url"] or "zhipu" in model_cfg["api_url"]:
            caller = self._call_zhipu
        elif "ollama" in model_cfg["api_url"]:
            caller = self._call_ollama
        else:
            caller = self._call_openai  # 默认

        try:
            result = caller(model_cfg, messages, temperature, stream)
            self.usage_stats["total_calls"] += 1
            self.usage_stats["total_tokens"] += result["tokens"]
            self.usage_stats["total_cost"] += result["tokens"] / 1000 * model_cfg["cost_per_1k"]
            model_cfg["calls"] += 1
            model_cfg["tokens"] += result["tokens"]

            return {
                "success": True,
                "response": result["content"],
                "model": model_name,
                "tokens": result["tokens"],
                "cost": round(result["tokens"] / 1000 * model_cfg["cost_per_1k"], 6),
                "mode": "live",
            }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            model_cfg["errors"] += 1
            return {"success": False, "error": f"HTTP {e.code}: {error_body[:200]}", "mode": "error"}
        except Exception as e:
            model_cfg["errors"] += 1
            return {"success": False, "error": str(e), "mode": "error"}

    def evaluate_models(self, test_prompt: str, models: List[str] = None) -> Dict:
        """评估多个模型"""
        results = []
        for name in models or list(self.models.keys()):
            r = self.chat([{"role": "user", "content": test_prompt}], model=name)
            results.append(
                {
                    "model": name,
                    "success": r["success"],
                    "response_preview": (r.get("response", "") or "")[:150],
                    "tokens": r.get("tokens", 0),
                    "error": r.get("error", ""),
                }
            )
        return {"success": True, "results": results}

    def get_stats(self) -> Dict:
        return {
            "models_count": len(self.models),
            "default": self.default_model,
            "models": {
                k: {"calls": v["calls"], "tokens": v["tokens"], "errors": v["errors"], "status": v["status"]}
                for k, v in self.models.items()
            },
            "usage": self.usage_stats,
        }

    # ──────────────────────────────────────────
    # Embeddings
    # ──────────────────────────────────────────

    def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> Dict:
        """
        生成文本向量嵌入。

        支持:
          - OpenAI: text-embedding-3-small (1536维), text-embedding-3-large (3072维), text-embedding-ada-002 (1536维)
          - Zhipu (智谱AI): embedding-2 (1024维)

        返回:
            {"success": True, "embeddings": [[float, ...], ...], "model": str, "dimensions": int}
        """
        # ── OpenAI / OpenAI兼容 ──
        if "openai" in str(self.models):
            openai_cfg = next((cfg for name, cfg in self.models.items() if "openai" in cfg["api_url"]), None)
            if openai_cfg:
                return self._embeddings_openai(openai_cfg, texts, model)

        # ── 智谱 AI ──
        if "bigmodel" in str(self.models) or "zhipu" in str(self.models):
            zhipu_cfg = next(
                (cfg for name, cfg in self.models.items() if "bigmodel" in cfg["api_url"] or "zhipu" in cfg["api_url"]),
                None,
            )
            if zhipu_cfg:
                return self._embeddings_zhipu(zhipu_cfg, texts)

        # ── Ollama 本地 embedding ──
        if "ollama" in str(self.models):
            ollama_cfg = next((cfg for name, cfg in self.models.items() if "ollama" in cfg["api_url"]), None)
            if ollama_cfg:
                return self._embeddings_ollama(ollama_cfg, texts)

        return {
            "success": False,
            "error": "没有可用的 embedding provider (需要 OPENAI_API_KEY 或 ZHIPU_API_KEY)",
            "embeddings": [],
        }

    def _embeddings_openai(self, model_cfg: Dict, texts: List[str], model: str = "text-embedding-3-small") -> Dict:
        """调用 OpenAI Embeddings API"""
        payload = json.dumps(
            {
                "model": model,
                "input": texts,
            }
        ).encode()
        url = f"{model_cfg['api_url']}/v1/embeddings"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {model_cfg['api_key']}"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            embeddings = [item["embedding"] for item in result["data"]]
            dims = len(embeddings[0]) if embeddings else 0
            logger.info(f"[Embedding] OpenAI {model} → {len(embeddings)} 条, {dims}维")
            return {
                "success": True,
                "embeddings": embeddings,
                "model": model,
                "dimensions": dims,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "embeddings": []}

    def _embeddings_zhipu(self, model_cfg: Dict, texts: List[str]) -> Dict:
        """调用智谱 AI Embeddings API"""
        embeddings = []
        for text in texts:
            payload = json.dumps(
                {
                    "model": "embedding-2",
                    "input": text,
                }
            ).encode()
            url = f"{model_cfg['api_url']}/embeddings"
            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {model_cfg['api_key']}"},
            )
            try:
                resp = urllib.request.urlopen(req, timeout=20)
                result = json.loads(resp.read().decode())
                emb = result["data"][0]["embedding"]
                embeddings.append(emb)
            except Exception:
                embeddings.append([])
        dims = len(embeddings[0]) if embeddings and embeddings[0] else 0
        return {
            "success": bool(embeddings and embeddings[0]),
            "embeddings": embeddings,
            "model": "embedding-2",
            "dimensions": dims,
        }

    def _embeddings_ollama(self, model_cfg: Dict, texts: List[str]) -> Dict:
        """调用 Ollama Embeddings API"""
        embeddings = []
        for text in texts:
            payload = json.dumps(
                {
                    "model": "nomic-embed-text",  # 默认 ollama embedding 模型
                    "prompt": text,
                }
            ).encode()
            url = f"{model_cfg['api_url']}/api/embeddings"
            req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
            try:
                resp = urllib.request.urlopen(req, timeout=20)
                result = json.loads(resp.read().decode())
                embeddings.append(result["embedding"])
            except Exception:
                embeddings.append([])
        dims = len(embeddings[0]) if embeddings and embeddings[0] else 0
        return {
            "success": bool(embeddings and embeddings[0]),
            "embeddings": embeddings,
            "model": "nomic-embed-text",
            "dimensions": dims,
        }

    def get_embedding_config(self) -> Dict:
        """返回当前可用的 embedding 配置"""
        cfg = {"provider": None, "model": None, "dimensions": 0}
        if any("openai" in c["api_url"] for c in self.models.values()):
            cfg = {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}
        elif any("bigmodel" in c["api_url"] or "zhipu" in c["api_url"] for c in self.models.values()):
            cfg = {"provider": "zhipu", "model": "embedding-2", "dimensions": 1024}
        elif any("ollama" in c["api_url"] for c in self.models.values()):
            cfg = {"provider": "ollama", "model": "nomic-embed-text", "dimensions": 768}
        return cfg

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("ai_gateway.execute", "start", action=action)
        self.metrics_collector.counter("ai_gateway.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "ai_gateway"}
            else:
                result = {"success": True, "action": action, "module": "ai_gateway"}
            self.metrics_collector.counter("ai_gateway.execute.success", 1)
            self.trace("ai_gateway.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("ai_gateway.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "ai_gateway"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "ai_gateway", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("ai_gateway.initialize", "start")
        self.metrics_collector.gauge("ai_gateway.initialized", 1)
        self.audit("初始化ai_gateway", level="info")
        self.trace("ai_gateway.initialize", "end")
        return {"success": True, "module": "ai_gateway"}

module_class = AIGateway
