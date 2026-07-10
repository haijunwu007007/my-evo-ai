import sys
sys.path.insert(0, '/home/ubuntu/my-evo-ai')
from api.agent_llm import free_providers
for p in free_providers:
    name = p.get('name','?')
    model = p.get('model','?')
    env_key = p.get('env','?')
    has_key = 'YES' if p.get('api_key') or os.environ.get(env_key) else 'NO'
    logger.info(f'{name}: model={model}, env={env_key}, key={has_key}'))
import os
