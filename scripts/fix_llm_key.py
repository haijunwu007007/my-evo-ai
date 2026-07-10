import os, re

# Read agent_llm.py
path = '/home/ubuntu/my-evo-ai/api/agent_llm.py'
with open(path) as f:
    c = f.read()

# Check if providers exist
if 'free_providers' in c:
    # Find the ZHIPU provider config and add api_key hardcoded as fallback
    key = 'b52c6e6a225a41928354521392b19541.Yih7xNOORHmw0qYM'
    
    # Pattern: a zhipu provider entry without api_key
    old = '{"name": "GLM-4-Flash", "model": "GLM-4-Flash", "priority": 100, "task_type": "free", "env": "ZHIPU_API_KEY"}'
    new = '{"name": "GLM-4-Flash", "model": "GLM-4-Flash", "priority": 100, "task_type": "free", "env": "ZHIPU_API_KEY", "api_key": "' + key + '"}'
    
    if old in c:
        c = c.replace(old, new)
        with open(path, 'w') as f:
            f.write(c)
        logger.info('FIXED: Added hardcoded API key to GLM-4-Flash provider'))
    else:
        # Check if already has api_key
        if 'api_key' in c:
            logger.info('ALREADY: provider config already has api_key field'))
        else:
            logger.info('WARN: old pattern not found, checking...'))
            # Find zhipu-related entries
            for line in c.split('\n'):
                if 'zhipu' in line.lower() or 'GLM' in line:
                    logger.info(f'  >> {line.strip()[:120]}'))
else:
    logger.info('ERROR: free_providers not found in file'))
