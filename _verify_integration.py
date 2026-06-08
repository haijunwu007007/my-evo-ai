"""验证9个新集成模块的导入、注册和定义"""
import sys
sys.path.insert(0, r'D:\AUTO-EVO-AI-V0.1')
import importlib

modules = [
    'api.agent_browser_use',
    'api.agent_gpt_researcher',
    'api.agent_openhands',
    'api.agent_letta',
    'api.agent_composio',
    'api.agent_self_evolving',
    'api.agent_moltron',
    'api.agent_accomplish',
    'api.agent_toolbench',
]

print('=== 9个新集成模块导入验证 ===')
ok = 0
fail = 0
for m in modules:
    try:
        mod = importlib.import_module(m)
        funcs = [f for f in dir(mod) if not f.startswith('_')]
        print(f'  [OK] {m} - 函数: {len(funcs)}个')
        ok += 1
    except Exception as e:
        print(f'  [FAIL] {m} - {e}')
        fail += 1

print(f'\n导入结果: {ok}/9 通过, {fail} 失败')

# 验证agent_tools.py中9个工具注册
print('\n=== agent_tools.py 工具注册验证 ===')
import inspect
from api.agent_tools import exec_tool
src = inspect.getsource(exec_tool)
tool_names = [
    'browser_use_task', 'gpt_research', 'openhands_generate',
    'letta_message', 'composio_execute', 'self_evolving_analyze',
    'moltron_learn', 'accomplish_desktop', 'toolbench_discover'
]
registered = []
missing = []
for t in tool_names:
    if f'name == "{t}"' in src:
        registered.append(t)
    else:
        missing.append(t)
print(f'  已注册: {len(registered)}/9')
if missing:
    print(f'  缺失: {missing}')

# 验证agent_core.py中9个工具定义
print('\n=== agent_core.py 工具定义验证 ===')
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_core.py', encoding='utf-8') as f:
    core_src = f.read()
defined = []
undef = []
for t in tool_names:
    if f'"name":"{t}"' in core_src:
        defined.append(t)
    else:
        undef.append(t)
print(f'  已定义: {len(defined)}/9')
if undef:
    print(f'  缺失: {undef}')

# 验证routes_smart_chat.py
print('\n=== routes_smart_chat.py 流式端点验证 ===')
with open(r'D:\AUTO-EVO-AI-V0.1\api\routes_smart_chat.py', encoding='utf-8') as f:
    route_src = f.read()
has_needs_tools = '_needs_tools' in route_src
has_tool_gen = 'tool_gen' in route_src
has_agent_core_in_stream = 'agent_core' in route_src and 'smart_stream' in route_src
print(f'  _needs_tools函数: {"OK" if has_needs_tools else "MISSING"}')
print(f'  tool_gen流式工具管道: {"OK" if has_tool_gen else "MISSING"}')
print(f'  流式端点集成agent_core: {"OK" if has_agent_core_in_stream else "MISSING"}')

print('\n=== 总结 ===')
all_ok = (ok == 9 and len(registered) == 9 and len(defined) == 9 
          and has_needs_tools and has_tool_gen and has_agent_core_in_stream)
print(f'  导入: {ok}/9')
print(f'  注册: {len(registered)}/9')
print(f'  定义: {len(defined)}/9')
print(f'  流式工具支持: {"OK" if has_needs_tools and has_tool_gen else "MISSING"}')
if all_ok:
    print('  全部通过! ✅')
else:
    print('  存在缺失项 ❌')
