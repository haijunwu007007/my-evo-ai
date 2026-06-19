"""
AUTO-EVO-AI — 模块管理路由
==================================
模块注册表、CRUD、执行、搜索、批量操作
"""

from __future__ import annotations

import os, sys, json, time, asyncio, importlib, inspect, hashlib, secrets, logging
from typing import Any, Dict, List, Optional
from api.category_map import CATEGORY_MAP
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from api.infra import (
    BASE_DIR, _ORIGINAL_BASE, registry, rate_limiter, manager,
    _request_counter, _request_errors, _request_latency, _request_latency_ms,
    _cache_hits, _api_cache, _CACHE_TTL, _CACHEABLE_PATHS, _CACHE_SHORT_PATHS,
    _execution_log, _invalidate_caches, _append_exec_log,
    _module_activity, _coord_v3, _planner_instance,
    get_coordinator_v3, get_planner,
    _preload_modules, _execute_module_internal,
    classify_module, logger,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# 模块查询与搜索
# ═══════════════════════════════════════════════════════════════

@router.get("/api/v1/modules/stats")
async def modules_stats():
    """Module file stats"""
    from pathlib import Path
    mod_dir = Path(__file__).parent.parent.parent / "modules"
    files = [f for f in mod_dir.glob("*.py") if f.name != "__init__.py"] if mod_dir.exists() else []
    sizes = [f.stat().st_size for f in files]
    return {"success": True, "total_files": len(files),
        "total_size_kb": round(sum(sizes)/1024, 1) if sizes else 0,
        "avg_size_kb": round(sum(sizes)/len(sizes)/1024, 1) if sizes else 0}

@router.get("/api/v1/modules/categories")
async def get_module_categories():
    """Get Module Categories - GET /api/v1/modules/categories"""
    raw = registry.get_categories()
    # 标准化分类名
    normalized = {}
    for raw_cat, count in raw.items():
        key = CATEGORY_MAP.get(raw_cat.upper(), raw_cat.capitalize())
        normalized[key] = normalized.get(key, 0) + count
    total = sum(normalized.values())
    return {"success": True, "categories": normalized, "total": total}


@router.get("/api/v1/modules")
async def list_modules(category: str = "", page: int = 1, limit: int = 100):
    """List Modules - GET /api/v1/modules"""
    no_page = page <= 0 and limit <= 0
    base_data = None

    now = time.time()
    if (not category and page == 1 and limit == 100):
        if hasattr(list_modules, '_cache') and (now - list_modules._cache_ts) < 3.0:
            base_data = list_modules._cache

    if base_data is not None and no_page:
        return base_data

    if base_data is not None:
        filtered = base_data.get("modules", [])
        for m in filtered:
            if "category" not in m:
                m["category"] = classify_module(m.get("name", ""))
    else:
        result = []
        for name, mod in registry.modules.items():
            try:
                cls_name = type(mod).__name__ if not inspect.ismodule(mod) else "module"
                health = registry.health.get(name, {})
                methods = []
                if not inspect.ismodule(mod):
                    try:
                        methods = [m for m in dir(mod) if not m.startswith("_") and callable(getattr(mod, m, None))]
                    except Exception:
                        methods = []
                import os as _os
                _mod_path = None
                if not inspect.ismodule(mod):
                    try: _mod_path = inspect.getfile(type(mod))
                    except Exception: _mod_path = None
                try:
                    if not _mod_path and isinstance(mod, type):
                        import importlib as _il
                        _src = _il.util.find_spec(name)
                        if _src: _mod_path = _src.origin
                except Exception: logger.debug(f"模块{name}路径获取失败")
                _fsize = _os.path.getsize(_mod_path) if _mod_path and _os.path.isfile(_mod_path) else 0
                result.append({
                    "name": name, "class": cls_name,
                    "category": classify_module(name),
                    "status": health.get("status", "unknown"),
                    "grade": health.get("grade", "C"),
                    "initialized": health.get("initialized", False),
                    "methods": methods,
                    "file_size": _fsize,
                })
            except Exception:
                result.append({"name": name, "class": "error", "category": "system",
                               "status": "error", "grade": "C", "methods": []})
        for name, info in registry._pending_modules.items():
            import os as _os2
            _pend_path = _os2.path.join(str(BASE_DIR), "modules", f"{name}.py")
            _pend_size = _os2.path.getsize(_pend_path) if _os2.path.isfile(_pend_path) else 0
            result.append({
                "name": name, "class": "pending",
                "category": classify_module(name),
                "status": "pending_lazy", "grade": "lazy",
                "initialized": False, "methods": [],
                "file_size": _pend_size,
            })
        list_modules._cache = {"modules": result, "count": len(result)}
        list_modules._cache_ts = time.time()
        filtered = result

    if category:
        filtered = [m for m in filtered if m.get("category") == category]

    if no_page:
        return {"success": True, "modules": filtered, "count": len(filtered), "categories": registry.get_categories()}

    total = len(filtered)
    start = (page - 1) * limit
    paged = filtered[start:start + limit]
    return {
        "success": True, "modules": paged, "count": total, "page": page, "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit),
        "categories": registry.get_categories(),
    }


@router.get("/api/v1/search/modules")
async def search_modules(q: str = "", status: str = "", limit: int = 50, offset: int = 0):
    """Search Modules - GET /api/v1/search/modules"""
    all_mods = await list_modules()
    mods = all_mods.get("modules", [])
    ql = q.lower().strip() if q else ""

    filtered = []
    for m in mods:
        if status and m.get("status") != status:
            continue
        if ql:
            searchable = (m.get("name", "") + " " + m.get("class", "") +
                          " " + " ".join(m.get("methods", []))).lower()
            if ql not in searchable:
                continue
        filtered.append(m)

    total = len(filtered)
    paged = filtered[offset:offset + limit]
    return {"success": True, "modules": paged, "total": total, "offset": offset, "limit": limit}


# ═══════════════════════════════════════════════════════════════
# 模块 CRUD
# ═══════════════════════════════════════════════════════════════

@router.post("/api/v1/modules/install")
async def install_module_api(request: Request):
    """Install Module Api - POST /api/v1/modules/install"""
    body = await request.json()
    code = body.get("code", "")
    name = body.get("name", "")
    if not code or not name:
        return {"success": False, "error": "需要 code 和 name 参数"}
    try:
        safe_name = registry.install_module(code, name)
        try:
            await asyncio.wait_for(registry.lazy_load_module(safe_name), timeout=15)
            return {"success": True, "module": safe_name, "status": "loaded",
                    "message": "模块已安装并加载成功"}
        except Exception as e:
            return {"success": True, "module": safe_name, "status": "registered",
                    "message": f"模块已注册但加载失败: {e}"[:120]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.post("/api/v1/modules/rescan")
async def rescan_modules_api():
    """Rescan Modules Api - POST /api/v1/modules/rescan"""
    try:
        added = registry.rescan_modules("modules")
        return {"success": True, "new_modules": added, "total": registry.get_total_count()}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.delete("/api/v1/modules/{name}")
async def uninstall_module_api(name: str):
    """Uninstall Module Api - DELETE /api/v1/modules/{name}"""
    if not name or name in ("modules", "health", "status"):
        return {"success": False, "error": "不能卸载核心模块"}
    try:
        removed_file = registry.uninstall_module(name)
        return {"success": True, "module": name, "file_removed": removed_file}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.get("/api/v1/modules/{name}/health")
async def module_health(name: str):
    """Module Health - GET /api/v1/modules/{name}/health"""
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
                logger.warning(f"[HEALTH] {name} async init failed: {e}")
    if not getattr(mod, '_status', None) and hasattr(mod, '_status'):
        mod._status = 'active'
    if not getattr(mod, '_data', None) and hasattr(mod, '_data'):
        mod._data = {}
    if not getattr(mod, '_metrics', None) and hasattr(mod, '_metrics'):
        mod._metrics = {"total_operations": 0, "errors": 0, "avg_latency_ms": 0}
    try:
        if hasattr(mod, 'health_check') and callable(mod.health_check):
            result = mod.health_check()
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, dict):
                registry.health[name] = result
                return result
        health = registry.health.get(name)
        if health:
            return health
        return {"success": False, "status": "unknown", "module": name, "detail": "无health_check方法"}
    except Exception as e:
        logger.error(f"health_check失败 {name}: {e}")
        return {"success": False, "status": "error", "module": name, "error": str(e)}


@router.get("/api/v1/modules/{name}/code")
async def module_source_code(name: str, lines: int = 100):
    """Module Source Code - GET /api/v1/modules/{name}/code"""
    mod = registry.modules.get(name)
    if not mod:
        mod = await registry.lazy_load_module(name)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module not found: {name}")
    try:
        src_file = inspect.getsourcefile(mod if not inspect.ismodule(mod) else type(mod))
        if not src_file:
            src_file = inspect.getsourcefile(mod if inspect.ismodule(mod) else mod.__class__)
    except Exception:
        src_file = None

    if src_file and Path(src_file).exists():
        try:
            all_lines = Path(src_file).read_text(encoding="utf-8", errors="ignore").splitlines()
            total = len(all_lines)
            code = "\n".join(all_lines[:lines])
            return {
                "success": True, "module": name, "file": src_file,
                "total_lines": total, "shown_lines": min(total, lines), "code": code,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    try:
        target = mod if not inspect.ismodule(mod) else type(mod)
        src = inspect.getsource(target)
        lines_list = src.splitlines()
        return {
            "success": True, "module": name, "total_lines": len(lines_list),
            "shown_lines": min(len(lines_list), lines),
            "code": "\n".join(lines_list[:lines]),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/v1/modules/{name}")
async def get_module_detail_api(name: str):
    """Get Module Detail Api - GET /api/v1/modules/{name}"""
    mod = registry.modules.get(name)
    if not mod:
        mod = await registry.lazy_load_module(name)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module not found: {name}")

    health = registry.health.get(name, {})
    cls_name = type(mod).__name__ if not inspect.ismodule(mod) else "module"
    methods = []
    if not inspect.ismodule(mod):
        try:
            methods = [m for m in dir(mod) if not m.startswith("_") and callable(getattr(mod, m, None))]
        except Exception:
            methods = []
    doc = ""
    try:
        doc = inspect.getdoc(mod if not inspect.ismodule(mod) else type(mod)) or ""
    except Exception:
        pass

    return {
        "success": True, "name": name, "class": cls_name,
        "status": health.get("status", "unknown"),
        "grade": health.get("grade", "C"),
        "initialized": health.get("initialized", False),
        "methods": methods[:50], "doc": doc[:500], "health": health,
    }


# ═══════════════════════════════════════════════════════════════
# 模块调用与执行
# ═══════════════════════════════════════════════════════════════

@router.get("/api/v1/batches")
async def list_batches():
    """List Batches - GET /api/v1/batches"""
    all_modules = list(registry._pending_modules.keys()) + list(registry.modules.keys())
    all_modules.sort()
    batch_size = 20
    batches = []
    for i in range(0, len(all_modules), batch_size):
        batch_modules = all_modules[i:i + batch_size]
        loaded = sum(1 for m in batch_modules if m in registry.modules)
        batches.append({
            "id": f"batch_{i // batch_size + 1}",
            "name": f"Batch {i // batch_size + 1}",
            "start_index": i, "total": len(batch_modules),
            "loaded": loaded, "pending": len(batch_modules) - loaded,
            "modules": batch_modules,
        })
    return {
        "success": True, "batches": batches, "total_batches": len(batches),
        "total_modules": len(all_modules), "total_loaded": len(registry.modules),
    }


@router.post("/api/v1/modules/{name}/call/{method}")
async def call_module_method(name: str, method: str, request: Request):
    """Call Module Method - POST /api/v1/modules/{name}/call/{method}"""
    body = await request.json()
    args = body.get("args", [])
    kwargs = body.get("kwargs", {})
    mod = registry.modules.get(name)
    if not mod:
        mod = await registry.lazy_load_module(name)
    if not mod:
        raise HTTPException(status_code=404, detail=f"模块不存在: {name}")
    handler = getattr(mod, method, None)
    if not handler or not callable(handler):
        raise HTTPException(status_code=404, detail=f"方法不存在: {name}.{method}")
    try:
        result = handler(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return result if isinstance(result, dict) else {"success": True, "result": result}
    except Exception as e:
        logger.error(f"调用失败 {name}.{method}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/v1/modules/{name}/execute")
async def execute_module_endpoint(name: str, request: Request):
    """Execute Module Endpoint - POST /api/v1/modules/{name}/execute"""
    # Fast direct import path for compact modules (bypasses _execute_module_internal)
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = body.get("action", "")
    params_dict = body.get("params", {})
    action = action or ""

    # Direct import path — bypasses lazy_load_module for compact modules
    _BYPS = {"github_scanner","data_masking","permission_rbac",
             "recommendation_system","sql_generator","agent_planner"}
    if name in _BYPS:
        try:
            import importlib as _il, asyncio as _as
            _mod = _il.import_module(f"modules.{name}")
            _cls = getattr(_mod, "module_class", None)
            if _cls:
                import inspect as _insp
                _inst = _cls() if _insp.isclass(_cls) else _cls
                if hasattr(_inst, 'initialize'): _inst.initialize()
                # Special: agent_planner uses async_execute(task=) in async context
                if name == "agent_planner":
                    task_text = params_dict.get("task", action) or action
                    _r = _inst.async_execute(task=task_text, params=params_dict)
                    _raw = await _r if hasattr(_r, '__await__') else _r
                    if isinstance(_raw, dict):
                        if _raw.get("status") == "error":
                            return {"success": False, "error": _raw.get("error","unknown")}
                        return {"success": True, "result": _raw.get("result",_raw), "plan_id": _raw.get("plan_id")}
                else:
                    _r = _inst.execute(action=action, params=params_dict)
                if hasattr(_r, '__await__') or hasattr(_r, 'send'):
                    _result = await _r
                else:
                    _result = _r
                if isinstance(_result, dict): return _result
                from modules._base.enterprise_module import Result as _R
                if isinstance(_result, _R):
                    return {"success": _result.success, "result": _result.data, "error": _result.error}
                return {"success": True, "result": _result}
        except Exception as e:
            logger.warning(f"[EXECUTE] 调用失败: {e}")

    t0 = time.time()
    try:
        result = await _execute_module_internal(name, action, params_dict)
        dur = (time.time() - t0) * 1000
        ok = result.get("success", False)
        _append_exec_log(name, action or "execute", "ok" if ok else "fail", dur,
                         str(result.get("result", result.get("error", "")))[:120])
        _module_activity[name] = _module_activity.get(name, 0) + 1
        return result
    except Exception as e:
        dur = (time.time() - t0) * 1000
        _append_exec_log(name, action or "execute", "error", dur, str(e)[:120])
        _module_activity[name] = _module_activity.get(name, 0) + 1
        raise


@router.post("/api/v1/call")
async def call_generic(request: Request):
    """Call Generic - POST /api/v1/call"""
    body = await request.json()
    module = body.get("module", "")
    method = body.get("method", "")
    args = body.get("args", [])
    kwargs = body.get("kwargs", {})
    mod = registry.modules.get(module)
    if not mod:
        return {"success": False, "error": f"模块不存在: {module}"}
    handler = getattr(mod, method, None)
    if not handler or not callable(handler):
        return {"success": False, "error": f"方法不存在: {module}.{method}"}
    try:
        result = handler(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return result if isinstance(result, dict) else {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 协调器已移至 routes_coordinator.py




@router.post("/api/v1/batch-execute")
async def batch_execute(request: Request):
    """Batch Execute - POST /api/v1/batch-execute"""
    body = await request.json()
    targets = body.get("targets", [])
    action = body.get("action", "status")
    if not targets:
        return {"success": False, "error": "targets is empty"}

    normalized = []
    for t in targets[:20]:
        if isinstance(t, str):
            normalized.append({"module": t, "action": action, "params": {}})
        else:
            normalized.append({
                "module": t.get("module", ""),
                "action": t.get("action", action),
                "params": t.get("params", {}),
            })

    results = []
    for item in normalized:
        name = item["module"]
        act = item["action"]
        params = item["params"]
        t0 = time.time()
        try:
            r = await _execute_module_internal(name, act, params)
            dur = (time.time() - t0) * 1000
            ok = r.get("success", False)
            _append_exec_log(name, act, "ok" if ok else "fail", dur,
                             str(r.get("result", r.get("error", "")))[:120])
            results.append({
                "module": name, "success": ok, "duration_ms": round(dur, 1),
                "result": r.get("result", r.get("error", "")),
            })
        except Exception as e:
            dur = (time.time() - t0) * 1000
            _append_exec_log(name, act, "error", dur, str(e)[:120])
            results.append({
                "module": name, "success": False,
                "duration_ms": round(dur, 1), "error": str(e)[:120],
            })

    ok_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True, "total": len(results),
        "ok": ok_count, "fail": len(results) - ok_count, "results": results,
    }


@router.get("/api/v1/execution-log")
async def get_execution_log(limit: int = 50):
    """Get Execution Log - GET /api/v1/execution-log"""
    return {"success": True, "log": _execution_log[-limit:], "total": len(_execution_log)}


# ===== Merged from routes_modules_browse.py =====
"""
AUTO-EVO-AI V0.1 — 模块浏览/搜索/分类 API
上市公司级: 解决535模块认知负担，让用户能发现、搜索、过滤模块
"""
from __future__ import annotations

from core.logging_config import get_logger
import os
import re
from pathlib import Path
from typing import Any
from api.category_map import normalize_category

from fastapi import APIRouter, Query

logger = get_logger("evo.api.modules_browse")

router = APIRouter()

MODULES_DIR = Path(__file__).resolve().parent.parent.parent / "modules"


def _scan_modules() -> list[dict[str, Any]]:
    """扫描 modules/ 目录，返回每个模块的元数据"""
    modules = []
    if not MODULES_DIR.exists():
        return modules
    for f in sorted(MODULES_DIR.iterdir()):
        if not f.name.endswith(".py") or f.name.startswith("_"):
            continue
        # 读取模块元数据
        content = f.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        docstring = ""
        reading_doc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if reading_doc:
                    break
                reading_doc = True
                doc_part = stripped[3:].strip()
                if doc_part:
                    docstring = doc_part
                continue
            if reading_doc:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    docstring += " " + stripped[:-3]
                    break
                docstring += " " + stripped

        # 提取 module_class 和 execute 方法
        has_execute = "async def execute" in content or "def execute" in content
        has_class = "class module_class" in content or "class Module" in content

        # 提取 grade（从 __module_meta__ 或文件注释）
        grade_match = re.search(r"""["']grade["']\s*:\s*["'](\w)["']""", content)
        grade = grade_match.group(1).upper() if grade_match else 'C'

        # 提取 category（从文件名前缀或 __module_meta__）
        meta_cat = re.search(r"""["']category["']\s*:\s*["']([\w_]+)["']""", content)
        if meta_cat:
            category = normalize_category(meta_cat.group(1))
        else:
            # fallback: 按文件名前缀分类
            parts = f.name[:-3].split('_')
            raw_cat = parts[0].upper() if len(parts) > 1 else f.name[:-3][:10].upper()
            category = normalize_category(raw_cat)

        module_size = len(content)

        # 判断是否真实逻辑（>2KB 或有 execute 方法）
        real_logic = module_size > 2048 or has_execute

        # 提取 actions
        actions = []
        for pattern in [
            r'action\s*=\s*"(\w+)"',
            r'action_lower\s*in\s*\("(\w+)"',
            r'"(\w+)"\s*,\s*#.*action',
        ]:
            actions.extend(re.findall(pattern, content))
        modules.append(
            {
                "name": f.name[:-3],
                "file": f.name,
                "size": module_size,
                "lines": len(lines),
                "has_class": has_class,
                "has_execute": has_execute,
                "grade": grade,
                "category": category,
                "real_logic": real_logic,
                "docstring": docstring[:200] if docstring else "",
                "actions": sorted(set(actions))[:20],
            }
        )
    return modules


@router.get("/api/v1/modules/list")
async def modules_list(
    search: str = Query("", description="搜索关键词（名称或描述）"),
    has_execute: bool | None = Query(None, description="是否包含 execute 方法"),
    min_lines: int = Query(0, description="最小行数"),
    sort_by: str = Query("name", description="排序: name|size|lines"),
    limit: int = Query(50, description="返回数量"),
    offset: int = Query(0, description="偏移量"),
):
    """浏览和搜索模块目录"""
    all_modules = _scan_modules()
    total = len(all_modules)

    # 过滤
    if search:
        q = search.lower()
        all_modules = [m for m in all_modules if q in m["name"].lower() or q in m["docstring"].lower()]
    if has_execute is not None:
        all_modules = [m for m in all_modules if m["has_execute"] == has_execute]
    if min_lines > 0:
        all_modules = [m for m in all_modules if m["lines"] >= min_lines]

    # 排序
    reverse = sort_by.startswith("-")
    key = sort_by.lstrip("-")
    if key in ("name", "size", "lines"):
        all_modules.sort(key=lambda m, k=key: m.get(k, 0) if isinstance(m.get(k, 0), (int, float)) else str(m.get(k, "")), reverse=reverse)

    # 分页
    page = all_modules[offset : offset + limit]
    return {
        "success": True,
        "modules": page,
        "total": total,
        "filtered": len(all_modules),
        "returned": len(page),
        "offset": offset,
        "limit": limit,
    }


@router.get("/api/v1/modules/categories")
async def modules_categories():
    """模块分类统计"""
    all_modules = _scan_modules()
    categories: dict[str, int] = {}
    for m in all_modules:
        # 按文件名首字母/前缀分类
        prefix = m["name"].split("_")[0] if "_" in m["name"] else m["name"][0].upper()
        categories[prefix] = categories.get(prefix, 0) + 1

    size_ranges = {"<1KB": 0, "1-5KB": 0, "5-20KB": 0, ">20KB": 0}
    for m in all_modules:
        if m["size"] < 1024:
            size_ranges["<1KB"] += 1
        elif m["size"] < 5120:
            size_ranges["1-5KB"] += 1
        elif m["size"] < 20480:
            size_ranges["5-20KB"] += 1
        else:
            size_ranges[">20KB"] += 1

    return {
        "success": True,
        "total": len(all_modules),
        "with_execute": sum(1 for m in all_modules if m["has_execute"]),
        "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "size_ranges": size_ranges,
        "largest": sorted(all_modules, key=lambda m: -m["size"])[:5],
    }
