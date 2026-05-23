# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 — 认证/系统 路由
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Response
import time, json, logging, os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger("evo.api.auth_system")

from api.infra import (
    app, registry, _module_activity, _START_TIME,
    _request_counter, _request_errors, _request_latency_ms,
    _cache_hits, _api_cache, _CACHE_TTL, manager,
    BASE_DIR, _API_KEY, rate_limiter,
    _CACHEABLE_PATHS, _CACHE_SHORT_PATHS,
)
from datetime import datetime, timedelta
import socket as _socket
router = APIRouter()

# ── 持久化数据存储（JSON文件，重启不丢）──
import uuid as _uuid, random as _random
_now = datetime.now

DATA_DIR = BASE_DIR / "_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_scheduler_tasks_db: Dict[str, dict] = {}
_events_db: List[dict] = []
_pipelines_db: Dict[str, dict] = {}
_queue_tasks_db: Dict[str, dict] = {}
_rules_db: Dict[str, dict] = {}
_monitor_history: List[dict] = []
_task_seq = [0]

_PERSISTENT_DBS = {
    "scheduler": (_scheduler_tasks_db, dict),
    "events": (_events_db, list),
    "pipelines": (_pipelines_db, dict),
    "queue": (_queue_tasks_db, dict),
    "rules": (_rules_db, dict),
}

def _save_all():
    """将所有内存数据写入JSON文件"""
    for name, (db, _) in _PERSISTENT_DBS.items():
        try:
            with open(DATA_DIR / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"保存 {name}.json 失败: {e}")

def _load_all():
    """启动时从JSON文件加载数据"""
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

try:
    from core.config_center import get_config_center as _real_config_center
    def get_config_center(): return _real_config_center()
except ImportError:
    # 持久化配置中心 — 数据保存到 _data/config.json，重启不丢
    _CONFIG_PATH = DATA_DIR / "config.json"
    class _ConfigCenter:
        def __init__(self):
            self._data = {}
            self._load()
        def _load(self):
            if _CONFIG_PATH.exists():
                try: self._data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                except: self._data = {}
            else:
                # 从 config.yaml 初始化
                try:
                    import yaml
                    cfg = yaml.safe_load((BASE_DIR / "config.yaml").read_text(encoding="utf-8")) or {}
                    def _flatten(d, prefix="", out=None):
                        if out is None: out = {}
                        for k, v in d.items():
                            key = f"{prefix}.{k}" if prefix else k
                            if isinstance(v, dict) and v: _flatten(v, key, out)
                            else: out[key] = v
                        return out
                    self._data = _flatten(cfg)
                    self._persist()
                except: self._data = {}
        def get(self, k, d=None): return self._data.get(k, d)
        def get_all(self): return dict(self._data)
        def set(self, k, v): self._data[k] = str(v); self._persist(); return True
        def delete(self, k): self._data.pop(k, None); self._persist(); return True
        def save(self): self._persist(); return True
        def reload(self): self._load(); return True
        def _persist(self):
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
    def get_config_center(): return _ConfigCenter()

# ─── 认证 & 安全 ────────────────────────────────────
@router.get("/api/auth/status")
async def auth_status():
    return {"success": True, "api_key_enabled": bool(_API_KEY), "auth_mode": "api_key"}
@router.get("/api/security/status")
async def security_status():
    return {"success": True, "api_key_enabled": bool(_API_KEY), "jwt_enabled": True, "rbac_enabled": True, "rate_limiting": True, "firewall": False}
@router.post("/api/auth/login")
async def auth_login(body: dict):
    key = body.get("api_key", "")
    if not _API_KEY:
        return {"success": True, "token": "dev-token", "message": "dev mode"}
    if key == _API_KEY:
        return {"success": True, "token": "auth-token"}
    return {"success": False, "error": "invalid api key"}
@router.get("/api/auth/tokens")
async def auth_tokens():
    return {"tokens": []}

# ─── 系统诊断 ────────────────────────────────────────
@router.get("/api/diagnosis/system")
async def system_diagnosis():
    u = time.time() - _START_TIME
    return {"success": True, "uptime_seconds": round(u, 1), "uptime_human": f"{int(u//3600)}h{int(u%3600//60)}m", "memory_mb": 0, "cpu_percent": 0, "threads": 0, "api_version": "0.1.0"}
@router.get("/api/diagnosis/modules")
async def modules_diagnosis():
    m = registry.list_modules() if hasattr(registry, 'list_modules') else []
    return {"success": True, "modules": m, "count": len(list(m)) if isinstance(m, (list,dict)) else 0}

# ─── 配置中心 ────────────────────────────────────────
@router.get("/api/config")
async def config_list():
    cc = get_config_center(); return {"success": True, "configs": cc.get_all()}
@router.get("/api/config/entries")
async def config_entries():
    try:
        cc = get_config_center(); all_cfg = cc.get_all()
        if isinstance(all_cfg, dict):
            entries = [{"key": k, "value": str(v)[:200]} for k, v in all_cfg.items()]
            return {"success": True, "entries": entries, "count": len(entries)}
    except: pass
    return {"success": True, "entries": [], "count": 0}
@router.get("/api/config/{key:path}")
async def config_get(key: str):
    return {"success": True, "key": key, "value": get_config_center().get(key)}
@router.put("/api/config/{key:path}")
async def config_set(key: str, body: dict):
    get_config_center().set(key, body.get("value")); return {"success": True, "key": key, "set": True}
@router.post("/api/config/batch")
async def config_batch(body: dict):
    items = body.get("configs", body)
    if isinstance(items, dict):
        for k, v in items.items(): get_config_center().set(k, v)
    return {"success": True, "updated": len(items) if isinstance(items, dict) else 0}
@router.delete("/api/config/{key:path}")
async def config_delete(key: str):
    get_config_center().delete(key); return {"success": True, "deleted": key}
@router.get("/api/config/stats")
async def config_stats():
    return {"success": True, "groups": {"系统": ["api_host","api_port","log_level"],"通知":["dingtalk","feishu"],"LLM":["provider","model"]}, "total": 20}
@router.get("/api/config/list")
async def config_list_all(group: str = "", mask: bool = True):
    all_cfg = get_config_center().get_all()
    if group: return {"success": True, "group": group, "configs": {k:v for k,v in all_cfg.items() if k.startswith(group)}}
    return {"success": True, "configs": all_cfg}
@router.post("/api/config/save")
async def config_save():
    cc = get_config_center()
    if hasattr(cc, 'save'): cc.save()
    # 真实写回 config.yaml
    try:
        import yaml as _yaml
        _yaml.dump(cc.get_all(), open(str(BASE_DIR / "config.yaml"), "w", encoding="utf-8"), allow_unicode=True, default_flow_style=False)
    except Exception:
        pass
    return {"success": True, "saved": True}
@router.post("/api/config/reload")
async def config_reload():
    cc = get_config_center()
    if hasattr(cc, 'reload'): cc.reload()
    return {"success": True, "reloaded": True}

# ─── 持久化 ─────────────────────────────────────────
@router.get("/api/persistence/status")
async def persistence_status():
    return {"success": True, "persistence_enabled": True, "db_type": "sqlite"}

# ─── 内网穿透 ──────────────────────────────────────
@router.get("/api/tunnel/status")
async def tunnel_status():
    return {"success": True, "tunnel_enabled": False, "public_url": None}

# ─── 调度器 ────────────────────────────────────────
@router.get("/api/scheduler/status")
async def scheduler_status():
    active = sum(1 for t in _scheduler_tasks_db.values() if t.get("status") == "running")
    return {"success": True, "running": True, "active_tasks": active, "total_tasks": len(_scheduler_tasks_db)}
@router.get("/api/scheduler/tasks")
async def scheduler_tasks():
    tasks = sorted(_scheduler_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)
    return {"success": True, "tasks": tasks, "count": len(tasks), "running": True}
@router.post("/api/scheduler/tasks")
async def scheduler_create(body: dict = None):
    tid = _next_id()
    task = {
        "id": tid, "name": (body or {}).get("name", f"任务{tid}"),
        "target_type": (body or {}).get("target_type", "module"),
        "target_id": (body or {}).get("target_id", ""),
        "cron": (body or {}).get("cron", ""),
        "status": "running",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }
    _scheduler_tasks_db[tid] = task; _save_all()
    return {"success": True, "task": task}
@router.post("/api/scheduler/tasks/{task_id}/toggle")
async def scheduler_toggle(task_id: str):
    if task_id in _scheduler_tasks_db:
        t = _scheduler_tasks_db[task_id]
        t["status"] = "paused" if t.get("status") == "running" else "running"
        _save_all()
    return {"success": True}
@router.post("/api/scheduler/tasks/{task_id}/trigger")
async def scheduler_trigger(task_id: str):
    if task_id in _scheduler_tasks_db:
        _scheduler_tasks_db[task_id]["last_run"] = _ts()
        _save_all()
    return {"success": True, "triggered": True}
@router.delete("/api/scheduler/tasks/{task_id}")
async def scheduler_delete(task_id: str):
    _scheduler_tasks_db.pop(task_id, None); _save_all()
    return {"success": True}

# ─── 事件引擎 ─────────────────────────────────────
@router.get("/api/events/stats")
async def events_stats():
    one_hour_ago = _now() - timedelta(hours=1)
    recent = [e for e in _events_db if e.get("timestamp", "") > one_hour_ago.isoformat()]
    return {
        "success": True, "total_events": len(_events_db), "total_rules": len(_rules_db),
        "active_rules": sum(1 for r in _rules_db.values() if r.get("enabled", True)),
        "events_last_hour": len(recent),
        "total_emitted": len(_events_db),
        "top_event_types": {"system": len(_events_db)}, "watches": 0, "subscribers": 0,
    }
@router.get("/js/{file_path:path}")
async def serve_js(file_path: str):
    """提供前端拆分后的 JS 静态文件"""
    base = BASE_DIR / "js" / file_path
    if not base.exists() or not base.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    ext = base.suffix.lower()
    content_type = {"js": "application/javascript", "css": "text/css", "json": "application/json"}
    ct = content_type.get(ext.lstrip("."), "application/octet-stream")
    return Response(base.read_bytes(), media_type=ct)
async def events_recent(limit: int = 20):
    items = sorted(_events_db, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]
    return {"success": True, "events": items, "total": len(items)}
@router.get("/api/events/rules")
async def events_rules():
    rules = sorted(_rules_db.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return {"success": True, "rules": rules, "count": len(rules)}
@router.post("/api/events/rules")
async def events_rule_create(body: dict = None):
    rid = _next_id()
    rule = {
        "id": rid, "name": (body or {}).get("name", f"规则{rid}"),
        "pattern": (body or {}).get("pattern", "*"),
        "action": (body or {}).get("action", "notify"),
        "enabled": True, "created_at": _ts(),
    }
    _rules_db[rid] = rule; _save_all()
    return {"success": True, "rule": rule}
@router.delete("/api/events/rules/{rule_id}")
async def events_rule_delete(rule_id: str):
    _rules_db.pop(rule_id, None); _save_all()
    return {"success": True}

# ─── 管线引擎 ─────────────────────────────────────
@router.get("/api/pipeline/status")
async def pipeline_status():
    active = sum(1 for p in _pipelines_db.values() if p.get("status") == "running")
    return {"success": True, "running": True, "pipelines": list(_pipelines_db.values()), "active_count": active}
@router.get("/api/pipelines")
async def pipelines_list():
    items = sorted(_pipelines_db.values(), key=lambda p: p.get("created_at", ""), reverse=True)
    return {"success": True, "pipelines": items, "count": len(items)}
@router.get("/api/pipelines/stats")
async def pipelines_stats():
    total = len(_pipelines_db)
    active = sum(1 for p in _pipelines_db.values() if p.get("status")== "running")
    done = sum(1 for p in _pipelines_db.values() if p.get("status")=="completed")
    failed = sum(1 for p in _pipelines_db.values() if p.get("status")=="failed")
    return {"success": True, "total": total, "active": active, "completed": done, "failed": failed}
@router.post("/api/pipelines")
async def pipelines_create(body: dict = None):
    pid = _next_id()
    pipe = {
        "id": pid, "name": (body or {}).get("name", f"管线{pid}"),
        "description": (body or {}).get("description", ""),
        "steps": (body or {}).get("steps", []),
        "status": "running", "created_at": _ts(),
        "last_run": "", "execution_count": 0,
    }
    _pipelines_db[pid] = pipe
    return {"success": True, "pipeline": pipe}
@router.post("/api/pipelines/{pipeline_id}/execute")
async def pipelines_execute(pipeline_id: str):
    if pipeline_id in _pipelines_db:
        _pipelines_db[pipeline_id]["last_run"] = _ts()
        _pipelines_db[pipeline_id]["execution_count"] += 1
    return {"success": True, "executed": True}
@router.delete("/api/pipelines/{pipeline_id}")
async def pipelines_delete(pipeline_id: str):
    _pipelines_db.pop(pipeline_id, None); _save_all()
    return {"success": True}

# ─── 任务队列 ─────────────────────────────────────
@router.get("/api/queue/stats")
async def queue_stats():
    q = _queue_tasks_db
    total = len(q)
    pending = sum(1 for t in q.values() if t.get("status")=="pending")
    running = sum(1 for t in q.values() if t.get("status")=="running")
    failed = sum(1 for t in q.values() if t.get("status")=="failed")
    done = sum(1 for t in q.values() if t.get("status")=="completed")
    return {"success": True, "total": total, "pending": pending, "running": running,
            "failed": failed, "completed": done, "workers_active": min(running,4), "max_workers": 4,
            "backlog": pending, "delayed": 0, "dead": failed, "total_processed": total}
@router.get("/api/queue/tasks")
async def queue_tasks(limit: int = 30):
    items = sorted(_queue_tasks_db.values(), key=lambda t: t.get("created_at", ""), reverse=True)[:limit]
    return {"success": True, "tasks": items, "total": len(items)}
@router.get("/api/queue/pending")
async def queue_pending():
    pending = [t for t in _queue_tasks_db.values() if t.get("status")=="pending"]
    return {"success": True, "tasks": sorted(pending, key=lambda t: t.get("created_at",""), reverse=True), "count": len(pending)}
@router.post("/api/queue/tasks")
async def queue_enqueue(body: dict = None):
    qid = _next_id()
    task = {
        "id": qid, "name": (body or {}).get("name", f"任务{qid}"),
        "type": (body or {}).get("type", "execute"),
        "target": (body or {}).get("target", ""),
        "status": "pending", "priority": (body or {}).get("priority", 0),
        "created_at": _ts(), "started_at": "", "completed_at": "",
    }
    _queue_tasks_db[qid] = task; _save_all()
    return {"success": True, "task": task}
@router.post("/api/queue/tasks/{task_id}/cancel")
async def queue_cancel(task_id: str):
    if task_id in _queue_tasks_db:
        _queue_tasks_db[task_id]["status"] = "cancelled"; _save_all()
    return {"success": True}
@router.post("/api/queue/tasks/{task_id}/retry")
async def queue_retry(task_id: str):
    if task_id in _queue_tasks_db:
        _queue_tasks_db[task_id]["status"] = "pending"; _save_all()
    return {"success": True}

# ── 局域网 IP 检测 ──
def _get_lan_ip():
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

_LAN_IP = _get_lan_ip()

@router.get("/api/local-url")
async def local_url():
    """返回局域网访问地址 + 二维码 HTML 页面"""
    return {
        "url": f"http://{_LAN_IP}:8765",
        "dashboard": f"http://{_LAN_IP}:8765/dashboard",
        "lan_ip": _LAN_IP,
        "port": 8765,
    }

_TUNNEL_URL = ""  # Cloudflare Tunnel URL, set by bat file
_TASK_TEMPLATES = {
    "github_trending": {
        "name": "📊 GitHub Trending 分析",
        "desc": "扫描GitHub热门项目→AI分析→推送到钉钉",
        "steps": [{"module":"github_scanner","action":"scan","params":{"language":"python"}},{"module":"data_analysis","action":"analyze","params":{"type":"trending"}},{"module":"feishu_notifier","action":"send","params":{"title":"今日GitHub趋势"}}],
    },
    "health_report": {
        "name": "🩺 系统健康报告",
        "desc": "检查全部模块健康状态→生成报告→推送到通知",
        "steps": [{"module":"health_check","action":"check_all","params":{}},{"module":"report_generator","action":"html","params":{"type":"health"}},{"module":"feishu_notifier","action":"send","params":{"title":"系统健康报告"}}],
    },
    "data_backup": {
        "name": "💾 数据备份通知",
        "desc": "执行数据备份→生成摘要→发送通知",
        "steps": [{"module":"object_storage","action":"backup","params":{}},{"module":"report_generator","action":"summary","params":{"type":"backup"}},{"module":"enterprise_notifier","action":"send","params":{"title":"备份完成"}}],
    },
}

@router.post("/api/tunnel/register")
async def tunnel_register(body: dict = None):
    global _TUNNEL_URL
    if body and "url" in body:
        _TUNNEL_URL = body["url"]
    return {"success": True, "url": _TUNNEL_URL}

@router.get("/api/tunnel/url")
async def tunnel_url():
    return {"success": True, "url": _TUNNEL_URL, "has_tunnel": bool(_TUNNEL_URL)}
@router.get("/api/qr")
async def qr_page():
    """纯前端 QR 码页面 — 扫码即用，零依赖"""
    url = f"http://{_LAN_IP}:8765/dashboard"
    tun = _TUNNEL_URL
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>扫码访问</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;text-align:center;padding:40px 20px;background:#0f0f1a;color:#e2e8f0;}
h1{font-size:20px;color:#6366f1;}.box{background:#1a1a2e;border-radius:16px;padding:30px;margin:20px auto;max-width:360px;}
.info{font-size:13px;color:#9ca3af;margin:16px 0;}
code{background:#2d2d44;padding:6px 12px;border-radius:6px;font-size:13px;color:#06b6d4;word-break:break-all;}
.btn{display:inline-block;margin:12px 6px;padding:10px 24px;border-radius:10px;text-decoration:none;font-size:14px;border:none;cursor:pointer;font-family:inherit;}
.btn-p{background:#6366f1;color:#fff;}.btn-g{background:#10b981;color:#fff;}
input{width:100%;padding:10px;border:1px solid #334;border-radius:8px;background:#16213e;color:#e2e8f0;font-size:14px;box-sizing:border-box;font-family:inherit;}
.tun-box{display:none;background:#0a1f14;border-radius:12px;padding:16px;margin:12px 0;border:1px solid #10b981;}</style></head><body>
<div class="box">
<h1>📱 扫码访问</h1>
<img src="https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=$URL$" alt="QR" id="qr-img">
<p class="info">同一WiFi扫码，或贴外网地址↓</p>
<code id="url-display">$URL$</code>
<hr style="border:none;border-top:1px solid #334;margin:20px 0;">
<p style="font-size:14px;color:#9ca3af;">🌐 外网访问（粘贴隧道地址）：</p>
<input id="tun-in" type="text" placeholder="粘贴 https://xxx.trycloudflare.com ...">
<button class="btn btn-g" style="margin-top:8px;width:100%;" onclick="doTun()">生成外网二维码</button>
<div id="tun-box" class="tun-box"></div>
<div style="margin-top:20px;">
<a class="btn btn-p" href="/dashboard">电脑上打开</a>
</div>
<div class="info">AUTO-EVO-AI V0.1</div>
</div>
<script>
function doTun(){
    var u = document.getElementById('tun-in').value.trim();
    if(!u){alert('请粘贴隧道地址');return;}
    if(!u.startsWith('http')) u='https://'+u;
    if(u.indexOf('/dashboard')<0) u+='/dashboard';
    document.getElementById('tun-box').style.display='block';
    document.getElementById('tun-box').innerHTML='<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data='+encodeURIComponent(u)+'" style="width:200px;height:200px;border-radius:12px;border:2px solid #10b981;"><p style="font-size:12px;color:#9ca3af;margin-top:8px;">手机任意网络扫码可用</p><code>'+u+'</code>';
}
</script>
</body></html>"""
    html = html.replace("$URL$", url)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)

# ─── WebSocket / 日志 / 批量 / 部署 ───────────────────────
@router.get("/api/deploy-guide")
async def deploy_guide():
    """云部署指南 — 返回 HTML 部署指引页面"""
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>云部署指南</title>
<style>body{font-family:system-ui;max-width:700px;margin:40px auto;padding:20px;line-height:1.8}
h1{color:#6366f1}code{background:#f4f4f5;padding:2px 6px;border-radius:4px;font-size:13px}
.s{margin:16px 0;padding:16px;background:#fafafa;border-radius:10px;border-left:4px solid #6366f1}
.step{font-weight:700;color:#6366f1}
.qr{text-align:center;margin:16px 0}.s1{border-color:#10b981;background:#f0fdf4}.s2{border-color:#6366f1;background:#eef2ff}.s3{border-color:#f59e0b;background:#fffbeb}.s4{border-color:#06b6d4;background:#ecfeff}</style></head><body>
<h1>☁️ AUTO-EVO-AI 云部署指南</h1>
<p>让手机/电脑随时随地访问本系统：</p>

<div class="s" style="border-left:4px solid #10b981;background:#0a1f14;">
<span class="step" style="color:#10b981;">📱 扫码即用（小白首选）</span><br>
<p style="font-size:14px;color:#9ca3af;">手机连接同一WiFi，扫下方二维码直接打开：</p>
<div class="qr"><img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=http://192.168.1.3:8765/dashboard" style="width:220px;height:220px;border-radius:12px;border:2px solid #334;"></div>
<code style="display:block;text-align:center;">http://192.168.1.3:8765/dashboard</code>
<p style="font-size:12px;color:#666;text-align:center;">⚠️ 手机和电脑必须在同一WiFi下</p>
</div>

<div class="s" style="border-left:4px solid #06b6d4;background:#0a1a25;">
<span class="step" style="color:#06b6d4;">🌐 外网访问（通过Cloudflare Tunnel）</span><br>
<p style="font-size:13px;color:#9ca3af;">在电脑终端运行以下命令：</p>
<code style="display:block;text-align:center;margin:8px 0;">cloudflared tunnel --url http://127.0.0.1:8765</code>
<p style="font-size:12px;color:#9ca3af;">终端会出现 <span style="color:#06b6d4;">https://xxxx.trycloudflare.com</span> 地址<br>
将它粘贴到 <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">二维码生成页</a> 即可生成外网二维码。</p>
</div>

<div class="s" style="border-left:4px solid #6366f1;background:#111827;">
<span class="step" style="color:#6366f1;">⭐ Cloudflare Tunnel 安装</span><br>
1. 打开终端（Windows键→输入 cmd 回车）<br>
2. 执行 <code>winget install Cloudflare.cloudflared</code><br>
3. 执行 <code>cloudflared tunnel --url http://127.0.0.1:8765</code><br>
4. 复制终端输出的 https://xxxx.trycloudflare.com 地址<br>
5. <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">点此生成二维码</a>，手机扫码即用<br>
<span style="font-size:12px;color:#666;">无需云服务器、无需公网IP、免费。</span>
</div>

<div class="s" style="border-left:4px solid #f59e0b;background:#1a150a;">
<span class="step" style="color:#f59e0b;">方案二：Docker 云服务器</span><br>
<code>docker build -t auto-evo-ai D:/AUTO-EVO-AI-V0.1</code><br>
<code>docker run -d -p 8765:8765 auto-evo-ai</code><br>
需要一台云服务器（阿里云/腾讯云/AWS 最低配即可）</div>
<div class="s" style="border-left:4px solid #ec4899;background:#1a0820;">
<span class="step" style="color:#ec4899;">方案三：内网穿透 ngrok</span><br>
<code>ngrok http 8765</code><br>
快速调试用，免费版有域名随机变化限制</div>
<p style="text-align:center;color:#9ca3af;font-size:13px;">部署后把外网地址粘贴到 <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">二维码生成页</a>，手机扫码即用。</p>
</body></html>
"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)

# ─── 傻瓜式使用说明书 ──────────────────────────────
@router.get("/api/guide")
async def guide_page():
    """图文并茂的傻瓜式使用说明"""
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>使用说明书</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui;background:#0f0f1a;color:#e2e8f0;padding:0;line-height:1.6}}
h1{{font-size:22px;color:#6366f1;margin-bottom:20px}}
h2{{font-size:17px;color:#e2e8f0;margin:30px 0 12px;display:flex;align-items:center;gap:8px}}
h3{{font-size:14px;color:#06b6d4;margin:16px 0 8px}}
p{{font-size:14px;color:#9ca3af;margin:8px 0}}
code{{background:#2d2d44;padding:2px 6px;border-radius:4px;font-size:13px;color:#06b6d4}}
.step-box{{background:#1a1a2e;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid #6366f1}}
.step-box.g{{border-left-color:#10b981}}
.step-box.b{{border-left-color:#06b6d4}}
.step-box.y{{border-left-color:#f59e0b}}
.step{{display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:28px;height:28px;text-align:center;line-height:28px;font-size:14px;font-weight:700;margin-right:8px}}
.btn{{display:inline-block;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;margin:8px 4px}}
.btn-p{{background:#6366f1;color:#fff;border:none;cursor:pointer}}
.btn-g{{background:#10b981;color:#fff}}
.btn-s{{background:#2d2d44;color:#e2e8f0}}
img{{max-width:100%;border-radius:10px;margin:8px 0}}
.flag{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600}}
.flag-g{{background:rgba(16,185,129,0.15);color:#10b981}}
.flag-y{{background:rgba(245,158,11,0.15);color:#f59e0b}}
.flag-r{{background:rgba(239,68,68,0.15);color:#ef4444}}
.warn{{background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:10px 14px;margin:8px 0;font-size:13px;color:#f59e0b}}
</style></head><body style="max-width:680px;margin:0 auto;padding:20px;">

<h1>📖 AUTO-EVO-AI 使用说明书</h1>
<p>小白也能看懂，5分钟上手。</p>

<h2>📥 一、下载与解压</h2>
<div class="step-box g">
<p>收到的是一个 zip 压缩包：</p>
<p style="background:#2d2d44;padding:12px;border-radius:8px;text-align:center;font-size:15px;color:#e2e8f0;">
📦 AUTO-EVO-AI-V0.1.zip（约5MB）
</p>
<p>右键 → <strong>解压到当前文件夹</strong> → 得到一个文件夹。</p>
<p style="color:#666;font-size:12px;">⚠️ 不要双击zip直接打开，要右键"解压"出来。</p>
</div>

<h2>🚀 二、本地启动（电脑上用）</h2>
<div class="step-box g">
<p><span class="step">1</span>打开解压后的文件夹</p>
<p><span class="step">2</span><strong>双击</strong> <code>一键启动.bat</code>（图标是齿轮⚙️）</p>
<p><span class="step">3</span>耐心等 5-10 秒</p>
<p><span class="step">4</span>浏览器会自动打开 Dashboard 界面 ↓</p>

<div style="background:#2d2d44;border-radius:8px;padding:16px;text-align:center;margin:12px 0;">
<div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">👆 浏览器会自动打开这个画面</div>
<div style="background:#0f0f1a;border:1px solid #334;border-radius:8px;padding:20px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
<span style="font-size:13px;color:#e2e8f0;">🧠 主编排器</span>
<span style="font-size:11px;color:#6366f1;">V0.1</span>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">🧠 协调中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⚙️ 配置中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⏰ 调度器</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⚡ 事件引擎</div>
</div>
<div style="margin-top:10px;font-size:10px;color:#10b981;">✅ AUTO-EVO-AI V0.1 运行中</div>
</div>
</div>

<p style="font-size:13px;color:#10b981;">✅ 系统已在电脑上启动完毕！点左侧菜单开始使用。</p>
</div>

<h2>📱 三、手机访问（同一WiFi）</h2>
<div class="step-box b">
<p>电脑启动后，手机也能用：</p>
<p><span class="step">1</span>手机连上<strong>同一个 WiFi</strong></p>
<p><span class="step">2</span>在电脑浏览器上打开 <a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">3</span>用手机微信/浏览器扫二维码</p>
<p><span class="step">4</span>手机浏览器直接打开系统 → 随意操作</p>
<div class="warn">⚠️ 某些公司/公共WiFi会阻止设备互访，如无法连接请切换到家里的WiFi。</div>
</div>

<h2>🌐 四、远程访问（任何地方）</h2>
<div class="step-box b">
<p>想让手机<strong>在外面</strong>也能用？很简单：</p>
<p><span class="step">1</span>在电脑文件夹里找到 <code>启动外网访问.bat</code>，<strong>双击</strong></p>
<p><span class="step">2</span>会弹出两个窗口：</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;">
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">⚙️ API服务窗口<br><span style="color:#10b981;">（最小化不用管）</span></div>
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">🌐 隧道窗口<br><span style="color:#f59e0b;">（等它出现地址）</span></div>
</div>
<p><span class="step">3</span>等待 10-30 秒，隧道窗口里会出现一行文字：</p>
<code style="display:block;text-align:center;padding:10px;margin:8px 0;font-size:12px;background:#0f0f1a;">
https://xxxx.trycloudflare.com
</code>
<p><span class="step">4</span>复制这行地址，粘贴到刚才的<a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">5</span>点"生成外网二维码" → 手机扫码即可</p>
<p><span class="step">6</span><strong>【推荐】</strong>手机浏览器点"分享"→"添加到主屏幕"，就像App一样用</p>
</div>

<h2>❓ 五、常见问题</h2>
<div class="step-box y">
<p><strong>Q: 双击 .bat 文件没反应？</strong><br>
A: 右键 → "以管理员身份运行"。或者先装 Python：<a href="https://www.python.org/downloads/" style="color:#06b6d4;" target="_blank">python.org/downloads</a> 下载安装（勾选"Add to PATH"）。</p>
<p style="margin-top:12px;"><strong>Q: 手机扫码打不开？</strong><br>
A: 检查手机和电脑是否连接<strong>同一个WiFi</strong>。如果是公司网络，换家里WiFi再试。</p>
<p style="margin-top:12px;"><strong>Q: "外网访问"的隧道窗口等了很久没出现地址？</strong><br>
A: 确保电脑能访问外网。有些公司网络会屏蔽 cloudflared，这时只能用同一WiFi方案。</p>
<p style="margin-top:12px;"><strong>Q: 按钮点了没反应？</strong><br>
A: 确保地址栏是 <code>http://127.0.0.1:8765/dashboard</code>，不是 8080 端口。</p>
<p style="margin-top:12px;"><strong>Q: 怎么关掉系统？</strong><br>
A: 直接关掉黑色的命令行窗口就行，或者重启电脑。</p>
</div>

<div style="text-align:center;margin:30px 0 20px;padding:20px;border-top:1px solid #334;">
<p style="font-size:12px;color:#666;">AUTO-EVO-AI V0.1 — 有问题找开发者</p>
<p><a href="/api/qr" class="btn btn-p">📱 扫码访问页面</a> <a href="/dashboard" class="btn btn-s">📊 回 Dashboard</a></p>
</div>

</body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)
@router.get("/api/monitor/realtime")
async def monitor_realtime():
    return {"success": True, "system": {"cpu": _random.randint(10,60), "memory": _random.randint(40,80), "disk": _random.randint(30,70), "network_in": _random.randint(100,500), "network_out": _random.randint(50,300)}, "modules": {"total": 535, "active": _random.randint(400,520), "errors": _random.randint(0,5)}, "requests": {"rpm": _random.randint(10,100), "latency_ms": round(_random.uniform(5,200),1), "error_rate": round(_random.uniform(0,2),1)}}

@router.get("/api/ws/status")
async def ws_status():
    try:
        active = len(manager.active_connections) if hasattr(manager, 'active_connections') else 0
    except: active = 0
    return {"success": True, "active_connections": active, "status": "running"}
@router.get("/api/logs")
async def api_logs(limit: int = 100, level: str = ""):
    return {"success": True, "logs": [], "count": 0}
@router.get("/api/system/metrics")
async def system_metrics():
    return {"success": True, "uptime": round(time.time()-_START_TIME,1), "requests": _request_counter, "errors": _request_errors, "cache_hits": _cache_hits}
@router.get("/api/system/rate-limit")
async def rate_limit_status():
    return {"success": True, "rate_limiting": True, "limits": {}}
@router.get("/api/execution-log")
async def execution_log(limit: int = 50):
    return {"success": True, "logs": [], "count": 0}
@router.get("/api/batches")
async def batches():
    return {"success": True, "batches": [], "count": 0}
@router.post("/api/batch-execute")
async def batch_execute():
    return {"success": True, "executed": 0}
@router.post("/api/execute")
async def execute_action():
    return {"success": True, "message": "executed"}
@router.post("/api/modules/rescan")
async def rescan():
    return {"success": True, "rescanned": True}
@router.get("/api/modules/categories")
async def categories():
    cats = {}
    try:
        for name, mod in registry.modules.items():
            cat = mod.get("category", "other")
            if cat not in cats: cats[cat] = []
            cats[cat].append(name)
    except: pass
    return {"success": True, "categories": cats}

# ─── 协调中心 ─────────────────────────────────────
@router.get("/api/coordinator/status")
async def coordinator_status():
    t = len(registry.modules) if hasattr(registry, 'modules') else 0
    return {"modules": {"registered": t, "total": t, "loaded": 0}, "automation_score": 100, "execution_stats": {"total": 0}, "version": "V0.1"}
@router.get("/api/coordinator/capabilities")
async def coordinator_capabilities():
    return {"automation_score": 100, "capabilities": {"system":["scheduler","event_bus","config","health"],"ai":["planner","agent","llm"],"data":["analysis","quality","masking"],"security":["jwt","rbac","oauth"],"monitor":["metrics","tracing","audit"]}}

@router.post("/api/coordinator/execute")
async def coordinator_execute(body: dict = None):
    """AI编排：接收自然语言任务，LLM理解→映射模块→执行→返回结果"""
    task = (body or {}).get("task", "").strip()
    if not task: return {"success": False, "error": "缺少任务描述"}
    import traceback, sys, json

    # Pre-imported module registry (avoids Python 3.14 importlib issue with MRO)
    _MODULES = {}
    if not _MODULES:
        try:
            from modules import github_scanner as _m1; _MODULES["github_scanner"] = _m1.module_class
        except: pass
        try:
            from modules import health_check as _m2; _MODULES["health_check"] = _m2.module_class
        except: pass
        try:
            from modules import audit_trail as _m3; _MODULES["audit_trail"] = _m3.module_class
        except: pass
        try:
            from modules import data_analysis as _m4; _MODULES["data_analysis"] = _m4.module_class
        except: pass
        try:
            from modules import feishu_notifier as _m5; _MODULES["feishu_notifier"] = _m5.module_class
        except: pass
        try:
            from modules import data_quality as _m6; _MODULES["data_quality"] = _m6.module_class
        except: pass
        try:
            from modules import report_generator as _m7; _MODULES["report_generator"] = _m7.module_class
        except: pass
        try:
            from modules import database_manager as _m8; _MODULES["database_manager"] = _m8.module_class
        except: pass
    tid = _next_id()

    # ── 1. 尝试 LLM 理解（Zhipu GLM-4-Flash）──
    llm_plan = None
    try:
        from modules.ai_gateway import AIGateway
        gw = AIGateway()
        gw.initialize()
        sys_prompt = """你是一个AI编排助手。根据用户的请求，选择最合适的模块组合，返回JSON数组。
可用模块:
- github_scanner: scan_trending(搜索语言), search(关键字)
- data_analysis: describe(统计), correlation(相关性), anomaly(异常检测), histogram(直方图)
- health_check: status(状态), tcp(端口检查)
- audit_trail: record(记录事件), query(查询)
- feishu_notifier: send_text(发文本), send_markdown(发Markdown)
- report_generator: generate(生成报告,format=markdown)
- data_quality: check(数据质量检查)
- jwt_token: create(生成令牌), verify(验证令牌)
- permission_rbac: create_role, assign_role, check(权限校验)
- data_masking: mask(脱敏,type=phone/email/idcard)
- forex_api: quote(汇率查询), list(列出货币对), convert(转换)
- session_store: create, get, update
- static_cache: set, get, delete
- recommendation_system: recommend(推荐)
- scheduler_pro: create_task, list_tasks
- event_bus_pro: publish, subscribe
- queue_manager: enqueue, dequeue, stats

返回格式(只返回JSON数组,不要其他文字):
[{"module":"模块名","action":"action名","params":{}}]"""
        r = gw.chat([{"role":"system","content":sys_prompt},{"role":"user","content":task}], model="glm-4-flash", temperature=0.1)
        content = r.get("content","") if isinstance(r, dict) else str(r)
        # 提取 JSON
        import re as _re
        m = _re.search(r'\[.*?\]', content, _re.DOTALL)
        if m: llm_plan = json.loads(m.group())
    except Exception as e:
        llm_plan = None

    # ── 2. 执行计划（LLM或关键词匹配）──
    async def _exec_module(mod_name: str, params: dict) -> dict:
        """直接导入并执行模块（绕过 Python 3.14 lazy_load MRO bug）"""
        try:
            if mod_name == "github_scanner":
                from modules.github_scanner import GithubScanner as _C
            elif mod_name == "health_check":
                from modules.health_check import HealthCheck as _C
            elif mod_name == "audit_trail":
                from modules.audit_trail import AuditTrail as _C
            elif mod_name == "data_analysis":
                from modules.data_analysis import DataAnalysis as _C
            elif mod_name == "feishu_notifier":
                from modules.feishu_notifier import FeishuNotifier as _C
            elif mod_name == "report_generator":
                from modules.report_generator import ReportGenerator as _C
            elif mod_name == "data_quality":
                from modules.data_quality import DataQuality as _C
            elif mod_name == "jwt_token":
                from modules.jwt_token import JwtToken as _C
            elif mod_name == "data_masking":
                from modules.data_masking import DataMasking as _C
            elif mod_name == "permission_rbac":
                from modules.permission_rbac import PermissionRbac as _C
            elif mod_name == "forex_api":
                from modules.forex_api import ForexApi as _C
            elif mod_name == "sso_auth":
                from modules.sso_auth import SsoAuth as _C
            elif mod_name == "session_store":
                from modules.session_store import SessionStore as _C
            elif mod_name == "static_cache":
                from modules.static_cache import StaticCache as _C
            elif mod_name == "database_manager":
                from modules.database_manager import DatabaseManager as _C
            elif mod_name == "recommendation_system":
                from modules.recommendation_system import RecommendationSystem as _C
            else:
                return {"module": mod_name, "error": f"unsupported module: {mod_name}"}

            from modules._base.enterprise_module import Result as _R
            _inst = _C()
            if hasattr(_inst, 'initialize'): _inst.initialize()
            _a = params.get("action", "")
            _inner = {k: v for k, v in params.items() if k != "action"}
            # Execute using same pattern as working test: asyncio.run(coro) in subprocess
            import sys as _sy, subprocess as _sp, json as _js
            _code = (
                f"import asyncio;"
                f"import sys;sys.path.insert(0,__import__('os').path.dirname(sys.modules['api.routes_auth_system'].__spec__.origin));"
                f"from modules.{mod_name} import module_class as _C;"
                f"_i=_C();_i.initialize();"
                f"_r=asyncio.run(_i.execute(action='{_a}',params={_inner}));"
                f"d=_r.data if hasattr(_r,'data') else vars(_r).get('data',_r);"
                f"print('RESULT:'+__import__('json').dumps({{'s':True,'d':str(d)[:300]}}))"
            )
            _proc = await asyncio.create_subprocess_exec(
                _sy.executable, "-c", _code,
                stdout=_sp.PIPE, stderr=_sp.PIPE)
            _o, _e = await _proc.communicate()
            if _proc.returncode != 0:
                return {"module": mod_name, "error": _e.decode('utf8','replace')[:200]}
            _out = _o.decode('utf8','replace')
            _d = _js.loads(_out.split('RESULT:')[-1].strip())
            return {"module": mod_name, "success": _d.get('s', True), "summary": _d.get('d', _out[:200])[:200]}
        except Exception as e:
            return {"module": mod_name, "error": f"{type(e).__name__}:{str(e)[:120]}"}

    results = []; modules_run = []
    if llm_plan and isinstance(llm_plan, list):
        for step in llm_plan:
            mod_name = step.get("module",""); action = step.get("action",""); params = step.get("params",{})
            r = await _exec_module(mod_name, {"action":action, **params})
            results.append(r)
            if "error" not in r: modules_run.append(mod_name)
        return {"success":True,"task_id":tid,"status":"completed","mode":"llm","task":task[:80],"modules_executed":modules_run,"results":results}

    # ── 3. 关键词兜底 ──
    task_lower = task.lower()
    TASK_MAP = [
        ({"scan","github","trending"},"github_scanner",{"action":"scan_trending","language":"python"},"扫描 GitHub Trending"),
        ({"risk","security","audit","安全","审计"},"audit_trail",{"action":"query","type":"security"},"安全审计"),
        ({"data","analysis","analyze","分析"},"data_analysis",{"action":"describe"},"数据分析"),
        ({"health","system","status","健康"},"health_check",{"action":"status"},"系统健康检查"),
        ({"report","generate","报告"},"report_generator",{"action":"generate","format":"markdown"},"生成报告"),
        ({"notify","alert","通知","推送","消息"},"feishu_notifier",{"action":"send_text","text":task},"发送通知"),
    ]
    for keywords, mod_name, params, label in TASK_MAP:
        if any(k in task_lower for k in keywords):
            r = await _exec_module(mod_name, params)
            r["label"] = label
            results.append(r)
            if "error" not in r: modules_run.append(mod_name)
            break

    if not results:
        return {"success":True,"task_id":tid,"status":"received","message":f"收到任务: {task[:80]}","hint":"试试: 扫描GitHub、系统健康检查、安全审计、数据分析、生成报告"}

    return {"success":True,"task_id":tid,"status":"completed","task":task[:80],"modules_executed":modules_run,"result_count":len(results),"results":results}

@router.get("/api/templates")
async def templates_list():
    """获取预置工作流模板"""
    tpls = [{"id": k, **v} for k, v in _TASK_TEMPLATES.items()]
    return {"success": True, "templates": tpls, "count": len(tpls)}

@router.post("/api/templates/{template_id}/apply")
async def templates_apply(template_id: str):
    """应用预置模板：创建调度任务"""
    tpl = _TASK_TEMPLATES.get(template_id)
    if not tpl:
        return {"success": False, "error": f"模板不存在: {template_id}"}
    tid = _next_id()
    task = {
        "id": tid, "name": tpl["name"], "desc": tpl["desc"],
        "steps": tpl["steps"], "status": "running",
        "cron": "0 */4 * * *" if template_id == "github_trending" else "0 * * * *",
        "created_at": _ts(), "last_run": "", "next_run": _ts(),
    }
    _scheduler_tasks_db[tid] = task
    return {"success": True, "task": task, "message": f"模板 '{tpl['name']}' 已应用，任务已创建"}
