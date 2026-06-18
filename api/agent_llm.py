"""LLM调用层 — 多用户多模型自动路由
排序：用户Key→GLM-4-Flash→GLM-4.7-Flash→DeepSeek→Qwen3.6→Qwen2.5-3B
"""
import os, json, httpx, re

# ── 默认API Key（环境变量注入） ──
_ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "")
_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ── 提供商路由表（按优先级降序） ──
_LLM_PROVIDERS = [
    # 1. GLM-4-Flash — 免费主力（默认）
    {"name":"GLM-4-Flash","model":"GLM-4-Flash","url":"https://open.bigmodel.cn/api/paas/v4/chat/completions",
     "env":"ZHIPU_API_KEY","key":_ZHIPU_KEY,"priority":100,"type":"api","check_401":False,
     "tags":["default"]},

    # 2. GLM-4.7-Flash — 编程增强（免费）
    {"name":"GLM-4.7-Flash","model":"GLM-4.7-Flash","url":"https://open.bigmodel.cn/api/paas/v4/chat/completions",
     "env":"ZHIPU_API_KEY","key":_ZHIPU_KEY,"priority":80,"type":"api","check_401":False,
     "tags":["default","code","reasoning"]},

    # 3. DeepSeek V4 Flash — 付费用户默认
    {"name":"DeepSeek-V4-Flash","model":"deepseek-v4-flash","url":"https://api.deepseek.com/v1/chat/completions",
     "env":"DEEPSEEK_API_KEY","key":_DEEPSEEK_KEY,"priority":60,"type":"api","check_401":True,
     "tags":["paid"]},

    # 4. Qwen3.6-35B — AutoDL高精度（反向隧道）
    {"name":"Qwen3.6","model":"Qwen3.6-35B-Q4_K_M","url":"http://127.0.0.1:6006/v1/chat/completions",
     "priority":-99,"type":"openai","timeout":60},

    # 5. Qwen2.5-3B — 本地断网保底
    {"name":"Qwen2.5-3B","model":"qwen2.5:3b","url":"http://localhost:11434/api/chat",
     "priority":-999,"type":"ollama","timeout":60},
]

def _detect_task_type(messages):
    """根据消息检测任务类型"""
    text = " ".join(m.get("content","") for m in messages if isinstance(m.get("content"), str)).lower()
    code_keywords = ["code","代码","编程","函数","bug","debug","审查","fix","error","exception","implement"]
    reasoning_keywords = ["推理","分析","比较","对比","评价","为什么","how","why","explain"]
    score = sum(1 for k in code_keywords if k in text)
    score += sum(0.5 for k in reasoning_keywords if k in text)
    if score >= 2: return "code"
    if score >= 1: return "reasoning"
    return "default"

def call_llm(messages, tools=None, key="", timeout=None):
    """省钱优先路由：免费→用户Key→AutoDL→本地"""
    task_type = _detect_task_type(messages)
    errors = []

    # ── 第一梯队：免费提供商（系统 Key） ──
    for p in sorted(_LLM_PROVIDERS, key=lambda x: -x["priority"]):
        tags = p.get("tags", [])
        if "paid" in tags or p.get("type") in ("ollama",): continue
        if p.get("type") == "api" and not (p.get("key") or os.environ.get(p["env"],"")): continue
        if tags and task_type not in tags and "default" not in tags: continue
        r = _try_provider(p, messages, tools, timeout, key)
        if r: return r
        if r is False: errors.append(f"{p['name']}: 认证失败")

    # ── 第二梯队：用户自己的 Key ──
    if key:
        for p in _LLM_PROVIDERS:
            if p.get("type") != "api": continue
            r = _call_api(p["url"], p["model"], messages, tools, key, timeout or 60)
            if r: return r

    # ── 第三梯队：Qwen3.6 AutoDL ──
    for p in _LLM_PROVIDERS:
        if p.get("type") == "openai":
            r = _try_provider(p, messages, tools, timeout, key)
            if r: return r

    # ── 最后保底：Qwen2.5-3B本地 ──
    for p in _LLM_PROVIDERS:
        if p.get("type") == "ollama":
            r = _try_provider(p, messages, tools, timeout, key)
            if r: return r

    return "LLM不可用", None

def _try_provider(p, messages, tools, timeout, key=""):
    """尝试单个提供商（超时60s，重试1次）"""
    t = timeout or p.get("timeout", 60)
    for _retry in range(2):
        try:
            ptype = p.get("type", "")
            if ptype == "openai":
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"max_tokens":4096}, timeout=t)
                if r.status_code == 200:
                    text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                    if text: return text, None
            elif ptype == "ollama":
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"stream":False}, timeout=t)
                if r.status_code == 200:
                    text = r.json().get("message",{}).get("content","")
                    if text: return text, None
            elif ptype == "api":
                api_key = key or p.get("key") or os.environ.get(p["env"],"")
                if not api_key: return None
                r = _call_api(p["url"], p["model"], messages, tools, api_key, t, p.get("check_401", True))
                if r: return r
        except Exception:
            if _retry == 1: return None  # 重试后仍失败
            continue  # 第1次失败，重试
        break  # 成功则退出循环
    return None

def _call_api(url, model, messages, tools, api_key, timeout, check_401=True):
    """调用 OpenAI 兼容 API"""
    payload = {"model": model, "messages": messages, "max_tokens": 8192}
    if tools: payload["tools"] = tools
    try:
        u = url.rstrip("/")
        if not u.endswith("/chat/completions"): u += "/chat/completions"
        r = httpx.post(u, headers={"Authorization": f"Bearer {api_key}"},
                       json=payload, timeout=timeout)
        if check_401 and r.status_code in (401, 402): return None
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
            return (content, tc) if content or tc else None
    except:
        return None
    return None

def call_llm_stream(messages, key="", system_prompt=""):
    """伪流式LLM调用：先完整获取响应，再按5字符分块yield。

    当前为简化实现，返回 __DONE__ 标记结尾。
    后续可替换为真正的 SSE/streaming 实现。
    """
    text, _ = call_llm(messages, key=key)
    if text:
        for i in range(0, len(text), 5):
            yield text[i:i+5]
    yield "__DONE__"

def _build_fallback_reply(messages, tools=None) -> str:
    return "LLM不可用，请检查API配置或稍后重试"
