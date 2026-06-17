"""插件自动发现加载"""
import os, logging, importlib

logger = logging.getLogger("evo.plugin_loader")
PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")

_loaded = {}

def discover():
    if not os.path.isdir(PLUGIN_DIR):
        return []
    plugins = []
    for f in sorted(os.listdir(PLUGIN_DIR)):
        if f.endswith(".py") and not f.startswith("_"):
            plugins.append(f[:-3])
    return plugins

def load_plugin(name):
    if name in _loaded:
        return _loaded[name]
    try:
        spec = importlib.util.spec_from_file_location(name, os.path.join(PLUGIN_DIR, f"{name}.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            mod.register()
        _loaded[name] = mod
        logger.info(f"插件已加载: {name}")
        return mod
    except Exception as e:
        logger.warning(f"插件加载失败 {name}: {e}")
        return None

def load_all():
    for p in discover():
        load_plugin(p)
    return list(_loaded.keys())
