"""LLM调用层 — 使用 curl 子进程（最可靠）"""
import os, json, subprocess

def _get_key():
    """获取 ZHIPU_API_KEY，优先级：环境变量 > /etc/evo.env > /etc/evo/env > 硬编码"""
    for src_name, src_val in [
        ("environ", os.environ.get("ZHIPU_API_KEY")),
        ("etc/evo.env", _read_file_key("/etc/evo.env")),
        ("etc/evo/env", _read_file_key("/etc/evo/env", prefix="Environment=")),
    ]:
        if src_val:
            return src_val
    return ""

def _read_file_key(path, prefix=""):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(prefix + "ZHIPU_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except: pass
    return ""

def call_llm(messages, tools=None, key="", timeout=None):
    # 不管传什么 key，都强制用 _get_key 的保底逻辑
    effective_key = key or _get_key()
    api_key = effective_key or _get_key()
    if not api_key:
        return ("LLM不可用，请检查API配置或稍后重试", [])
    try:
        payload = json.dumps({"model": "GLM-4-Flash", "messages": messages, "max_tokens": 8192})
        cmd = ['curl', '-s', '-X', 'POST',
               'https://open.bigmodel.cn/api/paas/v4/chat/completions',
               '-H', f'Authorization: Bearer {api_key}',
               '-H', 'Content-Type: application/json',
               '-d', payload,
               '--connect-timeout', str(timeout or 15),
               '--max-time', str(timeout or 30)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=(timeout or 30) + 5)
        import sys; print(f"=== CURL EXIT={r.returncode} STDOUT={r.stdout[:200] if r.stdout else 'EMPTY'} STDERR={r.stderr[:200] if r.stderr else 'NONE'} ===", file=sys.stderr)
        if r.returncode == 0 and r.stdout:
            try:
                data = json.loads(r.stdout)
                content = data.get("choices",[{}])[0].get("message",{}).get("content","")
                tc = data.get("choices",[{}])[0].get("message",{}).get("tool_calls",[])
                result = (content, tc) if content else ("", tc) if tc else (None, None)
                import sys; print(f"=== CALL_LLM RETURN: content_len={len(content) if content else 0}, has_tc={bool(tc)}, return={result[0][:30] if result[0] else 'NONE'} ===", file=sys.stderr)
                return result
            except json.JSONDecodeError:
                return ("", [])
        return ("", [])
    except Exception as e:
        return ("", [])

def call_llm_stream(messages, key=""):
    text, _ = call_llm(messages, key=key)
    if text:
        for i in range(0, len(text), 5):
            yield text[i:i+5]
    yield "__DONE__"

def get_active_model(api_key="") -> dict:
    return {"providers": [{"name":"GLM-4-Flash","model":"GLM-4-Flash","priority":100,"task_type":"free","available":bool(_get_key()),"in_cooldown":False,"fail_count":0}]}
