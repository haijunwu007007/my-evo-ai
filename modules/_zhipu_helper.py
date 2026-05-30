"""Shared LLM helper for modules - calls local Zhipu API directly."""
import json, urllib.request, urllib.error, logging, os
logger = logging.getLogger("zhipu_llm")

_ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "d9f5a51b0a014a68ad5ba34653a616dc.vJtwFWKvLbIZ67Uz")
_API2D_KEY = os.environ.get("API2D_KEY", "fk242997-B0YGuNctpt45eveYnaJVhKNylgNVHbG6")
_API2D_URL = "https://oa.api2d.net/v1/chat/completions"

def llm_chat(prompt: str, system: str = "", temperature: float = 0.7, provider: str = "zhipu") -> str:
    """Call LLM API and return response text. Supports zhipu (default) or api2d."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    if provider == "api2d":
        payload = json.dumps({"model": "gpt-3.5-turbo","messages": messages,"temperature": temperature}).encode()
        url = _API2D_URL; key = _API2D_KEY
    else:
        payload = json.dumps({"model": "glm-4.7","messages": messages,"temperature": temperature}).encode()
        url = _ZHIPU_URL; key = _ZHIPU_API_KEY
    
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json","Authorization": f"Bearer {key}"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error("Zhipu LLM call failed: %s", e)
        return ""
