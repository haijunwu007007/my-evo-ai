"""模块质量合规测试 — 确保每个模块达到最低标准"""
import pytest
from pathlib import Path
import re

MODULES_DIR = Path(__file__).parent.parent / "modules"

def get_all_modules():
    return sorted(MODULES_DIR.glob("*.py"))

class TestModuleCompliance:
    """所有模块必须满足的基本条件"""

    def test_no_empty_modules(self):
        """不允许空模块（允许已知的shim）"""
        small = []
        shims = {"_system_coordinator_v3_shim.py"}
        for f in get_all_modules():
            if f.name in shims:
                continue
            content = f.read_text(encoding="utf-8", errors="replace")
            if len(content) < 500:
                small.append(f.name)
        assert len(small) == 0, f"空壳模块: {small}"

    def test_all_have_enterprise_base(self):
        """大模块应继承EnterpriseModule"""
        missing = []
        skip = {"trending_pipeline.py"}
        for f in get_all_modules():
            if f.name in skip:
                continue
            content = f.read_text(encoding="utf-8", errors="replace")
            if len(content) > 5000 and "EnterpriseModule" not in content:
                missing.append(f.name)
        assert len(missing) == 0, f"大模块未继承EnterpriseModule: {missing[:10]}"

    def test_docstring_coverage(self):
        """超大模块(>30KB)必须有docstring"""
        missing = []
        for f in get_all_modules():
            content = f.read_text(encoding="utf-8", errors="replace")
            if len(content) > 30000:
                lines = content.strip().splitlines()
                if not lines or not (lines[0].startswith('"""') or lines[0].startswith("'''")):
                    missing.append(f.name)
        assert len(missing) == 0, f"超大模块缺少docstring({len(missing)}): {missing[:10]}"

    def test_import_format(self):
        """模块import靠前（特殊结构跳过）"""
        skip = {"dependency_manager.py"}
        for f in get_all_modules():
            if f.name in skip:
                continue
            content = f.read_text(encoding="utf-8", errors="replace")
            if len(content) < 2000:
                continue
            lines = content.splitlines()
            import_lines = [i for i, l in enumerate(lines) if l.startswith(("import ", "from "))]
            if import_lines:
                last_import = max(import_lines)
                total = len(lines)
                assert last_import < total * 0.4, f"{f.name}: import在文件后半部(line {last_import}/{total})"
