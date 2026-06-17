"""配置热加载 — evo_config.yaml → 全局字典"""
import os, yaml, time, threading

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "evo_config.yaml")
_config_cache = {}
_last_mtime = 0
_lock = threading.Lock()

def load_config(force=False):
    global _config_cache, _last_mtime
    with _lock:
        mtime = os.path.getmtime(_CONFIG_PATH)
        if force or mtime != _last_mtime:
            with open(_CONFIG_PATH, "r") as f:
                _config_cache = yaml.safe_load(f) or {}
            _last_mtime = mtime
    return _config_cache

def get_config(key, default=None):
    """获取配置项，支持点号路径如 'server.port'"""
    parts = key.split(".")
    val = load_config()
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return default
    return val if val is not None else default

def hot_reload():
    """手动触发重新加载"""
    return load_config(force=True)
