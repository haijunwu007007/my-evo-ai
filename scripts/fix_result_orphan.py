c = open('/home/ubuntu/my-evo-ai/api/agent_llm.py', 'r').read()
old = '        if result:\n            return result\n'
new = '        pass\n'
if old in c:
    c = c.replace(old, new)
    open('/home/ubuntu/my-evo-ai/api/agent_llm.py', 'w').write(c)
    logger.info('FIXED: removed orphaned if result'))
else:
    logger.info('Pattern not found, checking...'))
    if 'if result' in c:
        logger.info('Still present but different pattern'))
    else:
        logger.info('Already clean'))
