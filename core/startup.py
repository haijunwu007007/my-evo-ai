"""
AUTO-EVO-AI V0.1 — 启动模块：懒加载，非硬加载
"""
import os, sys, logging, importlib, time
from core.module_bus import module_bus

logger = logging.getLogger("startup")
_lazy_modules = {}

def discover_modules():
    """扫描 modules/ 目录，返回所有模块名称"""
    mods = []
    base = os.path.join(os.path.dirname(__file__), "..", "modules")
    base = os.path.abspath(base)
    if base not in sys.path:
        sys.path.insert(0, os.path.dirname(base))
    for f in sorted(os.listdir(base)):
        if f.endswith(".py") and not f.startswith("_") and f != "__init__.py":
            name = f[:-3]
            mods.append(name)
    return mods

def lazy_load(name):
    """懒加载单个模块"""
    try:
        mod = importlib.import_module(f"modules.{name}")
        if hasattr(mod, "module_class"):
            instance = mod.module_class()
            meta = getattr(mod, "__module_meta__", {})
            module_bus.register(name, instance, meta)
            logger.info(f"懒加载: {name} OK")
            return True
    except Exception as e:
        logger.debug(f"懒加载: {name} 跳过 ({e})")
    return False

def init(startup=True):
    """初始化：注册所有模块为懒加载"""
    t0 = time.time()
    all_mods = discover_modules()
    for name in all_mods:
        if startup and name in ("ocr_engine", "graph_engine"):
            lazy_load(name)  # 核心模块立即加载
        else:
            _lazy_modules[name] = name  # 其余标记为待加载

    count = module_bus.count()
    lazy_count = len(_lazy_modules)
    logger.info(f"启动完成: {count} 个立即加载, {lazy_count} 个懒加载待命, 耗时 {time.time()-t0:.2f}s")
    return {"loaded": count, "lazy": lazy_count}

def ensure_loaded(name):
    """确保模块已加载（按需加载）"""
    if module_bus.get(name):
        return True
    if name in _lazy_modules:
        lazy_load(name)
        del _lazy_modules[name]
        return module_bus.get(name) is not None
    return False
