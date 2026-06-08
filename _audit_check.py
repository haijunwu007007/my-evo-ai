"""全量审计：检查所有修复优化是否完整"""
import os, sys, importlib, inspect

sys.path.insert(0, "D:\\AUTO-EVO-AI-V0.1")
api_dir = "D:\\AUTO-EVO-AI-V0.1\\api"

# ── 1. 检查agent_*.py全部可导入 ──
agent_files = sorted(f for f in os.listdir(api_dir) if f.startswith("agent_") and f.endswith(".py"))
print(f"\n{'='*60}")
print(f"【1/6】api/agent_*.py 文件导入检查: {len(agent_files)} 个文件")
print('='*60)

ok = []
fail = []
for f in agent_files:
    modname = f.replace(".py","")
    try:
        spec = importlib.util.spec_from_file_location(modname, os.path.join(api_dir, f))
        if spec and spec.loader:
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            ok.append(f)
        else:
            fail.append(f"{f} -> spec无效")
    except Exception as e:
        fail.append(f"{f} -> {e}")

print(f"  通过: {len(ok)}  失败: {len(fail)}")
if fail:
    for f in fail:
        print(f"  ❌ {f}")

# ── 2. 检查agent_tools.py注册了哪些工具 ──
print(f"\n{'='*60}")
print("【2/6】agent_tools.py 工具注册检查")
print('='*60)

tool_file = os.path.join(api_dir, "agent_tools.py")
tool_names = set()
if os.path.exists(tool_file):
    with open(tool_file, "r", encoding="utf-8") as f:
        content = f.read()
    # 找所有 ToolDef 定义
    import re
    tool_defs = re.findall(r'ToolDef\(name=[\'"]([\w_]+)[\'"]', content)
    tool_names = set(tool_defs)
    print(f"  已注册工具: {len(tool_defs)} 个")
    for t in sorted(tool_defs):
        print(f"    - {t}")
else:
    print("  ❌ agent_tools.py 不存在！")

# 期望的8个新集成工具
expected_new_tools = {
    "browser_use_task", "gpt_research", "openhands_generate",
    "letta_message", "composio_execute", "toolbench_discover",
    "self_evolving_analyze", "moltron_learn", "accomplish_desktop"
}
missing_tools = expected_new_tools - tool_names
if missing_tools:
    print(f"\n  ❌ 缺少工具: {missing_tools}")
else:
    print(f"\n  ✅ 9个新集成工具全部注册")

# ── 3. 检查agent_core.py主循环接入 ──
print(f"\n{'='*60}")
print("【3/6】agent_core.py 主循环接入检查")
print('='*60)

core_file = os.path.join(api_dir, "agent_core.py")
if os.path.exists(core_file):
    with open(core_file, "r", encoding="utf-8") as f:
        core_content = f.read()
    # 检查各模块引用
    modules_in_core = {
        "browser_use": "browser_use" in core_content or "agent_browser_use" in core_content,
        "gpt_researcher": "gpt_researcher" in core_content or "agent_gpt_researcher" in core_content,
        "openhands": "openhands" in core_content or "agent_openhands" in core_content,
        "letta": "letta" in core_content or "agent_letta" in core_content,
        "composio": "composio" in core_content or "agent_composio" in core_content,
        "toolbench": "toolbench" in core_content or "agent_toolbench" in core_content,
        "self_evolving": "self_evolving" in core_content or "agent_self_evolving" in core_content,
        "moltron": "moltron" in core_content or "agent_moltron" in core_content,
        "accomplish": "accomplish" in core_content or "agent_accomplish" in core_content,
    }
    all_ok = True
    for mod, found in modules_in_core.items():
        status = "✅" if found else "❌"
        if not found: all_ok = False
        print(f"  {status} {mod}")
    if all_ok:
        print(f"\n  ✅ 9个模块全部接入主循环")
    else:
        print(f"\n  ❌ 有模块未接入")
else:
    print("  ❌ agent_core.py 不存在！")

# ── 4. 检查5个pip包 ──
print(f"\n{'='*60}")
print("【4/6】pip包可用性检查（本地）")
print('='*60)

packages = [
    ("browser_use", "browser-use"),
    ("gpt_researcher", "gpt-researcher"),
    ("letta", "letta"),
    ("composio_langchain", "composio-langchain"),
    ("playwright", "playwright"),
]
for impname, pkgname in packages:
    try:
        importlib.import_module(impname)
        print(f"  ✅ {pkgname}")
    except ImportError:
        print(f"  ❌ {pkgname} (未安装)")

# ── 5. 检查原有功能完整性 ──
print(f"\n{'='*60}")
print("【5/6】原有功能模块完整性")
print('='*60)

legacy_modules = ["agent_core", "agent_llm", "agent_tools", "agent_concurrent",
                   "agent_memos", "agent_spec", "agent_evolve", "agent_a2a",
                   "agent_plan", "agent_memory", "agent_workflow", "agent_mcp",
                   "agent_sandbox", "agent_gems", "routes_smart_chat"]
for mod in legacy_modules:
    fpath = os.path.join(api_dir, f"{mod}.py")
    exists = os.path.exists(fpath)
    print(f"  {'✅' if exists else '❌'} {mod}.py")

# ── 6. 检查服务器部署文件 ──
print(f"\n{'='*60}")
print("【6/6】检查前端和文档完整性")
print('='*60)

checks = {
    "GITHUB_AGENT_V2.md": os.path.join(api_dir, "..", "GITHUB_AGENT_V2.md"),
    "GITHUB_AGENT_ANALYSIS.md": os.path.join(api_dir, "..", "GITHUB_AGENT_ANALYSIS.md"),
    "specs/目录": os.path.join(api_dir, "..", "specs"),
    "plans/目录": os.path.join(api_dir, "..", "plans"),
}
for name, path in checks.items():
    exists = os.path.exists(path)
    print(f"  {'✅' if exists else '❌'} {name}")

print(f"\n{'='*60}")
print(f"审计完成: {len(agent_files)}个agent文件 / {len(tool_defs)}个工具 / 9模块核心检查")
print(f"{'='*60}")
