"""AUTO-EVO-AI V0.1 — 535模块合规测试"""
import os, sys, pytest, ast
from pathlib import Path
from typing import List
BASE = Path(__file__).parent.parent; sys.path.insert(0, str(BASE))
EXCLUDE_NO_CLASS = {"nl_workflow.py", "trending_pipeline.py"}
EXCLUDE_CB = EXCLUDE_NO_CLASS | {"atom_code.py", "key_insights.py", "langfuse_monitor.py",
    "trigger_engine.py", "webhook_handler.py", "workflow_manager.py"}

def get_py_files() -> list[Path]:
    d = BASE / "modules"; return sorted([f for f in d.iterdir() if f.suffix == ".py" and not f.name.startswith("_")])

@pytest.mark.compliance
class TestModuleCompliance:
    @pytest.fixture(autouse=True)
    def setup(self): self.all_files = get_py_files()

    def test_all_have_meta(self):
        missing = []
        for f in self.all_files:
            if "__module_meta__" not in f.read_text(encoding="utf-8"): missing.append(f.name)
        assert len(missing) == 0, f"{len(missing)} missing __module_meta__: {missing[:5]}"

    def test_no_stubs_remain(self):
        stubs = []
        for f in self.all_files:
            c = f.read_text(encoding="utf-8")
            if '"grade": "Stub"' in c or "'grade': 'Stub'" in c: stubs.append(f.name)
        assert len(stubs) == 0, f"Still {len(stubs)} stubs: {stubs[:10]}"

    def test_valid_syntax(self):
        invalid = []
        for f in self.all_files:
            try: ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as e: invalid.append((f.name, str(e)))
        assert len(invalid) == 0

    def test_module_count(self):
        assert len(self.all_files) >= 450

    def test_no_dup_ids(self):
        ids = []
        for f in self.all_files:
            for line in f.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if 'MODULE_ID = "' in line or "MODULE_ID = '" in line:
                    mid = line.split("=")[1].strip().strip('"').strip("'")
                    ids.append(mid)
        dup = [i for i in set(ids) if ids.count(i) > 1]
        assert len(dup) == 0, f"Duplicates: {dup}"

    def test_all_inherit_enterprise(self):
        bad = []
        for f in self.all_files:
            if f.name in EXCLUDE_NO_CLASS: continue
            c = f.read_text(encoding="utf-8")
            if "EnterpriseModule" not in c and "class " in c: bad.append(f.name)
        assert len(bad) == 0, f"Not inherited: {bad}"

    def test_circuit_breaker_mixin_present(self):
        missing = []
        for f in self.all_files:
            if f.name in EXCLUDE_CB: continue
            c = f.read_text(encoding="utf-8")
            if "class " in c and "EnterpriseModule" in c and "CircuitBreakerMixin" not in c:
                missing.append(f.name)
        assert len(missing) == 0, f"No CB Mixin: {missing[:5]}"

    def test_file_size_minimum(self):
        small = [(f.name, f.stat().st_size) for f in self.all_files if f.stat().st_size < 500]
        assert len(small) == 0, f"Too small: {small[:5]}"
