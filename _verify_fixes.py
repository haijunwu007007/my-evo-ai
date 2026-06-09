"""验证所有修复"""
import os, sys
sys.path.insert(0, os.path.abspath('.'))
errors = []

# 1. routes_agents
try:
    import api.routes.routes_agents as ra
    print('OK routes_agents 导入成功')
    assert 'deepseek' in ra._LLM_ENDPOINTS[0]['url']
    print('OK DeepSeek端点')
except Exception as e:
    errors.append(f'routes_agents: {e}')

# 2. agent_core
try:
    import api.agent_core as ac
    print('OK agent_core 导入成功')
    assert ac._DEFAULT_KEY == 'sk-e7a7f4e700d847f28027c5608e3f5c02'
except Exception as e:
    errors.append(f'agent_core: {e}')

# 3. agent模块Key注入
agents_dir = 'api/agents'
files = ['agent_s2c.py','agent_chat2db.py','agent_bolt.py','agent_claude.py','agent_legal.py','agent_pra.py','agent_qodo.py','agent_aider.py','agent_tts.py','agent_lida.py','agent_markitdown.py','agent_scrapegraphai.py','agent_interpreter.py','agent_openclaw.py','agent_zen.py','agent_shannon.py','agent_openant.py','agent_twenty.py','agent_invoice.py','agent_chatwoot.py','agent_mermaid.py','agent_agentk8s.py','agent_gptpilot.py','agent_swe.py','agent_agenteval.py','agent_autogpt.py','agent_openmanus.py','agent_chatdev.py','agent_paddleocr.py']
ok = 0
for fname in files:
    fp = os.path.join(agents_dir, fname)
    if not os.path.exists(fp):
        errors.append(f'缺失: {fname}')
        continue
    c = open(fp, encoding='utf-8', errors='replace').read()
    if '_LLM_ENDPOINT' in c:
        ok += 1
    else:
        errors.append(f'{fname} 缺Key')
print(f'OK Agent Key注入: {ok}/{len(files)}')

# 4. chat.html
html = open('frontend/chat.html', encoding='utf-8').read()
if '\u201d\u201c' in html:
    errors.append('chat.html 连引号')
else:
    print('OK chat.html 语法')

# 5. 模块
mdir = 'modules'
pys = [f for f in os.listdir(mdir) if f.endswith('.py') and not f.startswith('_')]
print(f'OK 剩余模块: {len(pys)}个')

if errors:
    print(f'\nFAIL {len(errors)}个:')
    for e in errors: print(f'  - {e}')
else:
    print('\nOK 全部通过！')
