"""服务器全量审计"""
import sys, importlib, os

sys.path.insert(0, '/home/ubuntu/my-evo-ai/api')
sys.path.insert(0, '/home/ubuntu/my-evo-ai')

# 1. 模块导入
modules = [
    'agent_a2a','agent_accomplish','agent_browser_use','agent_composio',
    'agent_concurrent','agent_core','agent_evolve','agent_gems',
    'agent_gpt_researcher','agent_letta','agent_llm','agent_mcp',
    'agent_memory','agent_memos','agent_moltron','agent_openhands',
    'agent_plan','agent_sandbox','agent_self_evolving','agent_spec',
    'agent_toolbench','agent_tools','agent_workflow'
]
ok = 0
fail = []
for m in modules:
    try:
        importlib.import_module(m)
        ok += 1
    except Exception as e:
        fail.append(f'{m}: {str(e)[:80]}')
print(f'IMPORT: {ok}/{len(modules)}')
if fail:
    for f in fail:
        print(f'  FAIL {f}')

# 2. pip包版本
pkgs = {
    'browser_use': 'browser_use',
    'gpt_researcher': 'gpt_researcher',
    'openhands': 'openhands',
    'letta': 'letta',
    'composio': 'composio',
    'playwright': 'playwright',
}
for pname, modname in pkgs.items():
    try:
        mod = importlib.import_module(modname)
        ver = getattr(mod, '__version__', '?')
        print(f'  PIP {pname}: {ver}')
    except Exception as e:
        print(f'  PIP {pname}: NOT_FOUND')

# 3. 检查exec_tool里工具定义
from agent_tools import exec_tool
src = open('/home/ubuntu/my-evo-ai/api/agent_tools.py').read()
tools_check = [
    'browser_use_task', 'gpt_research', 'openhands_generate',
    'letta_message', 'composio_execute', 'self_evolving_analyze',
    'moltron_learn', 'accomplish_desktop', 'toolbench_discover'
]
for t in tools_check:
    if t in src:
        print(f'  TOOL {t}: OK')
    else:
        print(f'  TOOL {t}: MISSING')

# 4. 检查get_tools定义
core_src = open('/home/ubuntu/my-evo-ai/api/agent_core.py').read()
for t in tools_check:
    if t in core_src:
        print(f'  CORE {t}: OK')
    else:
        print(f'  CORE {t}: MISSING')

print('DONE')
sys.exit(len(fail))
