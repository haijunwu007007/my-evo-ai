"""为22个模块添加 from __future__ import annotations — 修复前向引用问题"""
from pathlib import Path

MODULES = Path("D:\\AUTO-EVO-AI-V0.1\\modules")

modules = [
    "agent_hephaestus", "agent_marketplace",
    "bitmap_operations", "bucket_policy", "cpu_profiler",
    "dependency_injector", "event_bus", "form_builder",
    "geo_search", "hyperloglog", "langgraph_decision",
    "opentelemetry_bridge", "project_mgmt", "ragflow",
    "release_manager", "rule_engine", "second_brain",
    "self_healing", "table_engine", "workflow_manager",
    "agent_boreas", "agent_planner",
]

fixed = 0
for m in modules:
    fp = MODULES / f"{m}.py"
    content = fp.read_text(encoding='utf-8')
    
    if 'from __future__ import annotations' in content:
        print(f"  {m}: 已有 __future__ 导入")
        continue
    
    # 在第一个 """ docstring """ 之后、第一个 import 之前插入
    lines = content.split('\n')
    insert_pos = None
    
    # 找 docstring 结束位置
    in_docstring = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip().startswith('"""'):
            in_docstring = True
            continue
        if in_docstring:
            if line.strip().endswith('"""'):
                insert_pos = i + 1
                break
    
    if insert_pos is None:
        # 如果没有 docstring，在第一个 import 前插入
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_pos = i
                break
    
    if insert_pos is None:
        insert_pos = 0
    
    lines.insert(insert_pos, 'from __future__ import annotations')
    fp.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ {m}")
    fixed += 1

print(f"\n共修复: {fixed} 个模块")
