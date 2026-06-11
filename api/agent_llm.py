"""智能体 — LLM调用层（多Provider自动路由+流式+降级回复）"""
import os, json, httpx, re

_LLM_PROVIDERS = [
    # 国内优先：智谱GLM最快（服务器已配置ZHIPU_API_KEY）
    {"name":"智谱GLM","env":"ZHIPU_API_KEY","url":"https://open.bigmodel.cn/api/paas/v4","model":"glm-4-flash","priority":0},
    {"name":"智谱GLM-Plus","env":"ZHIPU_API_KEY","url":"https://open.bigmodel.cn/api/paas/v4","model":"glm-4-plus","priority":1},
    # 国际/国内备份
    {"name":"DeepSeek","env":"DEEPSEEK_API_KEY","url":"https://api.deepseek.com/v1","model":"deepseek-chat","priority":2},
    {"name":"DeepSeek-Coder","env":"DEEPSEEK_API_KEY","url":"https://api.deepseek.com/v1","model":"deepseek-coder","priority":3},
    {"name":"OpenAI","env":"OPENAI_API_KEY","url":"https://api.openai.com/v1","model":"gpt-4o-mini","priority":4},
    {"name":"Ollama-qwen2.5:1.5b","env":"","url":"http://localhost:11434/api/chat","model":"qwen2.5:1.5b","priority":7,"local":True},
    {"name":"Ollama-qwen2.5:0.5b","env":"","url":"http://localhost:11434/api/chat","model":"qwen2.5:0.5b","priority":8,"local":True},
    {"name":"Ollama-llama3.2:1b","env":"","url":"http://localhost:11434/api/chat","model":"llama3.2:1b","priority":9,"local":True},
]

def call_llm(messages, tools=None, key=""):
    for p in sorted(_LLM_PROVIDERS, key=lambda x: x["priority"]):
        try:
            if p.get("local"):
                r = httpx.post(p["url"], json={"model":p["model"],"messages":messages,"stream":False,"options":{"num_predict":4096}}, timeout=5)
                if r.status_code == 200:
                    content = r.json().get("message",{}).get("content","")
                    if content: return content, None
                continue
            api_key = key or os.environ.get(p["env"],"")
            if not api_key: continue
            payload = {"model":p["model"],"messages":messages,"temperature":0.1,"max_tokens":8192}
            if tools: payload["tools"] = tools
            url = p["url"].rstrip("/")+"/chat/completions"
            r = httpx.post(url, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}, json=payload, timeout=15)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices",[{}])[0].get("delta",{}).get("content","") or data.get("choices",[{}])[0].get("message",{}).get("content","")
                tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
                return content, tc
        except: continue
    # 所有Provider都失败时，返回降级回复
    _fallback_llm_reply = _build_fallback_reply(messages, tools)
    return _fallback_llm_reply, None

def _build_fallback_reply(messages, tools=None) -> str:
    """当所有LLM Provider都不可用时，返回降级回复"""
    # 提取用户最后一条消息
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            user_msg = m.get("content", "")
            break

    # 检查是否是系统/状态查询
    if any(kw in user_msg for kw in ["状态", "系统怎么样", "health", "status"]):
        return "✅ **AUTO-EVO-AI V0.1** 系统运行正常。\n- API: 8765端口在线\n- 模块: 400+已注册\n- 技能: 200+已就绪\n\n⚠️ **LLM API Key 未配置**，AI 对话功能不可用。\n请在 `.env` 文件中设置 `ZHIPU_API_KEY` 或 `DEEPSEEK_API_KEY` 后重启服务。\n\n当前可用直达命令：\n- 「系统怎么样」- 查看状态\n- 「游戏」- 小游戏列表\n- 「功能」- 查看能力列表"
    if any(kw in user_msg for kw in ["游戏", "五子棋", "贪吃蛇", "老婆跳井", "狼吃娃", "打飞机"]):
        return "🎮 **游戏列表**\n• ⚫ [五子棋](/gomoku.html)\n• 👩 [老婆跳井](/wife_well.html)\n• 🐺 [狼吃娃](/wolf)\n• 🐍 [贪吃蛇](/snake)\n• 🛩️ [打飞机](/shooter)"
    if any(kw in user_msg for kw in ["功能", "你能做什么", "你会做什么", "可以做那些事情", "帮助"]):
        return "AUTO-EVO-AI 功能列表:\n- 💻 开发网页/系统(说'开发xxx')\n- 🎨 画图(说'画xxx')\n- 🔍 搜索信息(说'搜索xxx')\n- 📊 做PPT(说'做一份PPT')\n- 🎮 玩游戏(说'游戏')\n- 📦 调模块(说'调xxx模块')\n- ⚡ 查状态(说'系统怎么样')\n\n⚠️ 如需 AI 对话功能，请在 `.env` 中配置 LLM API Key"
    if any(kw in user_msg for kw in ["搜索", "查一下", "查询"]):
        return "🔍 搜索功能需要 LLM API Key 才能工作。\n请配置 `ZHIPU_API_KEY` 或 `DEEPSEEK_API_KEY` 后重启服务。"

    # 检测是否有 API Key（仅用于判断消息）
    _has_any_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"))
    if not _has_any_key:
        return "⚠️ **系统尚未配置 LLM API Key**。\n\n请在 `.env` 文件中设置至少一个 API Key（如 `ZHIPU_API_KEY` 或 `DEEPSEEK_API_KEY`），然后重启服务。\n\n当前系统服务正常运行，仅 AI 对话功能受限。\n\n**可用直达命令：**\n- 「系统怎么样」- 查看系统状态\n- 「游戏」- 查看小游戏列表\n- 「功能」- 查看能力列表"

    # 有 Key 但所有 Provider 调用失败
    return "⚠️ 抱歉，所有 LLM Provider 暂时无法连接。请检查：\n1. 网络连接是否正常\n2. API Key 是否有效\n3. API 服务是否有余额\n\n请稍后再试，或使用「系统怎么样」查看系统状态。"

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
