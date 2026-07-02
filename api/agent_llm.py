"""LLM调用层 — 统一使用 core.llm_gateway.LLMPool（单例）

此模块所有函数委托给 LLMPool 全局实例，无需维护自己的 Provider 逻辑。
通过 config.yaml / 环境变量自动完成 Provider 配置。
"""
from __future__ import annotations

from core.llm_gateway import get_llm_pool
from core.logging_config import get_logger

logger = get_logger("evo.api.agent_llm")
_pool = None


def _get_pool():
    """获取全局 LLMPool 单例"""
    global _pool
    if _pool is None:
        _pool = get_llm_pool()
    return _pool


def call_llm(messages, tools=None, key="", timeout=None):
    """调用 LLM，返回 (content, tool_calls)
    
    保持与原有 call_llm() 完全兼容的接口签名。
    messages: list[dict] — [{"role": "user", "content": "..."}]
    tools: 暂不通过 LLMPool 传递 tools 参数
    key: 忽略，LLMPool 自动从环境变量/配置文件获取密钥
    timeout: 超时秒数
    returns: (content_str, []) 或 ("", [])
    """
    try:
        pool = _get_pool()
        if pool is None:
            return ("LLM不可用：LLMPool 未初始化", [])

        # 提取最后一条用户消息作为 prompt
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
            # 把所有消息拼接
            prompt = "\n".join(
                m.get("content", "") for m in (messages or []) if isinstance(m, dict)
            )

        result = pool.chat_sync(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=0.7,
        )

        if result and result.get("success"):
            content = result.get("response", "")
            logger.info(
                "[LLM] chat_sync 成功: len=%d model=%s",
                len(content),
                result.get("model", "?"),
            )
            return (content, [])
        else:
            err = result.get("error", "未知错误") if result else "LLMPool 无返回"
            logger.warning("[LLM] chat_sync 失败: %s", err)
            return ("", [])

    except Exception as e:
        logger.error("[LLM] call_llm 异常: %s", e)
        return ("", [])


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
