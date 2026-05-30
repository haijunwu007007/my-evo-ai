"""Shared LLM helper for modules - calls local Zhipu API directly."""
import json, urllib.request, urllib.error, logging, os
logger = logging.getLogger("zhipu_llm")

_ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "d9f5a51b0a014a68ad5ba34653a616dc.vJtwFWKvLbIZ67Uz")
_ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def llm_chat(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    """Call Zhipu API directly and return response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({"model": "glm-4.7", "messages": messages, "temperature": temperature}).encode()
    try:
        req = urllib.request.Request(
            _ZHIPU_URL, data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {_ZHIPU_API_KEY}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error("Zhipu LLM call failed: %s", e)
        return ""
