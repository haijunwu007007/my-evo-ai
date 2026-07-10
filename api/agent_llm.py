from __future__ import annotations
"""LLM调用层 — 统一使用 core.llm_gateway.LLMPool（单例）

此模块所有函数委托给 LLMPool 全局实例，无需维护自己的 Provider 逻辑。
通过 config.yaml / 环境变量自动完成 Provider 配置。

功能：
- 自动故障切换：主模型失败自动尝试备用模型（按 priority 排序）
- 超时兜底：timeout 参数控制，超时自动降级到下一个 Provider
"""
import os
from core.llm_gateway import get_llm_pool
from core.logging_config import get_logger

logger = get_logger("evo.api.agent_llm")
_pool = None

# ── 备用 Provider 列表（当 LLMPool 主模型失败时降级）──
_FALLBACK_PROVIDERS = []


def _get_pool():
    """获取全局 LLMPool 单例"""
    global _pool
    if _pool is None:
        _pool = get_llm_pool()
        _init_fallback_providers()
    return _pool


def _init_fallback_providers():
    """初始化备用 Provider 列表（按优先级排序）"""
    global _FALLBACK_PROVIDERS
    fallbacks = []
    # 1. 环境变量显式指定的备用模型
    fb = os.environ.get("EVO_FALLBACK_MODELS", "")
    if fb:
        for entry in fb.split(","):
            entry = entry.strip()
            if "|" in entry:
                prov, model = entry.split("|", 1)
                fallbacks.append({"provider": prov.strip(), "model": model.strip(), "priority": 99})
    # 2. 检测 llm_gateway 中的其他 Provider
    try:
        if _pool and hasattr(_pool, "list_providers"):
            providers = _pool.list_providers()
            # 排除默认 provider，其他按优先级排序
            defaults = [p.get("name", "") for p in providers if p.get("is_default")]
            others = [p for p in providers if p.get("name", "") not in defaults and p.get("name", "")]
            for p in others:
                fallbacks.append({"provider": p.get("name", ""), "model": p.get("model", ""), "priority": 50})
    except Exception as _e:
        logger.warning(f"error: {_e}")
    _FALLBACK_PROVIDERS = fallbacks
    if fallbacks:
        logger.info("[LLM-FALLBACK] 备用模型: %s", [f["provider"] for f in fallbacks])


def call_llm(messages, tools=None, key="", timeout=None):
    """调用 LLM，返回 (content, tool_calls)

    支持自动故障切换：主模型失败 → 备用 Provider 依次重试。

    messages: list[dict] — [{"role": "user", "content": "..."}]
    tools: 暂不通过 LLMPool 传递 tools 参数
    key: 忽略，LLMPool 自动从环境变量/配置文件获取密钥
    timeout: 超时秒数，默认 15s
    returns: (content_str, []) 或 ("", [])
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _TimeoutError

    try:
        pool = _get_pool()
        if pool is None:
            return ("LLM不可用：LLMPool 未初始化", [])

        # 提取消息
        prompt = ""
        system_prompt = ""
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                prompt = content

        if not prompt:
            prompt = "\n".join(
                m.get("content", "") for m in (messages or []) if isinstance(m, dict)
            )

        # ── 尝试主模型 ──
        _timeout = timeout or 15
        content = _try_call(pool, prompt, system_prompt, _timeout)
        if content:
            return (content, [])

        # ── 主模型失败 → 尝试每个备用 Provider ──
        if _FALLBACK_PROVIDERS:
            logger.info("[LLM-FALLBACK] 主模型失败，尝试 %d 个备用模型", len(_FALLBACK_PROVIDERS))
            for fb in _FALLBACK_PROVIDERS:
                fb_content = _try_call_with_provider(
                    pool, prompt, system_prompt, fb["provider"], fb.get("model", ""), _timeout
                )
                if fb_content:
                    return (fb_content, [])

        logger.warning("[LLM] 所有模型均失败")
        return ("", [])

    except Exception as e:
        logger.error("[LLM] call_llm 异常: %s", e)
        return ("", [])


def _try_call(pool, prompt, system_prompt, timeout):
    """尝试用默认模型调用 LLM"""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _TimeoutError
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                pool.chat_sync, prompt=prompt, system_prompt=system_prompt, temperature=0.7
            )
            result = future.result(timeout=timeout)
        if result and result.get("success"):
            content = result.get("response", "")
            if content and len(content) > 3:
                logger.info("[LLM] 主模型成功: len=%d model=%s", len(content), result.get("model", "?"))
                return content
    except _TimeoutError:
        logger.warning("[LLM] 主模型超时 (%ds)", timeout)
    except Exception as e:
        logger.warning("[LLM] 主模型异常: %s", e)
    return ""


def _try_call_with_provider(pool, prompt, system_prompt, provider, model, timeout):
    """尝试用指定 Provider 调用 LLM"""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _TimeoutError
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                pool.chat_sync, prompt=prompt, system_prompt=system_prompt,
                temperature=0.7, provider=provider, model=model,
            )
            result = future.result(timeout=timeout)
        if result and result.get("success"):
            content = result.get("response", "")
            if content and len(content) > 3:
                logger.info("[LLM-FALLBACK] %s 成功: len=%d", provider, len(content))
                return content
        logger.warning("[LLM-FALLBACK] %s 失败: %s", provider, result.get("error", "无返回") if result else "无返回")
    except _TimeoutError:
        logger.warning("[LLM-FALLBACK] %s 超时 (%ds)", provider, timeout)
    except Exception as e:
        logger.warning("[LLM-FALLBACK] %s 异常: %s", provider, e)
    return ""


def call_llm_stream(messages, key=""):
    """流式调用（简化版：先非流式获取，按字符 yield）"""
    text, _ = call_llm(messages, key=key)
    if text:
        for ch in text:
            yield ch
    else:
        yield ""


def get_active_model():
    """返回当前活跃的模型信息"""
    try:
        pool = _get_pool()
        if pool is None:
            return {"provider": "", "model": "", "active": False}
        providers = pool.list_providers()
        default_provider = next((p for p in providers if p.get("is_default")), providers[0] if providers else {})
        return {
            "provider": default_provider.get("name", ""),
            "model": pool._default_model if hasattr(pool, "_default_model") else "",
            "models": pool.list_models() if hasattr(pool, "list_models") else [],
            "active": bool(providers),
        }
    except Exception as e:
        logger.warning("[LLM] get_active_model 异常: %s", e)
        return {"provider": "", "model": "", "active": False}
