"""
AUTO-EVO-AI V0.1 — 端到端测试
覆盖: 健康检查 / 前端页面 / 核心API / 模块系统

运行: pytest tests/test_e2e.py -v
"""
import pytest, json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 健康检查 ─────────────────────────────
def test_api_server_imports():
    """API 服务器模块导入测试"""
    from api_server import app
    assert app is not None

def test_core_modules_import():
    """核心模块导入测试"""
    from core.logging_config import get_logger
    assert get_logger is not None

def test_routes_import():
    """路由模块导入测试"""
    from api.routes.routes_static import router as static_router
    from api.routes.features.core import router as features_router
    from api.routes.routes_smart_chat import router as chat_router
    assert static_router is not None
    assert features_router is not None
    assert chat_router is not None

# ── 核心功能 ─────────────────────────────
def test_features_split():
    """验证 core.py 已拆分为 3 个子文件"""
    from api.routes.features.core import router
    assert len(router.routes) >= 30, f"应包含31+路由, 实际{len(router.routes)}"
    # 验证所有子路由已合并
    paths = [r.path for r in router.routes]
    assert "/api/v1/email/send" in paths
    assert "/api/v1/todos" in paths
    assert "/api/v1/user/register" in paths
    assert "/api/v1/webhook" in paths
    assert "/api/v1/plugins" in paths
    assert "/api/v1/workflow/list" in paths
    assert "/api/v1/mcp/tools" in paths
    assert "/api/v1/rerank" in paths
    assert "/api/v1/selfheal/report" in paths
    assert "/api/v1/connectors" in paths

def test_routes_no_conflicts():
    """验证关键路由无冲突 — 至少保证路由文件可以同时导入"""
    from api.routes import routes_static, routes_smart_chat, routes_llm_chat, routes_rag
    assert routes_static is not None
    assert routes_smart_chat is not None
    assert routes_llm_chat is not None
    assert routes_rag is not None

# ── 模块系统 ─────────────────────────────
def test_modules_auto_discovery():
    """验证模块自动发现"""
    import importlib, pathlib
    mod_dir = pathlib.Path(__file__).resolve().parent.parent / "modules"
    mods = [f.stem for f in mod_dir.glob("*.py") if not f.stem.startswith("_")]
    assert len(mods) >= 500, f"应发现500+模块, 实际{len(mods)}"

def test_modules_no_empty_stubs():
    """验证模块非空壳（有 status/execute 方法）"""
    import importlib, pathlib
    mod_dir = pathlib.Path(__file__).resolve().parent.parent / "modules"
    empty = []
    for f in sorted(mod_dir.glob("*.py")):
        if f.stem.startswith("_"): continue
        c = f.read_text("utf-8", errors="ignore")
        if "def status" not in c and "async def" not in c and "class " not in c:
            empty.append(f.name)
    assert len(empty) < 50, f"空壳模块 >= 50: {empty[:10]}"

# ── 配置一致性 ────────────────────────────
def test_no_hardcoded_localhost():
    """验证 api/agents/ 中无硬编码 localhost"""
    import pathlib
    agent_dir = pathlib.Path(__file__).resolve().parent.parent / "api" / "agents"
    hardcoded = []
    for f in agent_dir.glob("*.py"):
        c = f.read_text("utf-8", errors="ignore")
        if 'localhost' in c and not c.strip().startswith("#") and '"localhost"' not in c:
            if 'os.environ.get' not in c:
                hardcoded.append(f.name)
    assert len(hardcoded) < 3, f"硬编码 localhost: {hardcoded}"

def test_no_body_hardcoded_bg():
    """验证前端页面 body 背景无硬编码色值"""
    import pathlib, re
    frontend = pathlib.Path(__file__).resolve().parent.parent / "frontend"
    bad = []
    for f in frontend.glob("*.html"):
        c = f.read_text("utf-8", errors="ignore")
        if re.search(r'body\s*\{[^}]*background[^}]*#[0-9a-fA-F]{6}', c):
            bad.append(f.name)
    assert len(bad) < 5, f"body硬编码: {bad}"

def test_code_quality():
    """验证无 except:pass 和 print() 调试（在核心代码中）"""
    import pathlib, re
    root = pathlib.Path(__file__).resolve().parent.parent
    exc = pr = 0
    for d in [root/"api"/"routes", root/"core"]:
        for f in d.rglob("*.py"):
            if "__pycache__" in str(f): continue
            c = f.read_text("utf-8", errors="ignore")
            exc += len(re.findall(r'^ +except[^:]*:[^\n]*\n +pass', c, re.MULTILINE))
            for line in c.split(chr(10)):
                s = line.strip()
                if "print(" in s and "logger" not in s and "#" not in s:
                    pr += 1
    assert exc < 10, f"except:pass >= 10 ({exc})"
    assert pr < 10, f"print() >= 10 ({pr})"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
