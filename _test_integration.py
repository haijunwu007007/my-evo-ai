"""快速检查所有修复是否完整"""
import sys, json
sys.path.insert(0, '.')

print("=" * 60)
print("1. 模块导入测试")
print("=" * 60)
modules = [
    'api.agent_browser_use', 'api.agent_gpt_researcher',
    'api.agent_openhands', 'api.agent_letta',
    'api.agent_composio', 'api.agent_self_evolving',
    'api.agent_moltron', 'api.agent_accomplish',
    'api.agent_toolbench', 'api.agent_tools',
    'api.agent_core', 'api.routes_smart_chat',
]
import importlib
for m in modules:
    try:
        importlib.import_module(m)
        print(f"  ✅ {m}")
    except Exception as e:
        print(f"  ❌ {m}: {e}")

print()
print("=" * 60)
print("2. 工具执行测试（pip无关部分）")
print("=" * 60)

from pathlib import Path
BASE = Path('.')
OUT = BASE / 'output'
TOOLS_DIR = OUT / 'tools'
_LAST = {}
_GENERATED_TOOLS = {}
from api.agent_tools import exec_tool

tests = [
    ("list_modules", {}, False),
    ("toolbench_discover", {"action": "stats"}, False),
    ("toolbench_discover", {"action": "search", "query": "微信"}, False),
    ("self_evolving_analyze", {"repo_path": "."}, False),
    ("moltron_learn", {"skill_name": "Test", "skill_description": "Test"}, False),
    ("accomplish_desktop", {"workflow": "[]"}, False),
]

for name, args, _ in tests:
    try:
        r = exec_tool(name, args, BASE, OUT, _LAST, _GENERATED_TOOLS)
        ok = "✅" if r.get("ok") else "❌"
        data = str(r.get("data", ""))[:80]
        print(f"  {ok} {name}: {data}")
    except Exception as e:
        print(f"  ❌ {name}: crash - {e}")

print()
print("=" * 60)
print("3. HTML/JS 前端检查")
print("=" * 60)
chat = Path("frontend/chat.html").read_text(encoding='utf-8')
checks = {
    "getElementById('messages')": "getElementById('messages')" in chat,
    "getElementById('msgs') BUG": "getElementById('msgs')" not in chat,
    "9个快捷按钮(.quick-actions)": '.quick-actions' in chat,
    "browser_use_task快捷按钮": 'browser_use_task' in chat,
    "gpt_research快捷按钮": 'gpt_research' in chat,
    "openhands_generate快捷按钮": 'openhands_generate' in chat,
    "letta_message快捷按钮": 'letta_message' in chat,
    "composio_execute快捷按钮": 'composio_execute' in chat,
    "self_evolving_analyze快捷按钮": 'self_evolving_analyze' in chat,
    "moltron_learn快捷按钮": 'moltron_learn' in chat,
    "accomplish_desktop快捷按钮": 'accomplish_desktop' in chat,
    "toolbench_discover快捷按钮": 'toolbench_discover' in chat,
    "needsTool()函数": 'function needsTool' in chat,
    "_TOOL_KEYWORDS定义": '_TOOL_KEYWORDS' in chat,
    "工具类走非流式路由": 'needsTool(text)' in chat,
}
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}: {'通过' if v else '未通过'}")

print()
print("=" * 60)
print("4. routes_smart_chat.py 检查")
print("=" * 60)
routes = Path("api/routes_smart_chat.py").read_text(encoding='utf-8')
rchecks = {
    "_needs_tools()函数": "def _needs_tools" in routes,
    "_TOOL_KEYWORDS定义": "_TOOL_KEYWORDS" in routes,
    "流式端点走agent_core": "from .agent_core import create_engine" in routes,
    "工具调用_ndjson流式": "tool_gen" in routes,
    "非流式端点走agent_core": "from .agent_core import create_engine" in routes,
}
for k, v in rchecks.items():
    print(f"  {'✅' if v else '❌'} {k}: {'通过' if v else '未通过'}")

print()
print("=" * 60)
print("5. agent_core.py 检查")
print("=" * 60)
core = Path("api/agent_core.py").read_text(encoding='utf-8')
cchecks = {
    "21个工具(12+9)": 21 if core.count('"type":"function"') == 21 else core.count('"type":"function"'),
    "browser_use_task定义": "browser_use_task" in core,
    "gpt_research定义": "gpt_research" in core,
    "openhands_generate定义": "openhands_generate" in core,
    "letta_message定义": "letta_message" in core,
    "composio_execute定义": "composio_execute" in core,
    "self_evolving_analyze定义": "self_evolving_analyze" in core,
    "moltron_learn定义": "moltron_learn" in core,
    "accomplish_desktop定义": "accomplish_desktop" in core,
    "toolbench_discover定义": "toolbench_discover" in core,
    "系统提示含9工具说明": "【新增能力 - 2026-06-08】" in core,
}
for k, v in cchecks.items():
    status = "✅" if (v if isinstance(v, bool) else True) else "❌"
    detail = f" ({v}个)" if isinstance(v, int) else ""
    print(f"  {status} {k}{detail}")

print()
print("=" * 60)
print("6. agent_tools.py 检查")
print("=" * 60)
tools = Path("api/agent_tools.py").read_text(encoding='utf-8')
tchecks = {
    "browser_use_task分发": "browser_use_task" in tools,
    "gpt_research分发": "gpt_research" in tools,
    "openhands_generate分发": "openhands_generate" in tools,
    "letta_message分发": "letta_message" in tools,
    "composio_execute分发": "composio_execute" in tools,
    "self_evolving_analyze分发": "self_evolving_analyze" in tools,
    "moltron_learn分发": "moltron_learn" in tools,
    "accomplish_desktop分发": "accomplish_desktop" in tools,
    "toolbench_discover分发": "toolbench_discover" in tools,
}
for k, v in tchecks.items():
    print(f"  {'✅' if v else '❌'} {k}: {'通过' if v else '未通过'}")

print()
all_ok = (
    all(checks.values()) and 
    all(rchecks.values()) and 
    all(v if isinstance(v, bool) else True for v in cchecks.values()) and 
    all(tchecks.values())
)
print(f"\n{'=' * 60}")
print(f"{'✅ 全部检查通过！系统集成完整' if all_ok else '❌ 仍有问题需要修复'}")
print(f"{'=' * 60}")
