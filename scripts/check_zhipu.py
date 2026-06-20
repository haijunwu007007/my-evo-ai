import os, sys, urllib.request, json

key = 'b52c6e6a225a41928354521392b19541.Yih7xNOORHmw0qYM'

# Check env
print(f'ZHIPU_API_KEY env: {"SET" if os.environ.get("ZHIPU_API_KEY") else "NOT_SET"}')

# Direct API test
data = json.dumps({
    "model": "GLM-4-Flash",
    "messages": [{"role": "user", "content": "hi"}]
}).encode()

try:
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    )
    r = urllib.request.urlopen(req, timeout=15)
    resp = json.loads(r.read())
    text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f'DIRECT_API: OK - {text[:80]}')
except Exception as e:
    error_text = str(e)[:200]
    if hasattr(e, 'read'):
        try:
            error_text += ' | ' + e.read().decode()[:200]
        except:
            pass
    print(f'DIRECT_API: FAIL - {error_text}')
