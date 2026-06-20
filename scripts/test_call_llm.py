"""Test call_llm directly"""
import os, sys
sys.path.insert(0, '/home/ubuntu/my-evo-ai')

# Set env first
os.environ['ZHIPU_API_KEY'] = 'b52c6e6a225a41928354521392b19541.Yih7xNOORHmw0qYM'

from api.agent_llm import _LLM_PROVIDERS, call_llm

print(f'Providers: {len(_LLM_PROVIDERS)}')
for p in _LLM_PROVIDERS:
    key_ok = bool(p.get('key'))
    print(f'  {p["name"]}: key_ok={key_ok} env={p.get("env","?")} cooldown={p.get("cooldown",0)}')

# Clear cooldowns
for p in _LLM_PROVIDERS:
    p['cooldown'] = 0

r = call_llm([{"role":"user","content":"hi"}])
print(f'\nResult: {r}')
