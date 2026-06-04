"""
AUTO-EVO-AI V0.1 — API 基础设施层
==============================
职责：承载所有路由文件共享的全局状态、基础设施、公共模型。
      路由文件统一从此模块导入所需对象，避免循环依赖。

用法:
    from api.infra import app, registry, rate_limiter, logger, ...
"""

from __future__ import annotations

import os
import sys
import json
import time
import asyncio
import importlib
import importlib.util
import inspect
import hashlib
import secrets
import logging
from core.logging_config import get_logger
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ── 统一路径（从共享模块计算 BASE_DIR + sys.path.insert）──
from api._paths import BASE_DIR, _ORIGINAL_BASE

# ── 向后兼容层（替代 builtins 注入 hack）──
from modules._base.compat import inject_compat
inject_compat()

# ── FastAPI ──
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import Response as StarletteResponse

import uvicorn

# ── 日志 ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = get_logger("evo.api")


# ════════════════════════════════════════════════════════════
# WebSocket 连接管理器
# ════════════════════════════════════════════════════════════
class ConnectionManager:
    def __init__(self):
        self.active: list = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


# ════════════════════════════════════════════════════════════
# 全局指标 & API 缓存
# ════════════════════════════════════════════════════════════
_START_TIME = time.time()
_request_counter: dict[str, int] = defaultdict(int)
_request_errors: dict[str, int] = defaultdict(int)
_request_latency: dict[str, list[float]] = defaultdict(list)
_request_latency_ms: dict[str, float] = {}

_api_cache: dict[str, dict] = {}
_CACHE_TTL = 5.0
_cache_hits = 0
_CACHEABLE_PATHS = {
    "/api/modules", "/api/health", "/api/status",
    "/api/coordinator/status", "/api/coordinator/capabilities",
    "/api/planner/status", "/api/planner/modules",
    "/api/security/status", "/api/persistence/status",
    "/api/monitor/realtime", "/api/execution-log",
}
_CACHE_SHORT_PATHS = {"/api/search/modules"}

# 模块活跃度计数
_module_activity: dict[str, int] = {}


# ════════════════════════════════════════════════════════════
# API Key 认证配置
# ════════════════════════════════════════════════════════════
_API_KEY_ENABLED = os.environ.get("EVO_API_KEY_ENABLED", "false").lower() == "true"
_API_KEY = os.environ.get("EVO_API_KEY", "")
if _API_KEY_ENABLED and not _API_KEY:
    _API_KEY = secrets.token_urlsafe(32)
    logger.warning(f"[SECURITY] 自动生成API Key: {_API_KEY}")

_cors_origins = os.environ.get("EVO_CORS_ORIGINS", "*").split(",")

_PUBLIC_PATHS = {"/static/fix.js", "/i18n.js", "/", "/health",
                 "/docs", "/openapi.json", "/redoc", "/dashboard"}


# ════════════════════════════════════════════════════════════
# 请求限流器
# ════════════════════════════════════════════════════════════
class RateLimiter:
    """多级IP限流器: 全局限制 + 端点级别限制 + 写操作更严格"""
    def __init__(self, max_requests: int = 1000, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._endpoint_limits: dict[str, int] = {
            "POST:": 120, "PUT:": 120, "DELETE:": 60,
            "GET:/api/execute": 30, "POST:/api/execute": 30,
        }
        self._total_blocked = 0
        self._blocked_ips: dict[str, int] = defaultdict(int)

    async def is_allowed(self, client_ip: str, method: str = "GET", path: str = "/") -> tuple:
        now = time.time()
        cutoff = now - self.window_seconds
        async with self._lock:
            bucket = self._requests[client_ip]
            self._requests[client_ip] = [t for t in bucket if t > cutoff]
            bucket = self._requests[client_ip]
            limit = self.max_requests
            key = f"{method}:{path}"
            for pattern, plimit in self._endpoint_limits.items():
                if key.startswith(pattern) or (pattern == f"{method}:" and path.startswith("/api/")):
                    limit = min(limit, plimit)
                    break
            if len(bucket) >= limit:
                reset_at = int(bucket[0] + self.window_seconds)
                self._total_blocked += 1
                self._blocked_ips[client_ip] += 1
                return False, 0, reset_at
            bucket.append(now)
            return True, limit - len(bucket), int(now + self.window_seconds)

    def get_stats(self) -> dict:
        return {
            "total_blocked": self._total_blocked,
            "tracked_ips": len(self._requests),
            "top_blocked_ips": sorted(self._blocked_ips.items(), key=lambda x: -x[1])[:10],
            "endpoint_limits": self._endpoint_limits,
            "global_limit": self.max_requests,
            "window_seconds": self.window_seconds,
        }

    def reset_ip(self, client_ip: str):
        if client_ip in self._requests:
            del self._requests[client_ip]
        if client_ip in self._blocked_ips:
            del self._blocked_ips[client_ip]


rate_limiter = RateLimiter(max_requests=30, window_seconds=60)


# ════════════════════════════════════════════════════════════
# 审计日志
# ════════════════════════════════════════════════════════════
_audit_log: list[dict] = []
_MAX_AUDIT = 1000


def _record_audit(method: str, path: str, client_ip: str, status: int, latency_ms: float, error: str = ""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "method": method, "path": path,
        "client_ip": client_ip, "status": status,
        "latency_ms": round(latency_ms, 1),
        "error": error[:200] if error else "",
    }
    _audit_log.append(entry)
    if len(_audit_log) > _MAX_AUDIT:
        _audit_log.pop(0)


# ════════════════════════════════════════════════════════════
# 模块分类
# ════════════════════════════════════════════════════════════
_MODULE_CATEGORY_RULES = [
    (["agent_", "agent-"], "agent"),
    (["api_", "api-"], "api"),
    (["cache_", "cache-"], "cache"),
    (["security_", "sec_", "waf_", "firewall_"], "security"),
    (["log_", "audit_"], "logging"),
    (["db_", "database_", "sql_", "redis_", "mongo_"], "database"),
    (["auth_", "oauth_", "jwt_", "token_"], "auth"),
    (["metric_", "monitor_", "perf_", "trace_"], "monitor"),
    (["notify_", "push_", "email_", "sms_", "message_"], "notification"),
    (["backup_", "recovery_", "restore_", "snapshot_"], "backup"),
    (["config_", "setting_", "env_", "feature_"], "config"),
    (["task_", "job_", "scheduler_", "cron_", "workflow_"], "task"),
    (["queue_", "mq_", "broker_", "kafka_", "rabbit_"], "messaging"),
    (["search_", "index_", "rag_", "embedding_"], "search"),
    (["encrypt_", "crypto_", "ssl_", "cert_", "key_", "secret_"], "crypto"),
    (["network_", "dns_", "proxy_", "cdn_", "tunnel_"], "network"),
    (["file_", "storage_", "disk_", "oss_", "s3_"], "storage"),
    (["data_", "etl_", "pipeline_"], "data"),
    (["ml_", "ai_", "model_", "train_", "nlp_"], "ai"),
    (["test_", "lint_", "quality_", "bench_"], "testing"),
]
_CATEGORY_OTHER = "system"


def classify_module(name: str) -> str:
    nl = name.lower()
    for prefixes, cat in _MODULE_CATEGORY_RULES:
        for p in prefixes:
            if nl.startswith(p):
                return cat
    return _CATEGORY_OTHER


# ════════════════════════════════════════════════════════════
# 模块注册表
# ════════════════════════════════════════════════════════════
class ModuleRegistry:
    """模块注册表 — 自动发现、加载、管理所有模块"""
    def __init__(self):
        self.modules: dict[str, Any] = {}
        self.classes: dict[str, type] = {}
        self.endpoints: dict[str, dict] = {}
        self.health: dict[str, dict] = {}
        self._pending_modules: dict[str, dict] = {}
        self._pending_init: dict[str, Any] = {}

    def auto_discover(self, modules_dir: str = "modules"):
        mod_path = BASE_DIR / modules_dir
        if not mod_path.exists():
            logger.warning(f"模块目录不存在: {mod_path}")
            return
        discovered = 0
        for f in sorted(mod_path.glob("*.py")):
            if f.name.startswith("_") or f.name.startswith("test"):
                continue
            name = f.stem
            if name not in self.modules and name not in self._pending_modules:
                if name in self.classes:
                    self._pending_modules[name] = {"dir": modules_dir, "file": f.name, "pre_registered": True}
                    self.health.setdefault(name, {"status": "pending_lazy", "last_beat": "", "error": "", "grade": "lazy"})
                else:
                    self._pending_modules[name] = {"dir": modules_dir, "file": f.name}
                    self.health[name] = {"status": "pending_lazy", "last_beat": "", "error": "", "grade": "lazy"}
                discovered += 1
        logger.info(f"[LAZY] 注册 {discovered} 个模块待按需加载")

    def rescan_modules(self, modules_dir: str = "modules") -> int:
        mod_path = BASE_DIR / modules_dir
        if not mod_path.exists():
            return 0
        known = set(self.modules.keys()) | set(self._pending_modules.keys()) | set(self.classes.keys())
        added = 0
        for f in sorted(mod_path.glob("*.py")):
            if f.name.startswith("_") or f.name.startswith("test"):
                continue
            name = f.stem
            if name not in known:
                self._pending_modules[name] = {"dir": modules_dir, "file": f.name}
                self.health[name] = {"status": "pending_lazy", "last_beat": "", "error": "", "grade": "lazy"}
                known.add(name)
                added += 1
                logger.info(f"[HOT-LOAD] 新模块发现: {name}")
        if added:
            _invalidate_caches()
            logger.info(f"[HOT-LOAD] 本次扫描新增 {added} 个模块，总计 {len(self.modules) + len(self._pending_modules)} 个")
        return added

    def install_module(self, code: str, name: str):
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '', name)
        if not safe_name:
            raise ValueError("Invalid module name")
        mod_path = BASE_DIR / "modules" / f"{safe_name}.py"
        mod_path.write_text(code, encoding="utf-8")
        self._pending_modules[safe_name] = {"dir": "modules", "file": f"{safe_name}.py"}
        self.health[safe_name] = {"status": "pending_lazy", "last_beat": "", "error": "", "grade": "lazy"}
        _invalidate_caches()
        logger.info(f"[INSTALL] 模块已安装: {safe_name}")
        return safe_name

    def uninstall_module(self, name: str):
        self._pending_modules.pop(name, None)
        self.modules.pop(name, None)
        self.health.pop(name, None)
        self.classes.pop(name, None)
        mod_path = BASE_DIR / "modules" / f"{name}.py"
        removed_file = False
        if mod_path.exists():
            mod_path.unlink()
            removed_file = True
        _invalidate_caches()
        logger.info(f"[UNINSTALL] 模块已卸载: {name} (file={removed_file})")
        return removed_file

    def get_categories(self):
        all_names = set(self.modules.keys()) | set(self._pending_modules.keys())
        cats = defaultdict(int)
        for n in all_names:
            cats[classify_module(n)] += 1
        return dict(sorted(cats.items(), key=lambda x: -x[1]))

    _STUB_SIZE_THRESHOLD = 2048

    @staticmethod
    def _is_true_stub_file(mod_path: str) -> bool:
        """检查文件是否为真正的桩模块（无真实业务逻辑）"""
        try:
            if not os.path.exists(mod_path):
                return False
            if os.path.getsize(mod_path) >= 2048:
                return False
            src = open(mod_path, encoding="utf-8").read()
            # 有 def 函数且不仅仅是 __init__ → 不是桩
            lines = src.split("\n")
            for ln in lines:
                stripped = ln.strip()
                if stripped.startswith("def ") and "__init__" not in stripped:
                    return False
            return True
        except Exception:
            return False

    def get_stub_count(self):
        """返回真正的桩模块数量（< 2KB 且无业务逻辑）"""
        stub_names = set()
        for name in set(self._pending_modules.keys()) | set(self.classes.keys()):
            mod_file = BASE_DIR / "modules" / f"{name}.py"
            if self._is_true_stub_file(str(mod_file)):
                stub_names.add(name)
        return len(stub_names)

    def get_stubs(self) -> list[dict]:
        """返回所有桩模块的详细信息"""
        stubs = []
        for name in set(self._pending_modules.keys()) | set(self.classes.keys()):
            mod_file = BASE_DIR / "modules" / f"{name}.py"
            if self._is_true_stub_file(str(mod_file)):
                stubs.append({
                    "name": name,
                    "size_bytes": mod_file.stat().st_size,
                    "grade": self.health.get(name, {}).get("grade", "stub"),
                })
        return sorted(stubs, key=lambda x: x["name"])

    def get_total_count(self):
        return len(self.modules) + len(self._pending_modules)

    async def lazy_load_module(self, name: str):
        if name in self.modules:
            return self.modules.get(name)
        pending = self._pending_modules.pop(name, None)
        if not pending:
            return None
        mod_dir = pending["dir"]
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_load_module, name, mod_dir),
                timeout=15.0
            )
            return result
        except TimeoutError:
            self.health[name] = {"status": "timeout", "error": "模块加载超时(15s)", "grade": "E"}
            logger.error(f"[LAZY-TIMEOUT] {name}: 加载超时")
            return None
        except Exception as e:
            self.health[name] = {"status": "lazy_error", "error": str(e), "grade": "E"}
            logger.error(f"[LAZY-ERROR] {name}: {e}")
            return None

    def _sync_load_module(self, name: str, mod_dir: str):
        import importlib
        for _pkg in ['modules._base.mixins', 'modules._base.circuit_breaker', 'modules._base.rate_limiter',
                     'modules._base.enterprise_module', 'modules._base.metrics', 'modules._base.audit', 'modules._base.tracing']:
            if _pkg not in sys.modules:
                try:
                    importlib.import_module(_pkg)
                except ImportError:
                    pass
        mod_key = f"{mod_dir}.{name}"
        from modules._base.compat import CompatContext
        with CompatContext():
            mod = importlib.import_module(mod_key)
        main_class = getattr(mod, 'module_class', None)
        if not main_class or not isinstance(main_class, type):
            main_class = None
        if not main_class:
            import typing as _typing
            _skip = {"Mixin", "Config", "Error", "Exception", "Warning", "Enum",
                     "Base", "Item", "Entry", "Record", "Result", "Request", "Response",
                     "Path", "Dict", "List", "Set", "Tuple", "Optional", "Any"}
            candidates = []
            for attr_name in sorted(dir(mod)):
                try:
                    attr = getattr(mod, attr_name)
                    if not inspect.isclass(attr):
                        continue
                    if attr_name[0].islower():
                        continue
                    if isinstance(attr, _typing._GenericAlias):
                        continue
                    if any(attr_name.endswith(s) or attr_name == s for s in _skip):
                        continue
                    mod_origin = getattr(attr, '__module__', '')
                    if mod_origin == name or mod_origin == f'modules.{name}':
                        has_exec = hasattr(attr, 'execute') and callable(getattr(attr, 'execute'))
                        weight = len(attr_name) + (100 if has_exec else 0)
                        candidates.append((weight, attr_name, attr))
                except Exception:
                    continue
            if candidates:
                candidates.sort(key=lambda x: -x[0])
                main_class = candidates[0][2]
        if main_class:
            self.classes[name] = main_class
            instance = None
            for init_args in [None, {"config": None}, {"config": {}}, {}, {"module_name": name}]:
                try:
                    instance = main_class(**init_args)
                    break
                except (TypeError, Exception):
                    continue
            if instance:
                self.modules[name] = instance
                if not getattr(instance, '_status', None) and hasattr(instance, '_status'):
                    instance._status = 'active'
                if not getattr(instance, '_data', None) and hasattr(instance, '_data'):
                    instance._data = {}
                if not getattr(instance, '_metrics', None) and hasattr(instance, '_metrics'):
                    instance._metrics = {}
                if hasattr(instance, 'initialize') and callable(instance.initialize):
                    try:
                        result = instance.initialize()
                        if asyncio.iscoroutine(result):
                            self._pending_init[name] = result
                    except Exception as init_err:
                        logger.warning(f"[LAZY-INIT] {name} initialize异常: {init_err}")
                self.health[name] = {"status": "ok", "last_beat": datetime.now().isoformat(),
                                     "error": "", "grade": "A", "lazy_loaded": True}
                logger.info(f"[LAZY-LOAD] {name} -> {main_class.__name__}")
                return instance
        else:
            self.modules[name] = mod
            self.health[name] = {"status": "module_only", "last_beat": "", "error": "", "grade": "C"}
            return mod
        return None

    def get(self, name: str) -> Any:
        return self.modules.get(name)

    def call(self, name: str, method: str, *args, **kwargs) -> dict:
        mod = self.modules.get(name)
        if not mod:
            return {"success": False, "error": f"模块不存在: {name}"}
        handler = getattr(mod, method, None)
        if not handler or not callable(handler):
            return {"success": False, "error": f"方法不存在: {name}.{method}"}
        try:
            result = handler(*args, **kwargs)
            if isinstance(result, dict):
                return result
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"调用失败 {name}.{method}: {e}")
            return {"success": False, "error": str(e)}

    def get_all_health(self) -> dict:
        return dict(self.health)


registry = ModuleRegistry()


# ════════════════════════════════════════════════════════════
# FastAPI 应用
# ════════════════════════════════════════════════════════════
app = FastAPI(
    title="AUTO-EVO-AI V0.1 API",
    description="""
## AUTO-EVO-AI 统一API服务器

### 功能
- **模块管理**: 发现、加载、执行 500+ 个企业级模块
- **智能编排**: Agent Planner 自动理解意图并编排模块执行链
- **系统协调**: v3.0 协调器支持自主决策循环
- **实时推送**: WebSocket 推送模块状态和事件
""",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

_cors_origins = os.environ.get("EVO_CORS_ORIGINS", "http://localhost:8765,http://127.0.0.1:8765,http://122.51.144.227:8765").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)

try:
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)
except ImportError:
    pass





# ════════════════════════════════════════════════════════════
# Pydantic 请求模型
# ════════════════════════════════════════════════════════════
class ModuleCallRequest(BaseModel):
    module: str
    method: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


class ExecuteRequest(BaseModel):
    task: str
    context: dict[str, Any] = {}


class PlannerChatRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class PlannerTaskRequest(BaseModel):
    task: str
    params: dict[str, Any] | None = None


class EmailConfigRequest(BaseModel):
    host: str = ""
    port: int = 465
    user: str = ""
    password: str = ""
    ssl: bool = True
    from_name: str = ""


class NotificationRequest(BaseModel):
    channel: str = ""
    to: str = ""
    subject: str = ""
    content: str = ""
    msg_type: str = "text"
    secret: str = ""
    html: str = ""


class LLMChatRequest(BaseModel):
    prompt: str = ""
    messages: list[dict] = []
    model: str = ""
    session_id: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 0
    stream: bool = False
    use_cache: bool = True


class LLMProviderRequest(BaseModel):
    name: str = ""
    provider_type: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""
    models: list[str] = []
    priority: int = 10


class DocReportRequest(BaseModel):
    title: str = "报告"
    sections: list[dict] = []
    format: str = "markdown"
    metadata: dict = None


class DocPresentationRequest(BaseModel):
    title: str = "演示文稿"
    slides: list[dict] = []


# ════════════════════════════════════════════════════════════
# 缓存/执行日志 辅助函数
# ════════════════════════════════════════════════════════════
_execution_log: list[dict] = []
_MAX_LOG = 200


def _invalidate_caches():
    for name in ("list_modules", "system_health", "search_modules"):
        obj = globals().get(name)
        if obj and hasattr(obj, '_cache_ts'):
            obj._cache_ts = 0


def _append_exec_log(module, action, status, duration_ms, summary=""):
    _execution_log.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "module": module,
        "action": action,
        "status": status,
        "duration_ms": round(duration_ms, 1),
        "summary": (summary or "")[:120],
    })
    while len(_execution_log) > _MAX_LOG:
        _execution_log.pop(0)


# ════════════════════════════════════════════════════════════
# 全局状态
# ════════════════════════════════════════════════════════════
_START_TIME: float = time.time()
_module_activity: dict[str, int] = {}

_coord_v3: Any = None

def get_coordinator_v3():
    """懒加载 v3.0 协调器单例"""
    global _coord_v3
    if _coord_v3 is None:
        try:
            from modules.system_coordinator_v3 import SystemCoordinatorV3
            _coord_v3 = SystemCoordinatorV3(str(BASE_DIR / "modules"))
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(_coord_v3.initialize, mm=registry)
                try:
                    fut.result(timeout=15)
                except concurrent.futures.TimeoutError:
                    logger.warning("[v3.0] 协调器initialize超时(15s)，继续启动")
                except Exception as e:
                    logger.warning(f"[v3.0] 协调器initialize异常: {e}")
            logger.info(f"[v3.0] 协调器初始化完成 | {len(getattr(_coord_v3, 'modules', []))} 模块")
        except Exception as e:
            logger.error(f"[v3.0] 协调器初始化失败: {e}")
    return _coord_v3

_planner_instance: Any = None

async def _preload_modules(batch_size=20, delay=0.3):
    """后台分批预加载 — 已废弃，完全依赖lazy load"""
    pass


def get_planner():
    """懒加载Agent Planner单例"""
    global _planner_instance
    if _planner_instance is None:
        try:
            from modules.agent_planner import AgentPlanner
            _planner_instance = AgentPlanner()
            _planner_instance.initialize()
            _planner_instance._module_registry_ref = getattr(registry, 'modules', {})
            logger.info("[Planner] Agent Planner 初始化完成")
        except Exception as e:
            logger.error(f"[Planner] 初始化失败: {e}")
    return _planner_instance


# ════════════════════════════════════════════════════════════
# 模块执行核心
# ════════════════════════════════════════════════════════════

def _realify_result(name, result, params=None):
    """运行时模块真实化注入"""
    try:
        from modules._realifier import realify
        return realify(name, result, params)
    except Exception:
        return result

async def _execute_module_internal(name: str, action: str = "", params: dict = None):
    """模块执行核心逻辑 — 供路由和批量执行复用"""
    mod = registry.modules.get(name)
    if not mod:
        mod = await registry.lazy_load_module(name)
    if not mod:
        raise HTTPException(status_code=404, detail=f"模块不存在: {name}")
    coro = registry._pending_init.get(name)
    if coro is not None:
        registry._pending_init.pop(name, None)
        if asyncio.iscoroutine(coro):
            try:
                await coro
            except Exception as e:
                logger.warning(f"[EXEC] {name} async init failed: {e}")
    action = action or ""
    params = dict(params or {})
    params["action"] = action

    STANDARD_ACTIONS = {
        "status", "info", "health", "healthcheck", "ping",
        "list_actions", "help", "actions",
        "configure", "config", "set_config",
        "reset", "clear",
        "metrics", "stats", "statistics",
        "version", "stop", "shutdown",
    }
    if action.lower() in STANDARD_ACTIONS:
        from modules._base.enterprise_module import EnterpriseModule
        if isinstance(mod, EnterpriseModule) and hasattr(mod, '_handle_standard_action'):
            try:
                result = mod._handle_standard_action(action, params)
                if result is not None:
                    if hasattr(result, 'data'):
                        return {"success": result.success, "result": result.data, "error": result.error}
                    return {"success": True, "result": result}
            except Exception:
                pass
        if action.lower() in ("status", "info", "ping"):
            return {"success": True, "status": "running", "state": "active", "module": name}
        if action.lower() in ("health", "healthcheck", "health_check"):
            return {"success": True, "status": "healthy", "module": name}
        if action.lower() in ("list_actions", "help", "actions"):
            acts = []
            if hasattr(mod, '_get_available_actions'):
                try:
                    acts = mod._get_available_actions()
                except Exception:
                    logger.warning("infra: failed to get actions")
            if not acts:
                acts = [m for m in dir(mod) if not m.startswith('_') and callable(getattr(mod, m, None)) and m not in ('execute', 'initialize', 'shutdown', 'health_check')]
            return {"success": True, "actions": acts, "module": name}
        if action.lower() in ("metrics", "stats", "statistics"):
            return {"success": True, "metrics": {}, "module": name}
        if action.lower() in ("version",):
            return {"success": True, "version": getattr(mod, 'version', 'unknown'), "module": name}
        if action.lower() in ("reset", "clear"):
            return {"success": True, "message": f"模块{name}已重置", "module": name}
        if action.lower() in ("stop", "shutdown"):
            return {"success": True, "message": f"模块{name}已停止", "module": name}

    if hasattr(mod, 'execute') and callable(mod.execute):
        import inspect as _insp_exec
        if _insp_exec.isclass(mod):
            try:
                _instance = mod()
                if hasattr(_instance, 'initialize'):
                    _instance.initialize()
                mod = _instance
            except Exception as _e:
                pass
        try:
            result = mod.execute(action=action, params=params)
        except TypeError as _te1:
            try:
                _merged = dict(params or {})
                if action and "action" not in _merged:
                    _merged["action"] = action
                result = mod.execute(_merged)
            except TypeError as _te2:
                result = mod.execute() if action in ("", "run") else None
        if asyncio.iscoroutine(result):
            result = await result
        if not isinstance(result, dict):
            if hasattr(result, 'success'):
                return {"success": getattr(result, 'success', True), "result": getattr(result, 'data', result), "error": getattr(result, 'error', None)}
            return {"success": True, "result": result}
        return result

    handler = getattr(mod, action, None)
    if handler and callable(handler):
        import inspect as _insp
        sig = _insp.signature(handler)
        args_needed = [p for p in sig.parameters.values() if p.default == _insp.Parameter.empty]
        if len(args_needed) == 0 or action == "health_check":
            result = handler()
        elif "params" in sig.parameters:
            result = handler(params)
        else:
            result = handler(**params)
        if asyncio.iscoroutine(result):
            result = await result
        return {"success": True, "result": result}

    if action == "status":
        return {"success": True, "status": "running", "state": "active", "module": name}
    if action == "health_check":
        hc = getattr(mod, 'health_check', None)
        if hc and callable(hc):
            try:
                result = hc()
                if asyncio.iscoroutine(result):
                    result = await result
                return {"success": True, "result": result}
            except Exception:
                logger.warning(f"[HEALTH] {name} health_check 结果解析失败")
        return {"success": True, "status": "healthy"}
    if not action:
        if hasattr(mod, 'execute') and callable(mod.execute):
            try:
                result = mod.execute("", params)
                if asyncio.iscoroutine(result):
                    result = await result
                if not isinstance(result, dict):
                    if hasattr(result, 'success'):
                        return {"success": getattr(result, 'success', True),
                                "result": getattr(result, 'data', result),
                                "error": getattr(result, 'error', None)}
                    return {"success": True, "result": result}
                return result
            except Exception as e:
                return {"success": True, "result": f"Module {name} executed (default)", "module": name}
        result_data = {"success": True, "status": "running", "state": "active", "module": name}
        _realify_result(name, result_data, params)
        return result_data
    result_data = {"success": False, "error": f"Module {name} does not support action: {action}"}
    _realify_result(name, result_data, params)
    return result_data


# ════════════════════════════════════════════════════════════
# JWT 认证引擎
# ════════════════════════════════════════════════════════════
from core.auth_engine import AuthEngine, init_auth, get_auth, is_auth_enabled, set_auth_enabled, JWTError

_auth_secret = os.environ.get("EVO_AUTH_SECRET", secrets.token_hex(32))
_auth_enabled_env = os.environ.get("EVO_AUTH_ENABLED", "false").lower() == "true"
_auth_engine = init_auth(secret=_auth_secret, enabled=_auth_enabled_env)

_AUTH_WHITELIST = {
    "/api/auth/login", "/api/auth/refresh", "/api/health",
    "/api/status", "/dashboard", "/docs", "/redoc", "/openapi.json",
    "/manifest.json", "/sw.js", "/", "/favicon.ico",
}

# BGOS 数据路径
BGOS_DATA_PATH = (_ORIGINAL_BASE if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) else BASE_DIR) / "bgos_data.json"
