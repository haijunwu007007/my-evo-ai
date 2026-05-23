"""
AUTO-EVO-AI V0.1 — 系统级LLM智能网关
====================================
上市公司生产级设计：

核心能力:
  1. 统一接口 — 一个入口调所有LLM (OpenAI/Anthropic/Gemini/DeepSeek/智谱/Ollama)
  2. 自动故障转移 — 主模型失败自动切换备用
  3. 流式SSE — Server-Sent Events实时推送
  4. 智能缓存 — 相同问题+模型命中缓存(可配TTL)
  5. 成本追踪 — 实时统计Token/费用/延迟
  6. 速率保护 — 按Provider独立限流
  7. 配置热更新 — 运行时增删Provider无需重启
  8. 对话上下文 — 自动管理多轮对话历史

使用方式:
  from core.llm_gateway import LLMPool

  pool = LLMPool()
  # 注册Provider
  pool.add_provider("deepseek", {
      "type": "openai_compatible",
      "base_url": "https://api.deepseek.com",
      "api_key": "sk-xxx",
      "models": ["deepseek-chat", "deepseek-reasoner"]
  })
  # 发送请求
  result = await pool.chat("你好", model="deepseek-chat")
  # 流式请求
  async for chunk in pool.chat_stream("讲个故事"):
      print(chunk, end="")

依赖: 无外部依赖，纯标准库 (urllib/httpx可选)
"""

import os
import json
import time
import hashlib
import asyncio
import logging
import threading
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("evo.llm_gateway")


# ═══════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════

@dataclass
class ProviderConfig:
    """LLM Provider配置"""
    name: str
    provider_type: str  # openai_compatible | anthropic | gemini | ollama
    base_url: str
    api_key: str = ""
    models: List[str] = field(default_factory=list)
    priority: int = 10  # 数字越小越优先
    max_concurrent: int = 5
    timeout: int = 120
    enabled: bool = True
    # 每模型的Token限制
    max_tokens_map: Dict[str, int] = field(default_factory=lambda: defaultdict(lambda: 4096))
    # 每模型每1K token成本(USD)
    cost_per_1k_map: Dict[str, float] = field(default_factory=lambda: defaultdict(lambda: 0.0))


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str
    timestamp: float = 0.0
    model: str = ""
    tokens: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class UsageRecord:
    provider: str
    model: str
    tokens: int
    cost: float
    latency_ms: float
    success: bool
    error: str = ""
    timestamp: float = 0.0
    cached: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


# ═══════════════════════════════════════════════════
# 响应缓存
# ═══════════════════════════════════════════════════

class ResponseCache:
    """LRU响应缓存 — 相同问题+参数命中缓存"""

    def __init__(self, max_size: int = 500, default_ttl: int = 300):
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def _make_key(self, messages: List[Dict], model: str, temperature: float) -> str:
        raw = json.dumps({"m": messages, "model": model, "t": temperature}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, messages: List[Dict], model: str, temperature: float) -> Optional[Dict]:
        key = self._make_key(messages, model, temperature)
        with self._lock:
            entry = self._cache.get(key)
            if entry and time.time() - entry["ts"] < entry.get("ttl", self._default_ttl):
                self._hits += 1
                entry["hits"] = entry.get("hits", 0) + 1
                return entry["data"]
        self._misses += 1
        return None

    def set(self, messages: List[Dict], model: str, temperature: float, data: Dict, ttl: int = 0):
        key = self._make_key(messages, model, temperature)
        with self._lock:
            if len(self._cache) >= self._max_size:
                # 清理最老的50%
                sorted_keys = sorted(self._cache, key=lambda k: self._cache[k]["ts"])
                for k in sorted_keys[:self._max_size // 2]:
                    del self._cache[k]
            self._cache[key] = {"data": data, "ts": time.time(), "ttl": ttl or self._default_ttl, "hits": 0}

    def invalidate(self):
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict:
        return {"size": len(self._cache), "max": self._max_size, "hits": self._hits, "misses": self._misses}


# ═══════════════════════════════════════════════════
# 对话会话管理
# ═══════════════════════════════════════════════════

class ConversationManager:
    """多轮对话上下文管理"""

    def __init__(self, max_sessions: int = 200, max_history_per_session: int = 50):
        self._sessions: Dict[str, List[ChatMessage]] = {}
        self._max_sessions = max_sessions
        self._max_history = max_history_per_session
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> List[ChatMessage]:
        with self._lock:
            if session_id not in self._sessions:
                if len(self._sessions) >= self._max_sessions:
                    # 淘汰最旧的会话
                    oldest = min(self._sessions, key=lambda k: self._sessions[k][-1].timestamp if self._sessions[k] else 0)
                    del self._sessions[oldest]
                self._sessions[session_id] = []
            return self._sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, model: str = "", tokens: int = 0):
        with self._lock:
            msgs = self._sessions.get(session_id, [])
            msgs.append(ChatMessage(role=role, content=content, model=model, tokens=tokens))
            if len(msgs) > self._max_history:
                self._sessions[session_id] = msgs[-self._max_history:]

    def get_messages(self, session_id: str, last_n: int = 0) -> List[Dict]:
        msgs = self.get_or_create(session_id)
        if last_n and last_n < len(msgs):
            msgs = msgs[-last_n:]
        return [{"role": m.role, "content": m.content} for m in msgs]

    def clear_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)

    def list_sessions(self) -> List[Dict]:
        result = []
        for sid, msgs in self._sessions.items():
            if msgs:
                result.append({
                    "id": sid,
                    "messages": len(msgs),
                    "last_active": msgs[-1].timestamp,
                    "models_used": list(set(m.model for m in msgs if m.model))
                })
        return sorted(result, key=lambda x: x["last_active"], reverse=True)


# ═══════════════════════════════════════════════════
# 速率限制器 (Per-Provider)
# ═══════════════════════════════════════════════════

class ProviderRateLimiter:
    """滑动窗口速率限制"""

    def __init__(self, max_rpm: int = 60, max_tpm: int = 100000):
        self._max_rpm = max_rpm
        self._max_tpm = max_tpm
        self._timestamps: List[float] = []
        self._token_usage: List[tuple] = []  # (timestamp, tokens)
        self._lock = threading.Lock()

    def can_proceed(self, estimated_tokens: int = 0) -> tuple:
        """返回 (allowed, wait_seconds)"""
        now = time.time()
        with self._lock:
            # 清理60秒外的记录
            self._timestamps = [t for t in self._timestamps if now - t < 60]
            self._token_usage = [(t, tk) for t, tk in self._token_usage if now - t < 60]

            if len(self._timestamps) >= self._max_rpm:
                wait = 60 - (now - self._timestamps[0])
                return False, max(0, wait)

            total_tks = sum(tk for _, tk in self._token_usage)
            if total_tks + estimated_tokens > self._max_tpm:
                return False, 1.0  # 等待1秒让token窗口滑动

            return True, 0

    def record(self, tokens: int = 0):
        now = time.time()
        with self._lock:
            self._timestamps.append(now)
            if tokens:
                self._token_usage.append((now, tokens))


# ═══════════════════════════════════════════════════
# 成本追踪器
# ═══════════════════════════════════════════════════

class CostTracker:
    """LLM调用成本实时追踪"""

    def __init__(self, max_records: int = 10000):
        self._records: List[UsageRecord] = []
        self._max_records = max_records
        self._lock = threading.Lock()

    def record(self, rec: UsageRecord):
        with self._lock:
            self._records.append(rec)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

    def summary(self, hours: int = 24) -> Dict:
        now = time.time()
        cutoff = now - hours * 3600
        with self._lock:
            recs = [r for r in self._records if r.timestamp >= cutoff]

        if not recs:
            return {"period_hours": hours, "total_calls": 0, "total_tokens": 0, "total_cost": 0.0}

        total_tokens = sum(r.tokens for r in recs)
        total_cost = sum(r.cost for r in recs)
        success = [r for r in recs if r.success]
        failed = [r for r in recs if not r.success]
        cached = [r for r in recs if r.cached]

        # 按Provider分
        by_provider = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0, "errors": 0})
        for r in recs:
            p = by_provider[r.provider]
            p["calls"] += 1
            p["tokens"] += r.tokens
            p["cost"] += r.cost
            if not r.success:
                p["errors"] += 1

        # 按模型分
        by_model = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
        for r in recs:
            m = by_model[r.model]
            m["calls"] += 1
            m["tokens"] += r.tokens
            m["cost"] += r.cost

        latencies = [r.latency_ms for r in success]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0

        return {
            "period_hours": hours,
            "total_calls": len(recs),
            "success_calls": len(success),
            "failed_calls": len(failed),
            "cached_calls": len(cached),
            "success_rate": round(len(success) / len(recs) * 100, 1) if recs else 0,
            "cache_hit_rate": round(len(cached) / len(recs) * 100, 1) if recs else 0,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 1),
            "p50_latency_ms": round(p50_latency, 1),
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
        }


# ═══════════════════════════════════════════════════
# HTTP调用引擎
# ═══════════════════════════════════════════════════

class _HTTPCaller:
    """统一HTTP调用 — 同步/异步兼容"""

    @staticmethod
    def post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
        """同步POST请求"""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def post_stream(url: str, payload: dict, headers: dict, timeout: int = 120):
        """同步SSE流式请求 — 返回response对象供调用者逐行读取"""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp

    @staticmethod
    async def post_json_async(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
        """异步POST请求 — 使用aiohttp或回退到线程池"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    return await resp.json()
        except ImportError:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _HTTPCaller.post_json, url, payload, headers, timeout)


# ═══════════════════════════════════════════════════
# Provider适配器
# ═══════════════════════════════════════════════════

class _ProviderAdapter:
    """将统一请求格式转换为各Provider的API格式"""

    @staticmethod
    def normalize_models(cfg: ProviderConfig) -> Dict[str, dict]:
        """返回 {model_name: {model_id, max_tokens, cost_per_1k}} 映射"""
        result = {}
        for m in cfg.models:
            result[m] = {
                "model_id": m,
                "max_tokens": cfg.max_tokens_map.get(m, 4096),
                "cost_per_1k": cfg.cost_per_1k_map.get(m, 0.0),
            }
        return result

    @staticmethod
    def call(cfg: ProviderConfig, model: str, messages: List[Dict],
             temperature: float = 0.7, max_tokens: int = 0) -> Dict:
        """统一调用入口 — 根据provider_type分发"""
        model_id = model
        _max_tokens = max_tokens or cfg.max_tokens_map.get(model, 4096)

        if cfg.provider_type == "anthropic":
            return _ProviderAdapter._call_anthropic(cfg, model_id, messages, temperature, _max_tokens)
        elif cfg.provider_type == "gemini":
            return _ProviderAdapter._call_gemini(cfg, model_id, messages, temperature, _max_tokens)
        elif cfg.provider_type == "ollama":
            return _ProviderAdapter._call_ollama(cfg, model_id, messages, temperature, _max_tokens)
        else:
            # openai_compatible (默认) — 覆盖OpenAI/DeepSeek/智谱/任何兼容API
            return _ProviderAdapter._call_openai_compatible(cfg, model_id, messages, temperature, _max_tokens)

    @staticmethod
    def call_stream(cfg: ProviderConfig, model: str, messages: List[Dict],
                    temperature: float = 0.7, max_tokens: int = 0):
        """流式调用 — 返回response对象"""
        model_id = model
        _max_tokens = max_tokens or cfg.max_tokens_map.get(model, 4096)

        if cfg.provider_type == "anthropic":
            return _ProviderAdapter._stream_anthropic(cfg, model_id, messages, temperature, _max_tokens)
        elif cfg.provider_type == "ollama":
            return _ProviderAdapter._stream_ollama(cfg, model_id, messages, temperature, _max_tokens)
        else:
            return _ProviderAdapter._stream_openai_compatible(cfg, model_id, messages, temperature, _max_tokens)

    # ── OpenAI Compatible (OpenAI / DeepSeek / 智谱 / 任何兼容) ──

    @staticmethod
    def _call_openai_compatible(cfg: ProviderConfig, model: str, messages: List[Dict],
                                  temperature: float, max_tokens: int) -> Dict:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        url = f"{cfg.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        }
        result = _HTTPCaller.post_json(url, payload, headers, cfg.timeout)
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    @staticmethod
    def _stream_openai_compatible(cfg: ProviderConfig, model: str, messages: List[Dict],
                                    temperature: float, max_tokens: int):
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        url = f"{cfg.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        }
        return _HTTPCaller.post_stream(url, payload, headers, cfg.timeout)

    # ── Anthropic Claude ──

    @staticmethod
    def _call_anthropic(cfg: ProviderConfig, model: str, messages: List[Dict],
                         temperature: float, max_tokens: int) -> Dict:
        system = ""
        claude_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                claude_msgs.append({"role": m["role"], "content": m["content"]})
        payload = {
            "model": model,
            "messages": claude_msgs,
            "system": system,
            "temperature": temperature,
            "max_tokens": min(max_tokens, 8192),
        }
        url = f"{cfg.base_url.rstrip('/')}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
        }
        result = _HTTPCaller.post_json(url, payload, headers, cfg.timeout)
        content = result["content"][0]["text"]
        usage = result.get("usage", {})
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    @staticmethod
    def _stream_anthropic(cfg: ProviderConfig, model: str, messages: List[Dict],
                           temperature: float, max_tokens: int):
        system = ""
        claude_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                claude_msgs.append({"role": m["role"], "content": m["content"]})
        payload = {
            "model": model,
            "messages": claude_msgs,
            "system": system,
            "temperature": temperature,
            "max_tokens": min(max_tokens, 8192),
            "stream": True,
        }
        url = f"{cfg.base_url.rstrip('/')}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
        }
        return _HTTPCaller.post_stream(url, payload, headers, cfg.timeout)

    # ── Google Gemini ──

    @staticmethod
    def _call_gemini(cfg: ProviderConfig, model: str, messages: List[Dict],
                      temperature: float, max_tokens: int) -> Dict:
        content = "\n".join([f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"])
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        if system:
            content = f"System: {system}\n\n{content}"
        payload = {
            "contents": [{"parts": [{"text": content}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        url = f"{cfg.base_url.rstrip('/')}/v1beta/models/{model}:generateContent?key={cfg.api_key}"
        headers = {"Content-Type": "application/json"}
        result = _HTTPCaller.post_json(url, payload, headers, cfg.timeout)
        content_text = result["candidates"][0]["content"]["parts"][0]["text"]
        tokens = result.get("usageMetadata", {}).get("totalTokenCount", 0)
        return {"content": content_text, "tokens": tokens, "raw": result}

    # ── Ollama (本地) ──

    @staticmethod
    def _call_ollama(cfg: ProviderConfig, model: str, messages: List[Dict],
                      temperature: float, max_tokens: int) -> Dict:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        url = f"{cfg.base_url.rstrip('/')}/api/chat"
        headers = {"Content-Type": "application/json"}
        result = _HTTPCaller.post_json(url, payload, headers, cfg.timeout + 60)
        content = result["message"]["content"]
        tokens = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
        return {"content": content, "tokens": tokens, "raw": result}

    @staticmethod
    def _stream_ollama(cfg: ProviderConfig, model: str, messages: List[Dict],
                        temperature: float, max_tokens: int):
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        url = f"{cfg.base_url.rstrip('/')}/api/chat"
        headers = {"Content-Type": "application/json"}
        return _HTTPCaller.post_stream(url, payload, headers, cfg.timeout + 60)


# ═══════════════════════════════════════════════════
# LLM Pool — 核心网关
# ═══════════════════════════════════════════════════

class LLMPool:
    """
    系统级LLM智能网关 — 统一管理所有LLM Provider

    特性:
    - 多Provider注册与管理
    - 自动故障转移 (failover)
    - 响应缓存
    - 成本追踪
    - 速率限制
    - 对话上下文管理
    - 流式SSE支持

    使用示例:
        pool = LLMPool()
        pool.auto_configure()  # 自动从环境变量配置

        # 简单对话
        result = pool.chat_sync("你好")
        print(result["response"])

        # 带上下文的对话
        result = pool.chat_sync("继续", session_id="s1")

        # 流式
        for chunk in pool.chat_stream_sync("讲个故事"):
            print(chunk, end="")
    """

    def __init__(self):
        self._providers: Dict[str, ProviderConfig] = {}
        self._rate_limiters: Dict[str, ProviderRateLimiter] = {}
        self._cache = ResponseCache(max_size=500, default_ttl=300)
        self._conversations = ConversationManager()
        self._cost_tracker = CostTracker()
        self._default_model = "gpt-4o-mini"
        self._default_provider = ""
        self._failover_chain: List[str] = []  # 按优先级排序的provider列表
        self._lock = threading.Lock()

    # ─── Provider管理 ───

    def add_provider(self, name: str, config: Dict) -> bool:
        """注册一个LLM Provider"""
        try:
            mtm = config.pop("max_tokens_map", {})
            cpm = config.pop("cost_per_1k_map", {})
            cfg = ProviderConfig(name=name, **config)
            cfg.max_tokens_map = defaultdict(lambda: 4096, mtm)
            cfg.cost_per_1k_map = defaultdict(lambda: 0.0, cpm)
            self._providers[name] = cfg
            self._rate_limiters[name] = ProviderRateLimiter()
            self._rebuild_failover_chain()
            # 如果是第一个provider或优先级最高，设为默认
            if not self._default_provider or cfg.priority < self._providers[self._default_provider].priority:
                self._default_provider = name
                if cfg.models:
                    self._default_model = cfg.models[0]
            logger.info(f"[LLM] Provider '{name}' 已注册: {cfg.models} (优先级={cfg.priority})")
            return True
        except Exception as e:
            logger.error(f"[LLM] 注册Provider '{name}' 失败: {e}")
            return False

    def remove_provider(self, name: str) -> bool:
        """移除一个Provider"""
        with self._lock:
            if name in self._providers:
                del self._providers[name]
                self._rate_limiters.pop(name, None)
                self._rebuild_failover_chain()
                if self._default_provider == name:
                    if self._providers:
                        self._default_provider = list(self._providers.keys())[0]
                    else:
                        self._default_provider = ""
                return True
        return False

    def list_providers(self) -> List[Dict]:
        """列出所有已注册Provider"""
        result = []
        for name, cfg in self._providers.items():
            result.append({
                "name": name,
                "type": cfg.provider_type,
                "base_url": cfg.base_url,
                "models": cfg.models,
                "priority": cfg.priority,
                "enabled": cfg.enabled,
                "is_default": name == self._default_provider,
                "has_key": bool(cfg.api_key and cfg.api_key != "ollama"),
            })
        return sorted(result, key=lambda x: x["priority"])

    def list_models(self) -> List[Dict]:
        """列出所有可用模型"""
        models = []
        for name, cfg in self._providers.items():
            if not cfg.enabled:
                continue
            for m in cfg.models:
                models.append({
                    "model": m,
                    "provider": name,
                    "provider_type": cfg.provider_type,
                    "max_tokens": cfg.max_tokens_map.get(m, 4096),
                    "cost_per_1k": cfg.cost_per_1k_map.get(m, 0.0),
                    "is_default": m == self._default_model and name == self._default_provider,
                })
        return models

    def set_default(self, provider: str, model: str):
        """设置默认Provider和模型"""
        if provider in self._providers:
            self._default_provider = provider
            self._default_model = model
            return True
        return False

    def _rebuild_failover_chain(self):
        """重建故障转移链 — 按优先级排序"""
        enabled = [(n, c) for n, c in self._providers.items() if c.enabled]
        enabled.sort(key=lambda x: x[1].priority)
        self._failover_chain = [n for n, _ in enabled]

    # ─── 自动配置 (从环境变量/配置文件) ───

    def auto_configure(self, config_path: str = None):
        """
        自动从环境变量和配置文件初始化所有Provider
        支持的环境变量:
          OPENAI_API_KEY, OPENAI_BASE_URL
          DEEPSEEK_API_KEY
          ANTHROPIC_API_KEY
          GEMINI_API_KEY
          ZHIPU_API_KEY
          OLLAMA_BASE_URL
          AI_DEFAULT_MODEL (格式: provider:model)
        """
        import yaml

        yaml_cfg = {}
        cfg_file = config_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}
                    # 兼容新格式（ConfigCenter 改为 list）和老格式（dict with "ai" key）
                    yaml_cfg = raw if isinstance(raw, dict) else {}
            except Exception:
                pass
        # 后备: 尝试读取 config/defaults.yaml
        if not yaml_cfg:
            defaults_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "defaults.yaml")
            if os.path.exists(defaults_file):
                try:
                    with open(defaults_file, "r", encoding="utf-8") as f:
                        raw = yaml.safe_load(f) or {}
                        yaml_cfg = raw if isinstance(raw, dict) else {}
                except Exception:
                    pass
        ai_cfg = yaml_cfg.get("ai", {}) if isinstance(yaml_cfg, dict) else {}

        # ── OpenAI ──
        openai_key = os.environ.get("OPENAI_API_KEY") or ai_cfg.get("openai", {}).get("api_key", "")
        if openai_key:
            base = os.environ.get("OPENAI_BASE_URL") or ai_cfg.get("openai", {}).get("base_url", "https://api.openai.com")
            self.add_provider("openai", {
                "provider_type": "openai_compatible",
                "base_url": base,
                "api_key": openai_key,
                "models": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"],
                "priority": 10,
                "max_tokens_map": {"gpt-4o": 128000, "gpt-4o-mini": 128000, "o1-mini": 65536, "o3-mini": 65536},
                "cost_per_1k_map": {"gpt-4o": 0.015, "gpt-4o-mini": 0.003, "o1-mini": 0.003, "o3-mini": 0.003},
            })

        # ── DeepSeek ──
        ds_key = os.environ.get("DEEPSEEK_API_KEY") or ai_cfg.get("deepseek", {}).get("api_key", "")
        if ds_key:
            base = ai_cfg.get("deepseek", {}).get("base_url", "https://api.deepseek.com")
            self.add_provider("deepseek", {
                "provider_type": "openai_compatible",
                "base_url": base,
                "api_key": ds_key,
                "models": ["deepseek-chat", "deepseek-reasoner"],
                "priority": 5,  # 高优先级（便宜）
                "max_tokens_map": {"deepseek-chat": 64000, "deepseek-reasoner": 64000},
                "cost_per_1k_map": {"deepseek-chat": 0.0014, "deepseek-reasoner": 0.004},
            })

        # ── Anthropic Claude ──
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or ai_cfg.get("anthropic", {}).get("api_key", "")
        if anthropic_key:
            base = ai_cfg.get("anthropic", {}).get("base_url", "https://api.anthropic.com")
            self.add_provider("anthropic", {
                "provider_type": "anthropic",
                "base_url": base,
                "api_key": anthropic_key,
                "models": ["claude-sonnet-4-20250514", "claude-opus-4-20251114"],
                "priority": 15,
                "max_tokens_map": {"claude-sonnet-4-20250514": 200000, "claude-opus-4-20251114": 200000},
                "cost_per_1k_map": {"claude-sonnet-4-20250514": 0.003, "claude-opus-4-20251114": 0.015},
            })

        # ── Google Gemini ──
        gemini_key = os.environ.get("GEMINI_API_KEY") or ai_cfg.get("gemini", {}).get("api_key", "")
        if gemini_key:
            base = ai_cfg.get("gemini", {}).get("base_url", "https://generativelanguage.googleapis.com")
            self.add_provider("gemini", {
                "provider_type": "gemini",
                "base_url": base,
                "api_key": gemini_key,
                "models": ["gemini-2.5-pro-preview-06-05", "gemini-2.5-flash-preview-05-20"],
                "priority": 20,
                "max_tokens_map": {"gemini-2.5-pro-preview-06-05": 1000000, "gemini-2.5-flash-preview-05-20": 1000000},
            })

        # ── 智谱AI (GLM) ──
        zhipu_key = os.environ.get("ZHIPU_API_KEY") or ai_cfg.get("zhipu", {}).get("api_key", "")
        if zhipu_key:
            base = ai_cfg.get("zhipu", {}).get("base_url", "https://open.bigmodel.cn/api/paas/v4")
            self.add_provider("zhipu", {
                "provider_type": "openai_compatible",
                "base_url": base,
                "api_key": zhipu_key,
                "models": ["glm-4-flash", "glm-4", "glm-4-plus"],
                "priority": 12,
                "max_tokens_map": {"glm-4-flash": 128000, "glm-4": 128000, "glm-4-plus": 128000},
                "cost_per_1k_map": {"glm-4-flash": 0.001, "glm-4": 0.1, "glm-4-plus": 0.05},
            })

        # ── Ollama 本地 ──
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or ai_cfg.get("local", {}).get("ollama_url", "")
        if ollama_url:
            self.add_provider("ollama", {
                "provider_type": "ollama",
                "base_url": ollama_url,
                "api_key": "ollama",
                "models": ["llama3", "qwen2.5", "codellama", "mistral"],
                "priority": 50,  # 最低优先级（备用）
                "cost_per_1k_map": {m: 0.0 for m in ["llama3", "qwen2.5", "codellama", "mistral"]},
            })

        # ── 默认模型 ──
        default_env = os.environ.get("AI_DEFAULT_MODEL", "")
        if default_env:
            if ":" in default_env:
                prov, mod = default_env.split(":", 1)
                if prov in self._providers and mod in self._providers[prov].models:
                    self._default_provider = prov
                    self._default_model = mod
            elif ai_cfg.get("provider"):
                prov = ai_cfg["provider"]
                if prov in self._providers:
                    self._default_provider = prov
                    self._default_model = self._providers[prov].models[0]

        # ── 支持config.yaml中任意自定义Provider ──
        for prov_name, prov_cfg in ai_cfg.get("custom_providers", {}).items():
            if prov_name not in self._providers:
                self.add_provider(prov_name, {
                    "provider_type": prov_cfg.get("type", "openai_compatible"),
                    "base_url": prov_cfg.get("base_url", ""),
                    "api_key": prov_cfg.get("api_key", ""),
                    "models": prov_cfg.get("models", []),
                    "priority": prov_cfg.get("priority", 30),
                })

        logger.info(f"[LLM] 自动配置完成: {len(self._providers)} providers, 默认={self._default_provider}/{self._default_model}")

    # ─── 核心调用 ───

    def _resolve_model(self, model: str = "") -> tuple:
        """
        解析模型名到Provider配置
        返回: (provider_name, provider_config, actual_model_id)
        如果模型名包含provider前缀(如 "deepseek:deepseek-chat")则直接路由
        否则在所有provider中查找
        """
        # 带前缀格式: provider:model
        if ":" in model:
            prov, mod = model.split(":", 1)
            if prov in self._providers and mod in self._providers[prov].models:
                return prov, self._providers[prov], mod

        # 精确匹配
        for pname, cfg in self._providers.items():
            if not cfg.enabled:
                continue
            if model in cfg.models:
                return pname, cfg, model

        # 默认
        if self._default_provider and self._default_provider in self._providers:
            cfg = self._providers[self._default_provider]
            actual = model if model in cfg.models else self._default_model
            return self._default_provider, cfg, actual

        if self._providers:
            first = next(iter(self._providers.values()))
            actual = model if model in first.models else (first.models[0] if first.models else "")
            return next(iter(self._providers)), first, actual

        return "", None, ""

    def chat_sync(self, prompt: str, model: str = "", session_id: str = "",
                  system_prompt: str = "", temperature: float = 0.7,
                  max_tokens: int = 0, use_cache: bool = True) -> Dict:
        """同步聊天接口"""
        if not prompt:
            return {"success": False, "error": "prompt不能为空"}

        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if session_id:
            history = self._conversations.get_messages(session_id, last_n=20)
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        model = model or self._default_model

        # 缓存检查
        if use_cache and not session_id:
            cached = self._cache.get(messages, model, temperature)
            if cached:
                rec = UsageRecord(provider="cache", model=model, tokens=0, cost=0,
                                  latency_ms=0.1, success=True, cached=True)
                self._cost_tracker.record(rec)
                return {**cached, "cached": True}

        # 故障转移链
        provider_name, provider_cfg, actual_model = self._resolve_model(model)
        if not provider_cfg:
            return {"success": False, "error": f"无可用Provider, 模型 '{model}' 未找到"}

        # 尝试主Provider
        chain = [provider_name]
        # 如果指定了不同provider，也加入其他作为failover
        for pn in self._failover_chain:
            if pn not in chain and pn != provider_name:
                if actual_model in self._providers[pn].models:
                    chain.append(pn)

        last_error = ""
        for pn in chain:
            cfg = self._providers[pn]
            if not cfg.enabled or actual_model not in cfg.models:
                continue
            # 速率检查
            limiter = self._rate_limiters.get(pn)
            if limiter:
                allowed, wait = limiter.can_proceed()
                if not allowed:
                    last_error = f"Provider '{pn}' 速率限制，需等待{wait:.1f}s"
                    continue

            t0 = time.time()
            try:
                result = _ProviderAdapter.call(cfg, actual_model, messages, temperature, max_tokens)
                latency = (time.time() - t0) * 1000
                tokens = result["tokens"]
                cost = tokens / 1000 * cfg.cost_per_1k_map.get(actual_model, 0.0)

                # 记录
                if limiter:
                    limiter.record(tokens)
                rec = UsageRecord(provider=pn, model=actual_model, tokens=tokens,
                                  cost=cost, latency_ms=latency, success=True)
                self._cost_tracker.record(rec)

                # 对话历史
                if session_id:
                    self._conversations.add_message(session_id, "user", prompt, actual_model)
                    self._conversations.add_message(session_id, "assistant", result["content"], actual_model, tokens)

                # 缓存
                if use_cache and not session_id:
                    self._cache.set(messages, actual_model, temperature, {
                        "success": True, "response": result["content"],
                        "model": actual_model, "provider": pn,
                        "tokens": tokens, "cost": round(cost, 6),
                        "latency_ms": round(latency, 1),
                    })

                return {
                    "success": True,
                    "response": result["content"],
                    "model": actual_model,
                    "provider": pn,
                    "tokens": tokens,
                    "cost": round(cost, 6),
                    "latency_ms": round(latency, 1),
                    "cached": False,
                }
            except Exception as e:
                last_error = str(e)
                latency = (time.time() - t0) * 1000
                rec = UsageRecord(provider=pn, model=actual_model, tokens=0,
                                  cost=0, latency_ms=latency, success=False, error=last_error)
                self._cost_tracker.record(rec)
                logger.warning(f"[LLM] Provider '{pn}' 调用失败: {e}, 尝试下一个...")

        return {"success": False, "error": f"所有Provider均失败: {last_error}", "tried": chain}

    def chat_stream_sync(self, prompt: str, model: str = "", session_id: str = "",
                          system_prompt: str = "", temperature: float = 0.7,
                          max_tokens: int = 0):
        """
        同步流式聊天 — 生成器，yield每个文本chunk
        SSE格式: "data: {json}\n\n"
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if session_id:
            history = self._conversations.get_messages(session_id, last_n=20)
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        model = model or self._default_model
        provider_name, provider_cfg, actual_model = self._resolve_model(model)
        if not provider_cfg:
            yield f"data: {json.dumps({'error': f'无可用Provider, 模型 {model} 未找到'})}\n\n"
            return

        chain = [provider_name]
        for pn in self._failover_chain:
            if pn not in chain and pn != provider_name and actual_model in self._providers[pn].models:
                chain.append(pn)

        full_response = ""
        t0 = time.time()
        success = False

        for pn in chain:
            cfg = self._providers[pn]
            if not cfg.enabled or actual_model not in cfg.models:
                continue
            try:
                resp = _ProviderAdapter.call_stream(cfg, actual_model, messages, temperature, max_tokens)
                buffer = ""
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace")
                    buffer += line
                    while "\n" in buffer:
                        chunk_line, buffer = buffer.split("\n", 1)
                        chunk_line = chunk_line.strip()
                        if not chunk_line or not chunk_line.startswith("data:"):
                            continue
                        data_str = chunk_line[5:].strip()
                        if data_str == "[DONE]":
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # 解析content
                        text = ""
                        if cfg.provider_type == "ollama":
                            text = data.get("message", {}).get("content", "")
                            if not data.get("done", False):
                                full_response += text
                                yield f"data: {json.dumps({'content': text, 'done': False, 'provider': pn})}\n\n"
                            else:
                                # 最后一个chunk — 包含累计统计
                                yield f"data: {json.dumps({'content': '', 'done': True, 'provider': pn, 'tokens': data.get('eval_count', 0)})}\n\n"
                        elif cfg.provider_type == "anthropic":
                            if data.get("type") == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                full_response += text
                                yield f"data: {json.dumps({'content': text, 'done': False, 'provider': pn})}\n\n"
                            elif data.get("type") == "message_stop":
                                yield f"data: {json.dumps({'content': '', 'done': True, 'provider': pn})}\n\n"
                        else:
                            # OpenAI compatible SSE
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                text = delta.get("content", "")
                                full_response += text
                                done = choices[0].get("finish_reason") == "stop"
                                yield f"data: {json.dumps({'content': text, 'done': done, 'provider': pn})}\n\n"

                # 流结束
                latency = (time.time() - t0) * 1000
                success = True

                # 保存到对话
                if session_id and full_response:
                    self._conversations.add_message(session_id, "user", prompt, actual_model)
                    self._conversations.add_message(session_id, "assistant", full_response, actual_model)

                # 记录成本
                tokens_est = len(full_response) // 2  # 粗估
                cost = tokens_est / 1000 * cfg.cost_per_1k_map.get(actual_model, 0.0)
                rec = UsageRecord(provider=pn, model=actual_model, tokens=tokens_est,
                                  cost=cost, latency_ms=latency, success=True)
                self._cost_tracker.record(rec)

                # 流结束后发元数据
                yield f"data: {json.dumps({'meta': True, 'provider': pn, 'model': actual_model, 'latency_ms': round(latency, 1), 'tokens_est': tokens_est})}\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as e:
                logger.warning(f"[LLM] Provider '{pn}' 流式失败: {e}")
                yield f"data: {json.dumps({'error': str(e), 'provider': pn})}\n\n"

        if not success:
            yield f"data: {json.dumps({'error': '所有Provider流式调用失败'})}\n\n"
            yield "data: [DONE]\n\n"

    # ─── 会话管理 ───

    def get_session_history(self, session_id: str, last_n: int = 20) -> List[Dict]:
        return self._conversations.get_messages(session_id, last_n)

    def clear_session(self, session_id: str) -> bool:
        self._conversations.clear_session(session_id)
        return True

    def list_sessions(self) -> List[Dict]:
        return self._conversations.list_sessions()

    # ─── 统计 ───

    def get_stats(self) -> Dict:
        return {
            "providers": len(self._providers),
            "total_models": len(self.list_models()),
            "default_model": self._default_model,
            "default_provider": self._default_provider,
            "failover_chain": self._failover_chain,
            "cache": self._cache.stats(),
            "conversations": len(self._conversations.list_sessions()),
            "cost_summary": self._cost_tracker.summary(hours=24),
        }

    def get_cost_report(self, hours: int = 24) -> Dict:
        return self._cost_tracker.summary(hours)

    def clear_cache(self):
        self._cache.invalidate()
        return {"success": True}

    def health_check(self) -> Dict:
        """检查各Provider连通性"""
        results = {}
        for name, cfg in self._providers.items():
            if not cfg.enabled:
                results[name] = {"status": "disabled"}
                continue
            try:
                if cfg.provider_type == "ollama":
                    url = f"{cfg.base_url.rstrip('/')}/api/tags"
                    req = urllib.request.Request(url, method="GET")
                    urllib.request.urlopen(req, timeout=5)
                    results[name] = {"status": "healthy", "type": cfg.provider_type}
                else:
                    # 发一个最小请求测试连通性
                    url = f"{cfg.base_url.rstrip('/')}/v1/models"
                    headers = {}
                    if cfg.api_key and cfg.api_key != "ollama":
                        headers["Authorization"] = f"Bearer {cfg.api_key}"
                    req = urllib.request.Request(url, headers=headers or None, method="GET")
                    urllib.request.urlopen(req, timeout=5)
                    results[name] = {"status": "healthy", "type": cfg.provider_type}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)[:100], "type": cfg.provider_type}
        return results


# ═══════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════

_llm_pool: Optional[LLMPool] = None


def get_llm_pool() -> LLMPool:
    """获取全局LLM Pool单例"""
    global _llm_pool
    if _llm_pool is None:
        _llm_pool = LLMPool()
        _llm_pool.auto_configure()
    return _llm_pool


def reset_llm_pool():
    """重置单例（配置变更后调用）"""
    global _llm_pool
    _llm_pool = None

def get_llm_gateway():
    from core.llm_gateway import LLMPool
    return LLMPool()
