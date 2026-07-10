"""热加载配置"""
import logging
logger = logging.getLogger("evo.hot_config")

import os, json, yaml, time, threading

CONFIG_FILE = "api/evo_config.yaml"
_config = {}
_last_mtime = 0
_lock = threading.Lock()

DEFAULTS = {
    "server": {"host": "0.0.0.0", "port": 8765, "workers": 4},
    "auth": {"enabled": True, "mode": "jwt+apikey", "token_ttl": 86400},
    "tools": {"timeout": 120, "max_retries": 3},
    "rate_limit": {"requests": 60, "per_seconds": 60},
}

def load():
    global _config, _last_mtime
    if os.path.isfile(CONFIG_FILE):
        mtime = os.path.getmtime(CONFIG_FILE)
        if mtime > _last_mtime:
            with open(CONFIG_FILE) as f:
                try:
                    _config = yaml.safe_load(f) or {}
                except:
                    _config = {}
            _last_mtime = mtime
    _config = {**DEFAULTS, **_config}

def get(key, default=None):
    if not _config:
        load()
    keys = key.split(".")
    val = _config
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default

def reload_loop(interval=10):
    while True:
        load()
        time.sleep(interval)
