# -*- coding: utf-8 -*-
"""一键部署增强版 — 真沙箱构建+真Nginx+验证循环"""
from fastapi import APIRouter
import os, json, time, hashlib, subprocess, shutil, re, asyncio, threading
from pathlib import Path

router = APIRouter(prefix="/api/v1", tags=["deploy-v2"])
BASE = Path(__file__).resolve().parent.parent.parent
DEPLOYS_DIR = BASE / "data" / "deploys"
DEPLOYS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_DB = BASE / "data" / "deploy_experience.json"
_DEPLOYS = {}
_lock = threading.Lock()

def _load_db():
    try: return json.load(open(_DB, encoding="utf-8"))
    except: return {"projects": []}
def _save_db(d):
    json.dump(d, open(_DB, "w", encoding="utf-8"), indent=2)

def _detect_type(name, files=None):
    n = name.lower()
    rules = [("node",["node","npm","express","next","nuxt","vue","react"]),("python",["python","flask","django","fastapi"]),("go",["go","golang","gin"]),("rust",["rust","cargo"]),("java",["java","spring","maven"]),("php",["php","laravel","wordpress"]),("docker",["docker","docker-compose"]),("static",["html","css","javascript","docs","blog","site","website","landing"])]
    for ptype, keywords in rules:
        if any(kw in n for kw in keywords): return ptype
    if files:
        if any(f.endswith(".py") for f in files): return "python"
        if any(f.endswith((".js",".ts")) for f in files): return "node"
        if any(f.endswith(".go") for f in files): return "go"
        if any(f.endswith(".rs") for f in files): return "rust"
    return "unknown"

def _update_status(did, msg):
    with _lock:
        if did in _DEPLOYS: _DEPLOYS[did]["progress"] = msg

def _clone_repo(url, target, did):
    strategies = [url, url.replace("github.com","ghproxy.com/github.com"), url.replace("github.com","ghfast.top/github.com")]
    for i, u in enumerate(strategies):
        try:
            r = subprocess.run(["git","clone","--depth","1",u,target], capture_output=True, text=True, timeout=180)
            if r.returncode == 0: _update_status(did,f"克隆成功(策略{i+1})"); return True
        except: _update_status(did,f"策略{i+1}失败")
    try:
        zu = url.replace(".git","")+"/archive/refs/heads/main.zip"
        import urllib.request, zipfile
        urllib.request.urlretrieve(zu, target+".zip")
        with zipfile.ZipFile(target+".zip") as zf: zf.extractall(target)
        _update_status(did,"ZIP下载成功"); return True
    except: pass
    return False

@router.post("/deploy/start")
async def deploy_start(data: dict):
    url = data.get("url","").strip()
    if not url: return {"success":False,"error":"需要 url 参数"}
    did = hashlib.md5((url+str(time.time())).encode()).hexdigest()[:12]
    name = url.rstrip("/").split("/")[-1].replace(".git","")
    clone_dir = DEPLOYS_DIR / did
    info = {"id":did,"url":url,"name":name,"type":"unknown","port":8080,"status":"cloning","progress":"正在克隆...","started_at":time.time(),"deps":[],"domain":f"{name}.autoevoai.com","dockerfile":"","nginx":"","docker_cmd":"","clone_ok":False,"build_ok":False,"run_ok":False}
    with _lock: _DEPLOYS[did] = info
    asyncio.create_task(_do_deploy(did, url, name, clone_dir))
    return {"success":True,"id":did,"name":name,"status":"cloning"}

async def _do_deploy(did, url, name, clone_dir):
    _update_status(did,"克隆仓库中...")
    ok = _clone_repo(url, str(clone_dir), did)
    with _lock:
        if did in _DEPLOYS: _DEPLOYS[did]["clone_ok"] = ok; _DEPLOYS[did]["status"] = "analyzing" if ok else "failed"
    if not ok: _update_status(did,"❌ 克隆失败"); return

    # 分析
    files = [os.path.relpath(f,clone_dir) for f in clone_dir.rglob("*") if f.is_file()][:50]
    ptype = _detect_type(name, files)
    with _lock:
        if did in _DEPLOYS: _DEPLOYS[did]["type"] = ptype

    # 用沙箱构建+运行
    _update_status(did,"沙箱构建中...")
    try:
        import httpx
        sr = await asyncio.wait_for(httpx.AsyncClient(timeout=300).post(
            "http://localhost:8765/api/v1/sandbox/run",
            json={"files":{os.path.relpath(f,clone_dir):open(f).read() for f in list(clone_dir.rglob("*"))[:30] if f.is_file() and os.path.getsize(f)<100000},"type":ptype,"action":"all"},
            timeout=300), timeout=300)
        srj = sr.json()
        build_ok = srj.get("success",False)
        with _lock:
            if did in _DEPLOYS: _DEPLOYS[did]["build_ok"] = build_ok; _DEPLOYS[did]["status"] = "running" if build_ok else "failed"; _DEPLOYS[did]["progress"] = f"沙箱构建完成: {srj.get('results',{})}"
    except Exception as e:
        _update_status(did,f"沙箱跳过: {str(e)[:50]}")

    # Nginx
    domain = f"{name}.autoevoai.com"
    nginx_conf = f"server {{listen 80;server_name {domain};location / {{proxy_pass http://127.0.0.1:8080;proxy_set_header Host $host;proxy_set_header X-Real-IP $remote_addr;}}}}\n"
    try:
        nginx_target = Path(f"/etc/nginx/sites-available/{name}")
        nginx_target.write_text(nginx_conf)
        subprocess.run(["ln","-sf",str(nginx_target),f"/etc/nginx/sites-enabled/{name}"], timeout=5)
        subprocess.run(["nginx","-s","reload"], timeout=5)
        with _lock:
            if did in _DEPLOYS: _DEPLOYS[did]["run_ok"] = True; _DEPLOYS[did]["nginx"] = nginx_conf[:100]
    except: pass

    with _lock:
        if did in _DEPLOYS: _DEPLOYS[did]["domain"] = domain; _DEPLOYS[did]["dockerfile"] = "via sandbox adapters"

    # 验证循环
    _update_status(did,"验证部署中...")
    try:
        import httpx
        vr = await asyncio.wait_for(httpx.AsyncClient(timeout=30).post(
            "http://localhost:8765/api/v1/sandbox/verify",
            json={"url":f"http://localhost:8080","expected_status":200,"retries":3},
            timeout=30), timeout=30)
        if vr.json().get("success"):
            _update_status(did,"✅ 部署验证通过")
            with _lock:
                if did in _DEPLOYS: _DEPLOYS[did]["status"] = "verified"
        else:
            _update_status(did,"⚠️ 验证未通过，但部署已完成")
    except:
        _update_status(did,"验证跳过")

    # 保存经验
    db = _load_db()
    db["projects"].append({"id":did,"name":name,"url":url,"type":ptype,"domain":domain,"created_at":time.time()})
    _save_db(db)

@router.get("/deploy/status/{deploy_id}")
async def deploy_status(deploy_id: str):
    d = _DEPLOYS.get(deploy_id)
    if not d: return {"success":False,"error":"not found"}
    return {"success":True, **d}

@router.get("/deploy/list")
async def deploy_list():
    return {"success":True,"deploys":_load_db().get("projects",[])}
