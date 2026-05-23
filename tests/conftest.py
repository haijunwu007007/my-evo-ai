# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 — 测试基础设施
上市公司级：pytest fixtures、mock 服务、共享工具
"""
import os, sys, json, time, http.client, pytest
from pathlib import Path
from typing import Dict, Any, Optional, List

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

HOST = os.environ.get("TEST_HOST", "localhost")
PORT = int(os.environ.get("TEST_PORT", "8765"))
API_KEY = os.environ.get("TEST_API_KEY", "")


# ── HTTP 请求工具 ──────────────────────────────────────────

def api_get(path: str, timeout: int = 10) -> tuple:
    """GET 请求"""
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    headers = {"Content-Type": "application/json"}
    if API_KEY: headers["X-API-Key"] = API_KEY
    c.request("GET", path, headers=headers)
    r = c.getresponse()
    data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}


def api_post(path: str, body: dict = None, timeout: int = 10) -> tuple:
    """POST 请求"""
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    headers = {"Content-Type": "application/json"}
    if API_KEY: headers["X-API-Key"] = API_KEY
    c.request("POST", path, body=json.dumps(body) if body else None, headers=headers)
    r = c.getresponse()
    data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}


def api_put(path: str, body: dict = None) -> tuple:
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if API_KEY: headers["X-API-Key"] = API_KEY
    c.request("PUT", path, body=json.dumps(body) if body else None, headers=headers)
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}


def api_delete(path: str) -> tuple:
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if API_KEY: headers["X-API-Key"] = API_KEY
    c.request("DELETE", path, headers=headers)
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}


# ── 模块加载工具 ──────────────────────────────────────────

def import_module_class(module_name: str):
    """动态导入模块并获取 module_class"""
    try:
        mod_path = f"modules.{module_name.replace('.py', '')}"
        import importlib
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, 'module_class', None)
        return cls, mod
    except Exception as e:
        return None, None


def get_all_module_files() -> List[Path]:
    """获取所有模块文件路径"""
    modules_dir = BASE / "modules"
    return sorted([f for f in modules_dir.iterdir() if f.suffix == ".py" and not f.name.startswith("_")])


# ── pytest fixtures ──────────────────────────────────

@pytest.fixture(scope="session")
def server_status():
    """检查 API 服务是否运行"""
    try:
        status, data = api_get("/api/status")
        assert status == 200, f"API not running: {status}"
        return data
    except Exception as e:
        pytest.skip(f"API 服务未运行: {e}")
        return {}


@pytest.fixture(scope="session")
def all_module_paths() -> List[Path]:
    return get_all_module_files()


@pytest.fixture
def sample_jwt_payload():
    return {"claims": {"sub": "test_user", "roles": ["admin"]}}


@pytest.fixture
def sample_rbac_data():
    return {"user_id": "test_user", "role_id": "admin"}
