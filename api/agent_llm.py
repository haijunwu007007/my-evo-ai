"""智能体 — LLM调用层（多Provider自动路由+流式）"""
import os, json, httpx

_LLM_PROVIDERS = [
    {"name":"Ollama-qwen2.5:1.5b","env":"","url":"http://localhost:11434/api/chat","model":"qwen2.5:1.5b","priority":0,"local":True},
    {"name":"Ollama-qwen2.5:0.5b","env":"","url":"http://localhost:11434/api/chat","model":"qwen2.5:0.5b","priority":1,"local":True},
    {"name":"Ollama-llama3.2:1b","env":"","url":"http://localhost:11434/api/chat","model":"llama3.2:1b","priority":2,"local":True},
    {"name":"DeepSeek","env":"DEEPSEEK_API_KEY","url":"https://api.deepseek.com/v1","model":"deepseek-chat","priority":3},
    {"name":"通义千问","env":"QWEN_API_KEY","url":"https://dashscope.aliyuncs.com/compatible-mode/v1","model":"qwen-plus","priority":4},
    {"name":"智谱GLM","env":"ZHIPU_API_KEY","url":"https://open.bigmodel.cn/api/paas/v4","model":"glm-4-flash","priority":5},
    {"name":"月之暗面Kimi","env":"KIMI_API_KEY","url":"https://api.moonshot.cn/v1","model":"moonshot-v1-8k","priority":6},
    {"name":"零一万物Yi","env":"YI_API_KEY","url":"https://api.lingyiwanwu.com/v1","model":"yi-lightning","priority":7},
    {"name":"OpenAI","env":"OPENAI_API_KEY","url":"https://api.openai.com/v1","model":"gpt-4o-mini","priority":8},
]

def call_llm(messages, tools=None, key=""):
    for p in sorted(_LLM_PROVIDERS, key=lambda x: x["priority"]):
        try:
            if p.get("local"):
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"stream":False,"options":{"num_predict":4096}}, timeout=30)
                if r.status_code == 200:
                    content = r.json().get("message",{}).get("content","")
                    if content: return content, None
                continue
            api_key = key or os.environ.get(p["env"],"")
            if not api_key: continue
            payload = {"model":p["model"],"messages":messages,"temperature":0.1,"max_tokens":8192}
            if tools: payload["tools"] = tools
            url = p["url"].rstrip("/")+"/chat/completions"
            r = httpx.post(url, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}, json=payload, timeout=300)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices",[{}])[0].get("delta",{}).get("content","") or data.get("choices",[{}])[0].get("message",{}).get("content","")
                tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
                return content, tc
        except: continue
    return None, None

def call_llm_stream(messages, key="", system_prompt=""):
    """流式调用LLM，逐个yield文本块"""
    if system_prompt:
        msgs = [{"role":"system","content":system_prompt}] + messages
    else:
        msgs = messages
    for p in sorted(_LLM_PROVIDERS, key=lambda x: x["priority"]):
        try:
            api_key = None
            if not p.get("local"):
                api_key = key or os.environ.get(p["env"],"")
                if not api_key: continue
            # 构建请求
            if p.get("local"):
                yield "local"
                yield ""
                return
            payload = {"model":p["model"],"messages":msgs,"temperature":0.1,"max_tokens":8192,"stream":True}
            url = p["url"].rstrip("/")+"/chat/completions"
            with httpx.Client(timeout=300) as client:
                with client.stream("POST", url, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}, json=payload) as r:
                    if r.status_code != 200:
                        continue
                    full = ""
                    for line in r.iter_lines():
                        if not line or line.startswith(":"): continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices",[{}])[0].get("delta",{})
                                content = delta.get("content","")
                                if content:
                                    full += content
                                    yield content
                            except Exception:
                                pass
                    yield "__DONE__"
                    return
        except: continue
    yield "__DONE__"
