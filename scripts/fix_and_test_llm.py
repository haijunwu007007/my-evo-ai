import sys, os, json, urllib.request
os.chdir('/home/ubuntu/my-evo-ai')
sys.path.insert(0, '/home/ubuntu/my-evo-ai')

from api.agent_llm import free_providers, _cooldowns

# Clear cooldowns
_cooldowns.clear()
logger.info(f'Providers: {len(free_providers)}'))
for p in free_providers:
    name = p.get('name','?')
    has_key = bool(p.get('api_key')) or bool(os.environ.get(p.get('env','')))
    m = p.get("model","?")
    logger.info(f'  {name}: key={has_key}, model={m}'))

# Test direct call
key = 'b52c6e6a225a41928354521392b19541.Yih7xNOORHmw0qYM'
data = json.dumps({"model":"GLM-4-Flash","messages":[{"role":"user","content":"hi"}]}).encode()
req = urllib.request.Request(
    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    data=data,
    headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"}
)
try:
    r = urllib.request.urlopen(req, timeout=15)
    resp = json.loads(r.read())
    text = resp.get("choices",[{}])[0].get("message",{}).get("content","")
    logger.info(f'\nAPI TEST: OK - {text[:100]}'))
except Exception as e:
    body = ''
    if hasattr(e, 'read'):
        try: body = e.read().decode()[:200]
        except: pass
    logger.info(f'\nAPI TEST: FAIL - {str(e)[:100]} | {body}'))
