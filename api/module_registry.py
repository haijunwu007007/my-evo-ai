"""模块注册修复 — 450模块真实注册"""
import os, sys, json, logging, importlib, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("evo.module_registry")

BASE_DIR = Path(__file__).parent.parent
MODULES_DIR = BASE_DIR / "modules"

_registry = {}
_loaded = set()

def scan_modules():
    """扫描所有模块文件"""
    files = sorted(MODULES_DIR.glob("[a-z]*.py"))
    modules = {}
    for f in files:
        mod_name = f.stem
        if mod_name.startswith("_"):
            continue
        cat = _guess_category(mod_name)
        modules[mod_name] = {"file": str(f), "category": cat, "loaded": False}
    return modules

def _guess_category(name):
    cats = {
        "browser": "浏览器",
        "chat": "聊天",
        "code": "代码", "git": "Git", "deploy": "部署",
        "email": "邮件", "file": "文件",
        "media": "媒体", "monitor": "监控",
        "network": "网络", "notify": "通知",
        "search": "搜索", "security": "安全",
        "social": "社交", "sys": "系统",
        "web": "Web", "workflow": "工作流",
    }
    for prefix, cat in cats.items():
        if name.startswith(prefix):
            return cat
    return "其他"

def load_module(name, filepath):
    """加载单个模块"""
    try:
        spec = importlib.util.spec_from_file_location(name, filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _loaded.add(name)
        return True
    except Exception as e:
        logger.warning(f"模块加载失败 {name}: {e}")
        return False

def load_all_async(max_workers=8):
    """异步批量加载所有模块"""
    modules = scan_modules()
    total = len(modules)
    logger.info(f"开始异步加载 {total} 模块")
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(load_module, name, info["file"]): name
                   for name, info in modules.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                ok = future.result()
                if ok:
                    _registry[name] = modules[name]
                    _registry[name]["loaded"] = True
            except: pass
    elapsed = time.time() - start
    logger.info(f"异步加载完成: {len(_loaded)}/{total} 成功, 耗时{elapsed:.1f}s")
    return {"loaded": len(_loaded), "total": total, "elapsed": f"{elapsed:.1f}s"}

def get_registered():
    return dict(_registry)
