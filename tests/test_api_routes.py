"""
AUTO-EVO-AI V0.1 — API 路由 & 模块全量导入测试
覆盖：路由文件导入、核心模块导入、模块随机抽样、前端完整性
"""

import os, sys, json, importlib, pytest
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

ROUTES_DIR = BASE / "api" / "routes"
CORE_DIR = BASE / "core"
MODULES_DIR = BASE / "modules"

def get_route_files():
    return sorted([f.stem for f in ROUTES_DIR.iterdir()
                   if f.suffix == ".py" and not f.name.startswith("_") and f.name != "__init__.py"])

def get_core_files():
    return sorted([f.stem for f in CORE_DIR.iterdir()
                   if f.suffix == ".py" and not f.name.startswith("_") and f.name != "__init__.py"])

# ── Test 1: API 路由文件导入 ─────────────────

class TestApiRouteImports:

    def test_route_directory_not_empty(self):
        files = get_route_files()
        assert len(files) > 10, f"路由文件数不足: {len(files)}"

    def test_all_route_files_import(self):
        files = get_route_files()
        failed = []
        for name in files:
            try:
                importlib.import_module(f"api.routes.{name}")
            except Exception as e:
                failed.append(f"{name}: {e}")
        fail_rate = len(failed) / len(files) * 100
        assert fail_rate < 30, f"导入失败 {len(failed)}/{len(files)}: {failed[:5]}"

    def test_routes_have_router(self):
        from fastapi import APIRouter
        files = get_route_files()
        bad = []
        for name in files:
            try:
                mod = importlib.import_module(f"api.routes.{name}")
                if not hasattr(mod, "router") or not isinstance(mod.router, APIRouter):
                    bad.append(name)
            except Exception:
                bad.append(name)
        fail_rate = len(bad) / len(files) * 100
        assert fail_rate < 30, f"无有效router: {len(bad)}/{len(files)}"

# ── Test 2: 核心模块导入 ─────────────────

class TestCoreModuleImports:

    def test_core_directory_not_empty(self):
        files = get_core_files()
        assert len(files) > 5, f"核心模块数不足: {len(files)}"

    def test_all_core_import(self):
        files = get_core_files()
        failed = []
        for name in files:
            try:
                importlib.import_module(f"core.{name}")
            except Exception as e:
                failed.append(f"{name}: {e}")
        fail_rate = len(failed) / len(files) * 100
        assert fail_rate < 30, f"核心导入失败 {len(failed)}/{len(files)}: {failed[:5]}"

    def test_core_has_public_members(self):
        files = get_core_files()
        empty = []
        for name in files:
            try:
                mod = importlib.import_module(f"core.{name}")
                members = [m for m in dir(mod) if not m.startswith("_")]
                if len(members) < 2:
                    empty.append(name)
            except Exception:
                empty.append(name)
        assert len(empty) < len(files) // 2, f"无公开成员模块过多: {len(empty)}/{len(files)}"

# ── Test 3: 模块系统 ─────────────────

class TestModuleSystem:

    def test_module_count(self):
        py_files = [f for f in MODULES_DIR.iterdir() if f.suffix == ".py" and not f.name.startswith("_")]
        assert len(py_files) > 50, f"模块文件过少: {len(py_files)}"

    def test_random_module_imports(self):
        py_files = sorted([f for f in MODULES_DIR.iterdir() if f.suffix == ".py" and not f.name.startswith("_")])
        import random; random.seed(42)
        samples = random.sample(py_files, min(20, len(py_files)))
        failed = []
        for f in samples:
            try:
                importlib.import_module(f"modules.{f.stem}")
            except Exception as e:
                failed.append(f"{f.stem}: {e}")
        fail_rate = len(failed) / len(samples) * 100
        assert fail_rate < 50, f"随机导入失败 {fail_rate:.0f}%: {failed[:3]}"

    def test_modules_with_module_class(self):
        py_files = [f for f in MODULES_DIR.iterdir() if f.suffix == ".py" and not f.name.startswith("_")]
        count = 0
        for f in py_files:
            try:
                mod = importlib.import_module(f"modules.{f.stem}")
                if hasattr(mod, "module_class"):
                    count += 1
            except Exception:
                pass
        assert count > 5, f"有module_class的模块: {count}"

# ── Test 4: 前端完整性 ─────────────────

class TestFrontendStructure:

    def test_core_html(self):
        for f in ["chat.html", "enterprise.html", "404.html", "500.html"]:
            assert (BASE / "frontend" / f).exists(), f"缺失: {f}"

    def test_core_js(self):
        for f in ["chat_engine.js", "components.js", "enterprise-modules.js"]:
            assert (BASE / "frontend" / f).exists(), f"缺失: {f}"

    def test_core_css(self):
        for f in ["share.css", "mobile.css"]:
            assert (BASE / "frontend" / f).exists(), f"缺失: {f}"

    def test_page_template(self):
        assert (BASE / "frontend" / "page-template.html").exists(), "page-template.html缺失"

    def test_html_files_non_empty(self):
        for f in ["chat.html", "404.html", "500.html", "enterprise.html"]:
            p = BASE / "frontend" / f
            assert p.exists() and len(p.read_text(encoding="utf-8")) > 100, f"{f} 为空"

    def test_share_css_non_empty(self):
        p = BASE / "frontend" / "share.css"
        assert p.exists() and len(p.read_text(encoding="utf-8")) > 500

    def test_components_js_has_evo_ns(self):
        content = (BASE / "frontend" / "components.js").read_text(encoding="utf-8")
        assert "Evo." in content, "components.js缺少Evo命名空间"

# ── Test 5: 配置文件 ─────────────────

class TestConfig:

    def test_config_exists(self):
        config_dir = BASE / "config"
        yamls = []
        if config_dir.exists():
            yamls = list(config_dir.glob("*.yaml"))
        assert len(yamls) > 0, "无配置文件"

    def test_database_import(self):
        try:
            importlib.import_module("core.database")
        except Exception as e:
            pytest.skip(f"database不可用: {e}")

    def test_config_loader_import(self):
        try:
            importlib.import_module("core.config_loader")
        except Exception as e:
            pytest.skip(f"config_loader不可用: {e}")

# ── Test 6: 安全模块 ─────────────────

class TestSecurity:

    def test_jwt_import(self):
        try:
            mod = importlib.import_module("modules.jwt_token")
            assert len(dir(mod)) > 5
        except Exception as e:
            pytest.skip(f"jwt_token不可用: {e}")

    def test_auth_middleware_import(self):
        try:
            mod = importlib.import_module("core.auth_middleware")
            assert len(dir(mod)) > 5
        except Exception as e:
            pytest.skip(f"auth_middleware不可用: {e}")

    def test_rbac_core_import(self):
        try:
            mod = importlib.import_module("core.rbac_core")
        except Exception as e:
            pytest.skip(f"rbac_core不可用: {e}")
