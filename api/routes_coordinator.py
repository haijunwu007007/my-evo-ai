# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 — 协同/网络路由
业务域：协调中心(AI编排)、内网穿透、网络访问(QR/部署指南/使用说明书)
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse
import time, json, logging, os, traceback, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
logger = logging.getLogger("evo.api.coordinator")

from api.infra import registry, _START_TIME, manager
from api._data_store import (
    _now, _next_id, _ts, _save_all, _LAN_IP, _TUNNEL_URL,
    _monitor_history, _scheduler_tasks_db,
)
from api._templates import QR_PAGE_HTML, DEPLOY_GUIDE_HTML, GUIDE_PAGE_HTML

router = APIRouter()

# ─── 内网穿透 ──────────────────────────────────────
@router.get("/api/tunnel/status")
async def tunnel_status():
    return {"success": True, "tunnel_enabled": False, "public_url": None}

@router.post("/api/tunnel/register")
async def tunnel_register(body: dict = None):
    global _TUNNEL_URL
    if body and "url" in body:
        _TUNNEL_URL = body["url"]
    return {"success": True, "url": _TUNNEL_URL}

@router.get("/api/tunnel/url")
async def tunnel_url():
    return {"success": True, "url": _TUNNEL_URL, "has_tunnel": bool(_TUNNEL_URL)}

# ─── 局域网 & 二维码 ──────────────────────────────
@router.get("/api/local-url")
async def local_url():
    return {
        "success": True,
        "url": f"http://{_LAN_IP}:8765",
        "dashboard": f"http://{_LAN_IP}:8765/dashboard",
        "lan_ip": _LAN_IP,
        "port": 8765,
    }

@router.get("/api/qr")
async def qr_page():
    """纯前端 QR 码页面 — 扫码即用"""
    url = f"http://{_LAN_IP}:8765/dashboard"
    tun = _TUNNEL_URL
    html = QR_PAGE_HTML.replace("$URL$", url)
    return HTMLResponse(html)

# ─── 部署指南 ───────────────────────────────────────
@router.get("/api/deploy-guide")
async def deploy_guide():
    """云部署指南 — 返回 HTML 部署指引页面"""
    return HTMLResponse(DEPLOY_GUIDE_HTML)

# ─── 使用说明书 ──────────────────────────────────────
@router.get("/api/guide")
async def guide_page():
    """图文并茂的傻瓜式使用说明"""
    return HTMLResponse(GUIDE_PAGE_HTML)

# ─── JS 静态文件服务 ─────────────────────────────────
@router.get("/js/{file_path:path}")
async def serve_js(file_path: str):
    """提供前端拆分后的 JS 静态文件"""
    base = BASE_DIR / "js" / file_path
    if not base.exists() or not base.is_file():
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": "not found"}, status_code=404)
    ext = base.suffix.lower()
    content_type = {"js": "application/javascript", "css": "text/css", "json": "application/json"}
    ct = content_type.get(ext.lstrip("."), "application/octet-stream")
    return Response(base.read_bytes(), media_type=ct)

# ─── 协调中心 ─────────────────────────────────────
@router.get("/api/coordinator/status")
async def coordinator_status():
    t = len(registry.modules) if hasattr(registry, 'modules') else 0
    return {"success": True, "modules": {"registered": t, "total": t, "loaded": 0}, "automation_score": 100, "execution_stats": {"total": 0}, "version": "V0.1"}
@router.get("/api/coordinator/capabilities")
async def coordinator_capabilities():
    return {"success": True, "automation_score": 100, "capabilities": {"system":["scheduler","event_bus","config","health"],"ai":["planner","agent","llm"],"data":["analysis","quality","masking"],"security":["jwt","rbac","oauth"],"monitor":["metrics","tracing","audit"]}}

@router.post("/api/coordinator/execute")
async def coordinator_execute(body: dict = None):
    """AI编排：接收自然语言任务，LLM理解→映射模块→执行→返回结果"""
    task = (body or {}).get("task", "").strip()
    if not task: return {"success": False, "error": "缺少任务描述"}
    import traceback, sys, json

    tid = _next_id()

    # ── 1. 尝试 LLM 理解（Zhipu GLM-4-Flash）──
    llm_plan = None
    try:
        from modules.ai_gateway import AIGateway
        gw = AIGateway()
        gw.initialize()
        sys_prompt = """你是一个AI编排助手。根据用户的请求，选择最合适的模块组合，返回JSON数组。
可用模块(共27个):
- github_scanner: scan_trending(编程语言), search(关键词)
- report_generator: generate(format=markdown/html)
- permission_rbac: create_role, assign_role, check(权限校验)
- data_masking: mask(type=phone/email/idcard)
- static_cache: set(key,value), get(key), delete(key)
- recommendation_system: recommend(场景)
- jwt_token: create(claims), verify(token), refresh(refresh_token), revoke(token_id)
- audit_trail: query(type=security/operation), log(action,detail)
- data_encrypt: encrypt(plaintext), decrypt(ciphertext), hash(data)
- web_remote: exec(cmd), history, status
- key_insights: describe(data), correlation(series_a,series_b), anomaly_detect(time_series)
- oauth_provider: authorize(client_id,scope), token(code)
- sso_auth: login(username,password), validate(session_id), logout(session_id)
- scheduler_pro: create(name,cron,target), list, pause(task_id), resume(task_id)
- file_watcher: watch(path), unwatch(path), status
- postgres_db: query(sql), execute(sql), tables
- forex_api: rate(from_currency,to_currency), rates(base=USD)
- firewall_rules: list, add(rule), remove(rule_id), check(ip,port)
- biometric_auth: enroll(user_id,data), verify(user_id,data), identify(data)
- database_manager: backup, restore(path), optimize
- auto_update: check, apply(version), rollback
- cloud_sync: push(local_path,remote_path), pull(remote_path,local_path), status
- oauth_server: register(client_name,redirect_uri), issue(client_id,user_id)
- evo_plugin_market: search(keyword), install(plugin_id), uninstall(plugin_id), list
- heatmap_generator: generate(data,width,height), stats
- query_cache_layer: get(key), set(key,value,ttl), invalidate(pattern), stats
- openinterpreter: run(code), install(package), analyze(file_path)

返回格式(只返回JSON数组,不要其他文字):
[{"module":"模块名","action":"action名","params":{}}]"""
        r = gw.chat([{"role":"system","content":sys_prompt},{"role":"user","content":task}], model="glm-4-flash", temperature=0.1)
        content = r.get("content","") if isinstance(r, dict) else str(r)
        import re as _re
        m = _re.search(r'\[.*?\]', content, _re.DOTALL)
        if m: llm_plan = json.loads(m.group())
    except Exception as e:
        llm_plan = None

    # ── 2. 执行计划 ──
    async def _exec_module(mod_name: str, params: dict) -> dict:
        try:
            import importlib as _il
            _mod = _il.import_module(f'modules.{mod_name}')
            if not hasattr(_mod, 'module_class'):
                return {"module": mod_name, "error": f"module_class not found"}
            _C = _mod.module_class
            _inst = _C()
            if hasattr(_inst, 'initialize'): _inst.initialize()
            _a = params.get("action", "")
            _inner = {k: v for k, v in params.items() if k != "action"}

            import sys as _sy, subprocess as _sp, json as _js
            _code = (
                "import asyncio;"
                "import sys;sys.path.insert(0,__import__('os').path.dirname(sys.modules['api.routes_coordinator'].__spec__.origin));"
                f"from modules.{mod_name} import module_class as _C;"
                "_i=_C();_i.initialize();"
                f"_r=asyncio.run(_i.execute(action='{_a}',params={_inner}));"
                "d=_r.data if hasattr(_r,'data') else vars(_r).get('data',_r);"
                "top5=[];rs=d.get('results',d.get('repos',[]));"
                "for r in rs[:]: top5.append({'name':r.get('full_name',''),'lang':r.get('language',''),'stars':r.get('stars',0),'desc':(r.get('description','') or '')[:80]});"
                "d['top_repos']=top5;d['total_count']=len(rs);"
                "print('RESULT:'+__import__('json').dumps({'s':d.get('success',True),'count':d.get('count',len(rs)),'total':len(rs),'top':top5},ensure_ascii=False))"
            )
            _proc = await asyncio.create_subprocess_exec(
                _sy.executable, "-c", _code,
                stdout=_sp.PIPE, stderr=_sp.PIPE)
            _o, _e = await _proc.communicate()
            if _proc.returncode != 0:
                return {"module": mod_name, "error": _e.decode('utf8','replace')[:200]}
            _out = _o.decode('utf8','replace')
            _d = _js.loads(_out.split('RESULT:')[-1].strip())
            top_repos = _d.get('top', [])
            summary = "; ".join([f"#{i+1} {r['name']}({r['stars']}⭐)" for i, r in enumerate(top_repos)]) if top_repos else _d.get('error', 'done')
            return {"module": mod_name, "success": _d.get('s', True), "summary": summary, "total_count": _d.get('total', 0), "count": _d.get('count', 0)}
        except Exception as e:
            return {"module": mod_name, "error": f"{type(e).__name__}:{str(e)[:120]}"}

    import asyncio
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
        ({"jwt","token","认证"},"jwt_token",{"action":"create","claims":{"sub":"user"}},"JWT令牌管理"),
        ({"audit","security","审计","安全"},"audit_trail",{"action":"query","type":"security"},"安全审计"),
        ({"encrypt","加密","解密","hash"},"data_encrypt",{"action":"encrypt"},"数据加密"),
        ({"shell","cmd","命令","执行"},"web_remote",{"action":"exec","cmd":"echo ok"},"远程命令执行"),
        ({"key","insight","分析"},"key_insights",{"action":"describe"},"关键洞察分析"),
        ({"oauth","授权"},"oauth_provider",{"action":"authorize"},"OAuth授权"),
        ({"sso","login","登录","认证"},"sso_auth",{"action":"validate"},"SSO单点登录"),
        ({"scheduler","调度","定时"},"scheduler_pro",{"action":"list"},"调度管理"),
        ({"file","watch","监听"},"file_watcher",{"action":"status"},"文件监听"),
        ({"postgres","sql","数据库"},"postgres_db",{"action":"tables"},"PostgreSQL查询"),
        ({"forex","汇率","外汇"},"forex_api",{"action":"rate","from_currency":"USD","to_currency":"CNY"},"外汇汇率"),
        ({"firewall","防火墙"},"firewall_rules",{"action":"list"},"防火墙规则"),
        ({"biometric","生物","指纹"},"biometric_auth",{"action":"status"},"生物认证"),
        ({"backup","备份"},"database_manager",{"action":"backup"},"数据库备份"),
        ({"update","upgrade","升级"},"auto_update",{"action":"status"},"自动更新"),
        ({"sync","同步","cloud"},"cloud_sync",{"action":"status"},"云同步"),
        ({"plugin","market","市场"},"evo_plugin_market",{"action":"list"},"插件市场"),
        ({"heatmap","热力图"},"heatmap_generator",{"action":"stats"},"热力图生成"),
        ({"cache","缓存"},"query_cache_layer",{"action":"stats"},"缓存管理"),
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
        return {"success":True,"task_id":tid,"status":"received","message":f"收到任务: {task[:80]}","hint":"试试: 扫描GitHub、系统健康检查、数据分析、生成报告"}
    return {"success":True,"task_id":tid,"status":"completed","task":task[:80],"modules_executed":modules_run,"result_count":len(results),"results":results}
