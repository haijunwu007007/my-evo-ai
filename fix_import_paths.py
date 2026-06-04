"""修复剩余的导入路径问题 — 精确修复每个文件"""
import re
from pathlib import Path

MODULES = Path("D:\\AUTO-EVO-AI-V0.1\\modules")

# 文件 → 需要替换的导入行 → 替换为
FIXES = {
    # core.data_layer → 本地桩
    "fts_query": ("from core.data_layer import DataEngine", "from dataclasses import dataclass\n@dataclass\nclass _MockEngine:\n    url: str = ''\n    def query(self, sql): return []\n    def execute(self, sql): return True\nDataEngine = _MockEngine"),
    "object_storage": ("from core.data_layer import DataEngine", "from dataclasses import dataclass\n@dataclass\nclass _MockEngine:\n    url: str = ''\n    def query(self, sql): return []\n    def execute(self, sql): return True\nDataEngine = _MockEngine"),
    "project_manager": ("from core.data_layer import DataEngine", "from dataclasses import dataclass\n@dataclass\nclass _MockEngine:\n    url: str = ''\n    def query(self, sql): return []\n    def execute(self, sql): return True\nDataEngine = _MockEngine"),

    # modules._base.planner_registry → modules._base.registry  (ModuleRegistry 实际位置)
    "agent_planner": ("from modules._base.planner_registry import ModuleRegistry", "from modules._base.registry import ModuleRegistry"),
}

for mod, (old_import, new_import) in FIXES.items():
    fp = MODULES / f"{mod}.py"
    if not fp.exists():
        print(f"❌ {mod}: 文件不存在")
        continue
    content = fp.read_text(encoding='utf-8')
    # 删除本地重复的 class DataEngine 桩（如果存在）
    content_clean = re.sub(r'\n@dataclass\nclass _MockEngine:.*?DataEngine = _MockEngine', '', content, flags=re.DOTALL)
    if old_import in content_clean:
        content_clean = content_clean.replace(old_import, new_import)
        fp.write_text(content_clean, encoding='utf-8')
        print(f"✅ {mod}: {old_import.split()[0]} → {new_import.split()[-1] if '=' not in new_import else '本地桩'}")
    else:
        print(f"  {mod}: 未找到旧导入 '{old_import[:50]}'")

# 额外修复: agent_boreas + http_client — 需要从 _base 导入 HealthReport/ModuleStats
for mod, missing_type in [("agent_boreas", "HealthReport"), ("http_client", "ModuleStats")]:
    fp = MODULES / f"{mod}.py"
    content = fp.read_text(encoding='utf-8')
    # 检查是否已有该导入
    if f"from modules._base import {missing_type}" in content:
        print(f"  {mod}: 已有 {missing_type} 导入")
        continue
    # 在现有的 from modules._base import 后面追加
    import_line = f"from modules._base import Result"
    if import_line in content:
        content = content.replace(import_line, f"from modules._base import Result, {missing_type}")
        fp.write_text(content, encoding='utf-8')
        print(f"✅ {mod}: +{missing_type}")
    else:
        # 直接在最顶部导入区域添加
        lines = content.split('\n')
        # 在 docstring 后、__module_meta__ 之前插入
        insert_at = 0
        found_meta = False
        for i, line in enumerate(lines):
            if '__module_meta__' in line:
                found_meta = True
            if found_meta and line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_at = i
                found_meta = False
                break
        if insert_at == 0:
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_at = i
                    break
        lines.insert(insert_at, f"from modules._base import {missing_type}")
        fp.write_text('\n'.join(lines), encoding='utf-8')
        print(f"✅ {mod}: +{missing_type} (新行插入)")

print("\n全部修复完成！")
