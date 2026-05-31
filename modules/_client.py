"""
AUTO-EVO-AI V0.1 — 真实外部依赖客户端
供所有模块调用真实 HTTP/DB/API，替换模拟数据
"""
import os, json, logging, time
from typing import Any

logger = logging.getLogger("evo.client")

class RealClient:
    """真实外部依赖统一入口"""

    def __init__(self):
        self._session = None
        self._cache = {}

    def http_get(self, url: str, headers: dict = None, timeout: int = 10) -> dict:
        try:
            import requests
            h = headers or {}
            h.setdefault("User-Agent", "AUTO-EVO-AI/0.1")
            r = requests.get(url, headers=h, timeout=timeout)
            r.raise_for_status()
            return {"success": True, "status": r.status_code, "data": r.json() if r.text else {}}
        except ImportError:
            return {"success": False, "error": "requests not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def http_post(self, url: str, data: dict = None, headers: dict = None, timeout: int = 10) -> dict:
        try:
            import requests
            h = headers or {}
            h.setdefault("User-Agent", "AUTO-EVO-AI/0.1")
            r = requests.post(url, json=data, headers=h, timeout=timeout)
            r.raise_for_status()
            return {"success": True, "status": r.status_code, "data": r.json() if r.text else {}}
        except ImportError:
            return {"success": False, "error": "requests not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def sqlite_query(self, db_path: str, sql: str, params: tuple = ()) -> dict:
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(sql, params)
            if sql.strip().upper().startswith("SELECT"):
                rows = [dict(r) for r in cur.fetchall()]
            else:
                conn.commit()
                rows = {"affected": cur.rowcount}
            conn.close()
            return {"success": True, "data": rows}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def file_read(self, path: str) -> dict:
        try:
            if not os.path.isfile(path):
                return {"success": False, "error": "file not found"}
            with open(path, encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "data": content, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def file_write(self, path: str, content: str) -> dict:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def exec_cmd(self, cmd: str, timeout: int = 30) -> dict:
        try:
            import subprocess
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {
                "success": r.returncode == 0,
                "stdout": r.stdout[:2000],
                "stderr": r.stderr[:1000],
                "returncode": r.returncode,
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def cache_get(self, key: str, ttl: int = 300) -> Any:
        entry = self._cache.get(key)
        if entry and time.time() - entry["ts"] < ttl:
            return entry["value"]
        return None

    def cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = {"value": value, "ts": time.time()}

    def cache_clear(self) -> None:
        self._cache.clear()

_client = None
def get_client() -> RealClient:
    global _client
    if _client is None:
        _client = RealClient()
    return _client

# ── 统一 HTTP 客户端 ──────────────────────────────────

def configure_requests():
    """统一配置全局 requests：重试/超时/连接池/UA

    调用后，所有 ``import requests; requests.get(...)``
    自动走统一 Session，无需修改任何模块代码。
    """
    import requests as _req
    from requests.adapters import HTTPAdapter
    import urllib3

    _session = _req.Session()
    _session.headers.update({"User-Agent": "AUTO-EVO-AI/0.1 (+https://github.com/haijunwu007007/my-evo-ai)"})
    _retry = urllib3.Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}),
    )
    _adapter = HTTPAdapter(max_retries=_retry, pool_connections=20, pool_maxsize=100)
    _session.mount("https://", _adapter)
    _session.mount("http://", _adapter)

    # 替换 requests 模块的全局函数
    for _method in ("get", "post", "put", "delete", "head", "options", "patch", "request"):
        setattr(_req, _method, getattr(_session, _method))
    _req.session = lambda: _session

    logger.info("[CLIENT] requests 已统一配置 (3重试/连接池/UA)")
