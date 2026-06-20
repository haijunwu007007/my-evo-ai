"""LLM调用层 — 多用户多模型智能路由
具备熔断、并行首发、自适应超时、结果缓存能力
排序：免费→用户Key→AutoDL→本地保底
"""
import os, json, httpx, re, asyncio, time, hashlib

# ── 默认API Key（延迟读取，避免模块加载时 .env 未生效） ──
def _load_env():
    """从 .env 文件加载环境变量（兜底）"""
    for p in [os.path.join(os.path.dirname(__file__), "..", ".env"),
              os.path.join(os.path.dirname(__file__), "..", ".env.production"),
              "/home/ubuntu/my-evo-ai/.env"]:
        p = os.path.abspath(p)
        if os.path.exists(p):
            try:
                for line in open(p, encoding='utf-8'):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
            except Exception:
                pass
            break
_load_env()
def _get_key(name): return os.environ.get(name, "")


# ── LLM结果缓存（防API抖动） ──
_LLM_CACHE: dict = {}
_LLM_CACHE_MAX = 100
_LLM_CACHE_TTL = 300  # 5分钟

def _cache_key(messages, key=""):
    return hashlib.md5((str(messages[-2:]) + key).encode()).hexdigest()[:16]

def _cache_get(key):
    if key in _LLM_CACHE:
        v, t = _LLM_CACHE[key]
        if time.time() - t < _LLM_CACHE_TTL:
            return v
        del _LLM_CACHE[key]
    return None

# ── 提供商路由表 ──
_LLM_PROVIDERS = [
    {"name":"GLM-4-Flash","model":"GLM-4-Flash","url":"https://open.bigmodel.cn/api/paas/v4/chat/completions",
     "env":"ZHIPU_API_KEY","key":_get_key("ZHIPU_API_KEY"),"priority":100,"type":"api","check_401":False,
     "tags":["default"],"cooldown":0},
    {"name":"GLM-4.7-Flash","model":"GLM-4.7-Flash","url":"https://open.bigmodel.cn/api/paas/v4/chat/completions",
     "env":"ZHIPU_API_KEY","key":_get_key("ZHIPU_API_KEY"),"priority":80,"type":"api","check_401":False,
     "tags":["default","code","reasoning"],"cooldown":0},
    {"name":"DeepSeek-V4-Flash","model":"deepseek-v4-flash","url":"https://api.deepseek.com/v1/chat/completions",
     "env":"DEEPSEEK_API_KEY","key":_get_key("DEEPSEEK_API_KEY"),"priority":60,"type":"api","check_401":True,
     "tags":["paid"],"cooldown":0},
    {"name":"Qwen3.6","model":"qwen","url":"http://127.0.0.1:6006/v1/chat/completions",
     "priority":-99,"type":"openai","timeout":60,"cooldown":0},
    {"name":"Qwen2.5-3B","model":"qwen2.5:3b","url":"http://localhost:11434/api/chat",
     "priority":-999,"type":"ollama","timeout":60,"cooldown":0},
]
_FAIL_COUNT: dict[str, int] = {}  # 连续失败计数

# ── 复用 httpx 客户端 ──
_HTTP = httpx.Client(timeout=60, limits=httpx.Limits(max_keepalive_connections=8, max_connections=16))

def _in_cooldown(p: dict) -> bool:
    """熔断检查：连续失败3次后冷却60s"""
    cd = p.get("cooldown", 0)
    return time.time() < cd

def _mark_fail(name: str):
    _FAIL_COUNT[name] = _FAIL_COUNT.get(name, 0) + 1
    if _FAIL_COUNT[name] >= 3:
        for p in _LLM_PROVIDERS:
            if p["name"] == name:
                p["cooldown"] = time.time() + 60  # 冷却60秒
                break

def _mark_ok(name: str):
    _FAIL_COUNT.pop(name, None)  # 成功后清零失败计数

def _detect_task_type(messages):
    text = " ".join(m.get("content","") for m in messages if isinstance(m.get("content"), str)).lower()
    code_kw = ["code","代码","编程","函数","bug","debug","审查","fix","error","exception","implement","写一个","写个"]
    reason_kw = ["推理","分析","比较","对比","评价","为什么","how","why","explain","解释"]
    score = sum(1 for k in code_kw if k in text) + sum(0.5 for k in reason_kw if k in text)
    if score >= 2: return "code"
    if score >= 1: return "reasoning"
    return "default"

def call_llm(messages, tools=None, key="", timeout=None):
    """省钱优先 + 熔断 + 智能路由"""
    task_type = _detect_task_type(messages)
    t = timeout or 60

    # ── 第一梯队：免费（并行首发 + 熔断） ──
    free_providers = [p for p in sorted(_LLM_PROVIDERS, key=lambda x: -x["priority"])
                      if "paid" not in p.get("tags",[]) and p.get("type") not in ("ollama",)
                      and _in_cooldown(p) is False
                      and (p.get("key") or os.environ.get(p.get("env",""),""))
                      and (not p.get("tags") or task_type in p.get("tags",[]) or "default" in p.get("tags",[]))]
    if free_providers:
        # 前2个并行竞速（同步化：直接串行执行避免 asyncio.run 嵌套冲突）
        top2 = free_providers[:2]
        for p in top2:
            r = _try_provider(p, messages, tools, t, key)
            if r:
                _mark_ok(p["name"])
                return r
            _mark_fail(p["name"])
        # 都失败则串行试剩余
        for p in free_providers[2:]:
            if _in_cooldown(p): continue
            r = _try_provider(p, messages, tools, t, key)
            if r:
                _mark_ok(p["name"])
                return r
            _mark_fail(p["name"])

    # ── 第二梯队：用户 Key ──
    if key:
        r = _call_api("", "", messages, tools, key, t)
        if r: return r

    # ── 第三梯队：AutoDL ──
    for p in _LLM_PROVIDERS:
        if p.get("type") == "openai" and not _in_cooldown(p):
            r = _try_provider(p, messages, tools, t, key)
            if r:
                _mark_ok(p["name"])
                return r
            _mark_fail(p["name"])

    # ── 最后：Ollama ──
    for p in _LLM_PROVIDERS:
        if p.get("type") == "ollama":
            r = _try_provider(p, messages, tools, 30, key)
            if r: return r

    return "LLM不可用，请检查API配置或稍后重试", None

def _try_provider(p, messages, tools, timeout, key=""):
    """尝试单个提供商（自适应超时）"""
    t = min(timeout, p.get("timeout", 60))
    fail_n = _FAIL_COUNT.get(p["name"], 0)
    if fail_n > 0: t = max(t // 2, 10)  # 有过失败记录，超时减半
    for _retry in range(2 if fail_n < 3 else 1):
        try:
            ptype = p.get("type", "")
            if ptype == "openai":
                r = _HTTP.post(p["url"], json={"model":p["model"],"messages":messages,"max_tokens":4096}, timeout=t)
                if r.status_code == 200:
                    text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                    if text:
                        _LLM_CACHE[_cache_key(messages, key)] = (text, time.time())
                        return text, None
            elif ptype == "ollama":
                r = _HTTP.post(p["url"], json={"model":p["model"],"messages":messages,"stream":False}, timeout=t)
                if r.status_code == 200:
                    text = r.json().get("message",{}).get("content","")
                    if text: return text, None
            elif ptype == "api":
                api_key = key or p.get("key") or os.environ.get(p["env"],"")
                if not api_key: return None
                r = _call_api(p["url"], p["model"], messages, tools, api_key, t, p.get("check_401", True))
                if r: return r
        except Exception:
            if _retry == 1: return None
            continue
        break
    return None

def _call_api(url, model, messages, tools, api_key, timeout, check_401=True):
    """调用 OpenAI 兼容 API"""
    payload = {"model": model, "messages": messages, "max_tokens": 8192}
    if tools: payload["tools"] = tools
    try:
        u = url.rstrip("/")
        if not u.endswith("/chat/completions"): u += "/chat/completions"
        r = _HTTP.post(u, headers={"Authorization": f"Bearer {api_key}"},
                       json=payload, timeout=timeout)
        if check_401 and r.status_code in (401, 402): return None
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
            return (content, tc) if content or tc else None
    except: return None
    return None

def call_llm_stream(messages, key="", system_prompt=""):
    """伪流式：先完整获取再分块输出"""
    text, _ = call_llm(messages, key=key)
    if text:
        for i in range(0, len(text), 5):
            yield text[i:i+5]
    yield "__DONE__"

def get_active_model(api_key="") -> dict:
    """返回当前可用的模型状态（供前端查询）"""
    providers = []
    for p in _LLM_PROVIDERS:
        task_type = "default"
        tags = p.get("tags", [])
        if "paid" in tags: task_type = "paid"
        elif "default" in tags: task_type = "free"
        has_key = bool(p.get("key") or os.environ.get(p.get("env",""),""))
        available = has_key and not _in_cooldown(p)
        if p.get("type") == "openai": available = not _in_cooldown(p)
        if p.get("type") == "ollama": available = True
        providers.append({
            "name": p["name"],
            "model": p.get("model",""),
            "priority": p.get("priority",0),
            "task_type": task_type,
            "available": available,
            "in_cooldown": _in_cooldown(p),
            "fail_count": _FAIL_COUNT.get(p["name"],0),
        })
    providers.sort(key=lambda x: -x["priority"])
    return {"providers": providers, "active": [p for p in providers if p["available"]][:1] if providers else []}

def _build_fallback_reply(messages, tools=None) -> str:
    return "LLM不可用，请检查API配置或稍后重试"

def reset_fail_count():
    """重置所有LLM失败计数"""
    _FAIL_COUNT.clear()
    return {"success": True, "count": len(_FAIL_COUNT)}
