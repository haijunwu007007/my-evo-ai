"""api/routes/__init__.py — 路由模块自动发现与批量注册

自动扫描本目录所有 routes_*.py 及 hub_static.py，
导入其 router 对象供 api_server.py 批量注册。
新加路由只需创建 routes_xxx.py，无需手动 import/include。
"""

from __future__ import annotations
import importlib
import logging
from pathlib import Path
from typing import Generator

from fastapi import APIRouter, FastAPI

logger = logging.getLogger("evo.routes")


def discover_routers() -> Generator[tuple[str, APIRouter], None, None]:
    """扫描本目录所有 routes_*.py + hub_static.py，yield (模块名, router)"""
    routes_dir = Path(__file__).parent
    patterns = ["routes_*.py", "hub_static.py"]
    seen = set()

    for pattern in patterns:
        for f in sorted(routes_dir.glob(pattern)):
            if f.stem == "__init__":
                continue
            mod_name = f.stem
            if mod_name in seen:
                continue
            seen.add(mod_name)
            try:
                mod = importlib.import_module(f"api.routes.{mod_name}")
                router = getattr(mod, "router", None)
                if router is not None and isinstance(router, APIRouter):
                    yield mod_name, router
                else:
                    logger.debug("[ROUTES] %s 无 APIRouter，跳过", mod_name)
            except Exception as exc:
                logger.warning("[ROUTES] %s 导入失败: %s", mod_name, exc)


def register_all_routers(app: FastAPI) -> int:
    """注册所有发现的路由器到 app，返回注册数量"""
    count = 0
    for mod_name, router in discover_routers():
        try:
            app.include_router(router)
            count += 1
            logger.debug("[ROUTES] ✅ %s 已注册", mod_name)
        except Exception as exc:
            logger.warning("[ROUTES] %s 注册失败: %s", mod_name, exc)
    logger.info("[ROUTES] 批量注册 %d 个路由模块", count)
    return count
