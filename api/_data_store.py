# -*- coding: utf-8 -*-
"""API 路由共享数据存储层 — 持久化、配置中心、公共辅助函数"""
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import time, json, logging, os, uuid as _uuid, random as _random, socket as _socket

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger("evo.api.data_store")
_now = datetime.now

# ── 持久化数据存储 ──
DATA_DIR = BASE_DIR / "_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_scheduler_tasks_db: Dict[str, dict] = {}
_events_db: List[dict] = []
_pipelines_db: Dict[str, dict] = {}
_queue_tasks_db: Dict[str, dict] = {}
_rules_db: Dict[str, dict] = {}
_monitor_history: List[dict] = []

_PERSISTENT_DBS = {
    "scheduler": (_scheduler_tasks_db, dict),
    "events": (_events_db, list),
    "pipelines": (_pipelines_db, dict),
    "queue": (_queue_tasks_db, dict),
    "rules": (_rules_db, dict),
}

def _save_all() -> Any:
    for name, (db, _) in _PERSISTENT_DBS.items():
        try:
            with open(DATA_DIR / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"保存 {name}.json 失败: {e}")

def _load_all() -> Any:
    for name, (db, dtype) in _PERSISTENT_DBS.items():
        path = DATA_DIR / f"{name}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if dtype == dict:
                    db.clear(); db.update(data)
                else:
                    db.clear(); db.extend(data)
            except Exception as e:
                logger.warning(f"加载 {name}.json 失败: {e}")

def _next_id(): return f"t{int(time.time())}{_random.randint(100,999)}"
def _ts(): return _now().isoformat()

_load_all()

# ── 配置中心 ──
try:
    from core.config_center import get_config_center as _real_config_center
    def get_config_center(): return _real_config_center()
except ImportError:
    _CONFIG_PATH = DATA_DIR / "config.json"
    class _ConfigCenter:
        def __init__(self) -> None:
            self._data = {}
            self._load()
        def _load(self) -> Any:
            if _CONFIG_PATH.exists():
                try:
                    self._data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    self._data = {}
            else:
                try:
                    import yaml
                    cfg = yaml.safe_load((BASE_DIR / "config.yaml").read_text(encoding="utf-8")) or {}
                    def _flatten(d, prefix="", out=None) -> Any:
                        if out is None: out = {}
                        for k, v in d.items():
                            key = f"{prefix}.{k}" if prefix else k
                            if isinstance(v, dict) and v: _flatten(v, key, out)
                            else: out[key] = v
                        return out
                    self._data = _flatten(cfg)
                    self._persist()
                except OSError:
                    self._data = {}
        def get(self, k, d=None): return self._data.get(k, d)
        def get_all(self): return dict(self._data)
        def set(self, k, v): self._data[k] = str(v); self._persist(); return True
        def delete(self, k): self._data.pop(k, None); self._persist(); return True
        def save(self): self._persist(); return True
        def reload(self): self._load(); return True
        def _persist(self) -> Any:
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
    def get_config_center(): return _ConfigCenter()

# ── 局域网 IP ──
def _get_lan_ip() -> Any:
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
_LAN_IP = _get_lan_ip()
_TUNNEL_URL = ""

# ── 工作流模板 ──
_TASK_TEMPLATES = {
    "github_trending": {
        "name": "📊 GitHub Trending 分析",
        "desc": "扫描GitHub热门项目→AI分析→推送到钉钉",
        "steps": [{"module":"githubtrending","action":"scan_trending","params":{"language":"python","period":"daily"}},{"module":"data_analysis","action":"analyze","params":{"type":"trending"}},{"module":"feishu_notifier","action":"send","params":{"title":"今日GitHub趋势"}}],
    },
    "health_report": {
        "name": "🩺 系统健康报告",
        "desc": "检查全部模块健康状态→生成报告→推送到通知",
        "steps": [{"module":"system_health","action":"check_all","params":{}},{"module":"report_generator","action":"report","params":{"type":"health"}},{"module":"notification_center","action":"send","params":{"title":"系统健康报告"}}],
    },
    "data_backup": {
        "name": "💾 数据备份通知",
        "desc": "执行数据备份→生成摘要→发送通知",
        "steps": [{"module":"object_storage","action":"backup","params":{}},{"module":"report_generator","action":"report","params":{"type":"backup"}},{"module":"notification_center","action":"send","params":{"title":"备份完成"}}],
    },
    "daily_self_evolution": {
        "name": "🧬 每日自我进化",
        "desc": "扫描GitHub趋势→代码分析→GLM-4解读→进化报告",
        "steps": [
            {"module":"githubtrending","action":"scan_trending","params":{"language":"all","period":"daily"}},
            {"module":"githubtrending","action":"analyze","params":{}},
            {"module":"evo_engine","action":"evolve","params":{"type":"daily_analysis"}},
        ],
        "cron": "0 9 * * *",
    },
}
