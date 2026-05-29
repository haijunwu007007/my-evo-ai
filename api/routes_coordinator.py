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

router = APIRouter()

# ─── 内网穿透 ──────────────────────────────────────
@router.get("/api/tunnel/status")
    """Tunnel Status - GET /api/tunnel/status"""
    async def tunnel_status():
    return {"success": True, "tunnel_enabled": False, "public_url": None}

@router.post("/api/tunnel/register")
    """Tunnel Register - POST /api/tunnel/register"""
    async def tunnel_register(body: dict = None):
    global _TUNNEL_URL
    if body and "url" in body:
        _TUNNEL_URL = body["url"]
    return {"success": True, "url": _TUNNEL_URL}

@router.get("/api/tunnel/url")
    """Tunnel Url - GET /api/tunnel/url"""
    async def tunnel_url():
    return {"success": True, "url": _TUNNEL_URL, "has_tunnel": bool(_TUNNEL_URL)}

# ─── 局域网 & 二维码 ──────────────────────────────
@router.get("/api/local-url")
    """Local Url - GET /api/local-url"""
    async def local_url():
    return {
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
    return HTMLResponse(html)

# ─── 部署指南 ───────────────────────────────────────
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
</body></html>"""
    return HTMLResponse(html)

# ─── 使用说明书 ──────────────────────────────────────
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
📦 AUTO-EVO-AI-V0.1.zip（约5MB）</p>
<p>右键 → <strong>解压到当前文件夹</strong> → 得到一个文件夹。</p>
<p style="color:#666;font-size:12px;">⚠️ 不要双击zip直接打开，要右键"解压"出来。</p></div>

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
<span style="font-size:11px;color:#6366f1;">V0.1</span></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">🧠 协调中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⚙️ 配置中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⏰ 调度器</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">⚡ 事件引擎</div></div>
<div style="margin-top:10px;font-size:10px;color:#10b981;">✅ AUTO-EVO-AI V0.1 运行中</div></div></div>
<p style="font-size:13px;color:#10b981;">✅ 系统已在电脑上启动完毕！点左侧菜单开始使用。</p></div>

<h2>📱 三、手机访问（同一WiFi）</h2>
<div class="step-box b">
<p>电脑启动后，手机也能用：</p>
<p><span class="step">1</span>手机连上<strong>同一个 WiFi</strong></p>
<p><span class="step">2</span>在电脑浏览器上打开 <a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">3</span>用手机微信/浏览器扫二维码</p>
<p><span class="step">4</span>手机浏览器直接打开系统 → 随意操作</p>
<div class="warn">⚠️ 某些公司/公共WiFi会阻止设备互访，如无法连接请切换到家里的WiFi。</div></div>

<h2>🌐 四、远程访问（任何地方）</h2>
<div class="step-box b">
<p>想让手机<strong>在外面</strong>也能用？很简单：</p>
<p><span class="step">1</span>在电脑文件夹里找到 <code>启动外网访问.bat</code>，<strong>双击</strong></p>
<p><span class="step">2</span>会弹出两个窗口：</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;">
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">⚙️ API服务窗口<br><span style="color:#10b981;">（最小化不用管）</span></div>
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">🌐 隧道窗口<br><span style="color:#f59e0b;">（等它出现地址）</span></div></div>
<p><span class="step">3</span>等待 10-30 秒，隧道窗口里会出现一行文字：</p>
<code style="display:block;text-align:center;padding:10px;margin:8px 0;font-size:12px;background:#0f0f1a;">
https://xxxx.trycloudflare.com</code>
<p><span class="step">4</span>复制这行地址，粘贴到刚才的<a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">5</span>点"生成外网二维码" → 手机扫码即可</p>
<p><span class="step">6</span><strong>【推荐】</strong>手机浏览器点"分享"→"添加到主屏幕"，就像App一样用</p></div>

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
A: 直接关掉黑色的命令行窗口就行，或者重启电脑。</p></div>

<div style="text-align:center;margin:30px 0 20px;padding:20px;border-top:1px solid #334;">
<p style="font-size:12px;color:#666;">AUTO-EVO-AI V0.1 — 有问题找开发者</p>
<p><a href="/api/qr" class="btn btn-p">📱 扫码访问页面</a> <a href="/dashboard" class="btn btn-s">📊 回 Dashboard</a></p></div>
</body></html>"""
    return HTMLResponse(html)

# ─── JS 静态文件服务 ─────────────────────────────────
@router.get("/js/{file_path:path}")
async def serve_js(file_path: str):
    """提供前端拆分后的 JS 静态文件"""
    base = BASE_DIR / "js" / file_path
    if not base.exists() or not base.is_file():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "not found"}, status_code=404)
    ext = base.suffix.lower()
    content_type = {"js": "application/javascript", "css": "text/css", "json": "application/json"}
    ct = content_type.get(ext.lstrip("."), "application/octet-stream")
    return Response(base.read_bytes(), media_type=ct)

# ─── 协调中心 ─────────────────────────────────────
@router.get("/api/coordinator/status")
    """协调器状态"""
    async def coordinator_status():
    t = len(registry.modules) if hasattr(registry, 'modules') else 0
    return {"modules": {"registered": t, "total": t, "loaded": 0}, "automation_score": 100, "execution_stats": {"total": 0}, "version": "V0.1"}
@router.get("/api/coordinator/capabilities")
    """协调器能力列表"""
    async def coordinator_capabilities():
    return {"automation_score": 100, "capabilities": {"system":["scheduler","event_bus","config","health"],"ai":["planner","agent","llm"],"data":["analysis","quality","masking"],"security":["jwt","rbac","oauth"],"monitor":["metrics","tracing","audit"]}}

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
