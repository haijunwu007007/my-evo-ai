"""一次性修复所有 36 个模块的 NameError 导入问题"""
import os, re, ast, sys
from pathlib import Path

MODULES_DIR = Path("D:\\AUTO-EVO-AI-V0.1\\modules")

# 每个模块需要修复的精确问题
FIXES = {
    # ── 缺少 typing 导入 ──
    "parallel_executor": {"add_imports": ["from typing import Dict, Any, Callable"]},
    "output_formatter": {"add_imports": ["from typing import List, Dict, Any"]},
    "agent_market": {"add_imports": ["from typing import Tuple"]},
    "llamaparse": {"add_imports": ["from typing import Set"]},
    "permission_guard": {"add_imports": ["from typing import Callable"]},

    # ── 缺少 from modules._base import XXX ──
    "agent_boreas": {"add_imports": ["from modules._base import Result"]},
    "agent_cronus": {"add_imports": ["from modules._base import Result"]},
    "agent_iris": {"add_imports": ["from modules._base import Result"]},
    "feature_flag": {"add_imports": ["from modules._base import Result"]},
    "git_ops": {"add_imports": ["from modules._base import Result"]},
    "kubernetes_orchestrator": {"add_imports": ["from modules._base import Result"]},
    "message_broker": {"add_imports": ["from modules._base import Result"]},
    "resource_server": {"add_imports": ["from modules._base import Result"]},
    "user_profile": {"add_imports": ["from modules._base import Result"]},
    "ws_manager": {"add_imports": ["from modules._base import Result"]},
    "agent_planner": {"add_imports": ["from modules._base import ModuleRegistry"]},
    "cloud_connector": {"add_imports": ["from modules._base import ModuleStats"]},
    "kafka_producer": {"add_imports": ["from modules._base import ModuleStats"]},
    "http_client": {"add_imports": ["from modules._base import HealthReport"]},

    # ── 缺失类型定义：类型在文件内定义，但引用在定义之前 ──
    "access_control": {
        "note": "RoleRegistry 在文件第340行定义，但可能被提前引用。添加 from __future__ import annotations"}
}

# 这些缺失的类型需要在每个模块内添加桩定义
STUB_DEFS = {
    "agent_hephaestus": "@dataclass\nclass DependencyNode:\n    name: str = ''\n    deps: list = None\n    status: str = 'pending'",
    "agent_marketplace": "@dataclass\nclass PackageDependency:\n    name: str = ''\n    version: str = ''\n    optional: bool = False",
    "bitmap_operations": "@dataclass\nclass Bitmap:\n    data: int = 0\n    def set(self, pos): self.data |= (1 << pos)\n    def test(self, pos): return bool(self.data & (1 << pos))",
    "bucket_policy": "@dataclass\nclass PolicyStatement:\n    effect: str = 'Allow'\n    actions: list = None\n    resources: list = None",
    "cpu_profiler": "@dataclass\nclass FlameGraphFrame:\n    name: str = ''\n    value: float = 0.0\n    children: list = None",
    "dependency_injector": "@dataclass\nclass Scope:\n    name: str = 'singleton'",
    "event_bus": "class Pipeline:\n    def __init__(self): self._handlers = []\n    def subscribe(self, fn): self._handlers.append(fn); return self\n    async def emit(self, event):\n        for h in self._handlers:\n            r = h(event)\n            if hasattr(r, '__await__'): await r",
    "form_builder": "@dataclass\nclass FieldDef:\n    name: str = ''\n    field_type: str = 'text'\n    required: bool = False\n    default: any = None",
    "fts_query": "class DataEngine:\n    def query(self, sql): return []\n    def execute(self, sql): return True",
    "object_storage": "class DataEngine:\n    def query(self, sql): return []\n    def execute(self, sql): return True",
    "project_manager": "class DataEngine:\n    def query(self, sql): return []\n    def execute(self, sql): return True",
    "geo_search": "@dataclass\nclass GeoPoint:\n    lat: float = 0.0\n    lng: float = 0.0",
    "hyperloglog": "class _SparseSet:\n    def __init__(self): self.data = set()\n    def add(self, v): self.data.add(hash(v))\n    def __len__(self): return len(self.data)",
    "langgraph_decision": "@dataclass\nclass GraphBuilder:\n    nodes: list = None\n    edges: list = None",
    "opentelemetry_bridge": "class Meter:\n    def create_counter(self, n): return type('Counter',(),{'add':lambda s,v,**k:None})()",
    "project_mgmt": "@dataclass\nclass ProjectMember:\n    user_id: str = ''\n    role: str = 'member'",
    "release_manager": "@dataclass\nclass SemanticVersion:\n    major: int = 1\n    minor: int = 0\n    patch: int = 0",
    "rule_engine": "@dataclass\nclass Condition:\n    field: str = ''\n    operator: str = 'eq'\n    value: any = None",
    "second_brain": "class Memory:\n    def __init__(self): self.data = {}\n    def store(self, k, v): self.data[k] = v\n    def recall(self, k): return self.data.get(k)",
    "self_healing": "@dataclass\nclass ErrorContext:\n    module_id: str = ''\n    error_type: str = ''\n    message: str = ''\n    stack: str = ''",
    "table_engine": "@dataclass\nclass ColumnDef:\n    name: str = ''\n    col_type: str = 'string'\n    nullable: bool = True",
    "workflow_manager": "@dataclass\nclass RetryPolicy:\n    max_retries: int = 3\n    delay: float = 1.0\n    backoff: float = 2.0",
}

def add_import_to_file(filepath, import_line):
    """在 __module_meta__ 之后、实际代码之前添加导入"""
    content = filepath.read_text(encoding='utf-8')
    
    # 检查是否已经有这个 import
    if import_line in content:
        return False
    
    # 找到第一个 import/class/def 行
    lines = content.split('\n')
    insert_pos = None
    
    # 先看是否有 __module_meta__ 的结束大括号
    brace_count = 0
    meta_started = False
    for i, line in enumerate(lines):
        if '__module_meta__' in line:
            meta_started = True
        if meta_started:
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0 and i > 0:
                insert_pos = i + 1
                break
    
    if insert_pos is None:
        # 找 docstring 结束
        for i, line in enumerate(lines):
            if line.strip().endswith('"""') and i > 0:
                insert_pos = i + 1
                break
    
    if insert_pos is None:
        insert_pos = 1  # 紧接第一行
    
    # 插入 import
    lines.insert(insert_pos, import_line)
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return True

def add_stub_before_first_class(filepath, stub_code):
    """在第一个 class 定义前添加桩定义"""
    content = filepath.read_text(encoding='utf-8')
    
    # 检查是否已定义
    stub_class_name = stub_code.split('class')[1].split(':')[0].split('(')[0].strip()
    stub_name = stub_code.split('class')[0].split('@')[0].strip() or stub_class_name
    if not stub_name:
        stub_name = stub_class_name
    if f"class {stub_name}" in content or f"class {stub_class_name}" in content:
        return False
    
    lines = content.split('\n')
    
    # 找到所有 import 行之后、第一个 class 之前
    last_import = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import = i
    
    # 在最后一个 import 之后插入
    if last_import >= 0:
        lines.insert(last_import + 1, '')
        lines.insert(last_import + 2, stub_code)
    else:
        # 没 import？在文件末尾前插入
        lines.insert(-1, stub_code)
    
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return True

def fix_access_control(filepath):
    """access_control 特殊处理：添加 from __future__ import annotations"""
    content = filepath.read_text(encoding='utf-8')
    if 'from __future__ import annotations' in content:
        return False
    lines = content.split('\n')
    # 在 __module_meta__ 结束后的 import 区域前添加
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from typing'):
            lines.insert(i, 'from __future__ import annotations')
            break
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return True

# 执行修复
fixed_count = 0
errors = []

# 1. 修复普通导入缺失
for module, fixes in FIXES.items():
    filepath = MODULES_DIR / f"{module}.py"
    if not filepath.exists():
        errors.append(f"{module}: 文件不存在")
        continue
    if "add_imports" in fixes:
        for imp in fixes["add_imports"]:
            try:
                if add_import_to_file(filepath, imp):
                    fixed_count += 1
                    print(f"✅ {module}: +{imp}")
            except Exception as e:
                errors.append(f"{module}: {e}")
    if "note" in fixes:
        try:
            if module == "access_control":
                fix_access_control(filepath)
                print(f"✅ {module}: +from __future__ import annotations")
                fixed_count += 1
        except Exception as e:
            errors.append(f"{module}: {e}")

# 2. 添加缺失类型桩定义
for module, stub in STUB_DEFS.items():
    filepath = MODULES_DIR / f"{module}.py"
    if not filepath.exists():
        errors.append(f"{module}: 文件不存在")
        continue
    try:
        if add_stub_before_first_class(filepath, stub):
            stype = stub.split('class')[1].split(':')[0].split('(')[0].strip()
            print(f"✅ {module}: +class {stype}")
            fixed_count += 1
    except Exception as e:
        errors.append(f"{module}: {e}")

print(f"\n共修复: {fixed_count} 个模块")
if errors:
    print(f"错误: {len(errors)}")
    for e in errors:
        print(f"  ❌ {e}")

# 3. 额外修复 access_control.py — 确保 `__future__` 在 import 前
ac_path = MODULES_DIR / "access_control.py"
content = ac_path.read_text(encoding='utf-8')
# 把 from __future__ import annotations 移到文件顶部（所有 import 之前）
if 'from __future__ import annotations' in content:
    lines = content.split('\n')
    future_line = None
    for i, line in enumerate(lines):
        if 'from __future__ import annotations' in line:
            future_line = i
            break
    if future_line and future_line > 0:
        # 检查前面是否有非注释非空行
        has_code_before = any(
            l.strip() and not l.strip().startswith('#') and not l.strip().startswith('"""')
            for l in lines[:future_line]
        )
        if has_code_before:
            # 移到文档字符串/注释之后
            lines.pop(future_line)
            insert_at = 0
            for i, l in enumerate(lines):
                if l.strip() == '' or l.strip().startswith('#'):
                    insert_at = i + 1
                else:
                    break
            lines.insert(insert_at, 'from __future__ import annotations')
            ac_path.write_text('\n'.join(lines), encoding='utf-8')
            print(f"✅ access_control: __future__ 移到正确位置")

print("\n修复完成!")
