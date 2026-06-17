"""插件系统 — 自动扫描注册"""
import os, importlib.util, logging

logger = logging.getLogger("evo.plugins")

def discover_plugins():
    """扫描 plugins/ 目录下的所有 .py 文件"""
    plugins = []
    plugins_dir = os.path.dirname(__file__)
    for f in sorted(os.listdir(plugins_dir)):
        if f.endswith(".py") and not f.startswith("_"):
            mod_name = f[:-3]
            try:
                spec = importlib.util.spec_from_file_location(mod_name, os.path.join(plugins_dir, f))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register()
                    plugins.append(mod_name)
                    logger.info(f"插件已加载: {mod_name}")
            except Exception as e:
                logger.error(f"插件加载失败 {mod_name}: {e}")
    return plugins
