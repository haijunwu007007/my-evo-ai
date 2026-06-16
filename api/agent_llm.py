"""LLM调用层 — 本地模型自动路由"""
import os, json, httpx, re

_LLM_PROVIDERS = [
    {"name":"Qwen3.6","env":"","url":"http://127.0.0.1:5999/v1/chat/completions","model":"Qwen3.6-35B-Q4_K_M","priority":-99,"local":"openai","timeout":5},
    {"name":"Ollama","env":"","url":"http://localhost:11434/api/chat","model":"dsr1","priority":-1,"local":"ollama","timeout":60},
]

def call_llm(messages, tools=None, key=""):
    for p in sorted(_LLM_PROVIDERS, key=lambda x: x["priority"]):
        try:
            if p.get("local") == "openai":
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"max_tokens":4096}, timeout=p.get("timeout",30))
                if r.status_code == 200:
                    text = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                    if text: return text, None
            elif p.get("local") == "ollama":
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"stream":False}, timeout=p.get("timeout",30))
                if r.status_code == 200:
                    text = r.json().get("message",{}).get("content","")
                    if text: return text, None
            else:
                api_key = key or os.environ.get(p["env"],"")
                if not api_key: continue
                payload = {"model":p["model"],"messages":messages,"max_tokens":8192}
                if tools: payload["tools"] = tools
                url = p["url"].rstrip("/")
                if not url.endswith("/chat/completions"): url += "/chat/completions"
                r = httpx.post(url, headers={"Authorization":f"Bearer {api_key}"}, json=payload, timeout=15)
                if r.status_code in (401, 402): continue
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("choices",[{}])[0].get("message",{}).get("content","")
                    tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
                    return content, tc
        except:
            continue
    return "", None

def call_llm_stream(messages, key="", system_prompt=""):
    text, _ = call_llm(messages, key=key)
    if text:
        for i in range(0, len(text), 5):
            yield text[i:i+5]
    yield "__DONE__"

def _build_fallback_reply(messages, tools=None) -> str:
    return "LLM不可用"
