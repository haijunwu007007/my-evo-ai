# -*- coding: utf-8 -*-
"""一键部署增强版 — 真Docker构建运行+镜像克隆+复杂项目支持"""
from fastapi import APIRouter
import os, json, time, hashlib, subprocess, shutil, re, asyncio, threading, urllib.request, zipfile, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("evo.deploy")
router = APIRouter(prefix="/api/v1", tags=["deploy-v2"])
BASE = Path(__file__).resolve().parent.parent.parent
DEPLOYS_DIR = BASE / "data" / "deploys"
DEPLOYS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_DB = BASE / "data" / "deploy_experience.json"
_DEPLOYS: dict = {}
_lock = threading.Lock()

def _load_db():
    try: return json.load(open(_DB, encoding="utf-8"))
    except: return {"projects": []}
def _save_db(d): json.dump(d, open(_DB, "w", encoding="utf-8"), indent=2)

def _detect_type(name: str) -> dict:
    n = name.lower()
    for ptype, kws in [
        ("node",["node","npm","express","next","nuxt","vue","react","angular"]),
        ("python",["python","flask","django","fastapi","pytorch","pip"]),
        ("go",["go","golang","gin","echo"]),
        ("rust",["rust","cargo"]),
        ("java",["java","spring","maven"]),
        ("php",["php","laravel","wordpress","composer"]),
        ("docker",["docker","docker-compose","container"]),
        ("static",["html","css","javascript","docs","blog","landing"]),
        ("flutter",["flutter","dart"]),
    ]:
        if any(kw in n for kw in kws): return {"type": ptype, "score": 90}
    return {"type": "unknown", "score": 10}

def _analyze(repo_path: str) -> dict:
    r = {"deps": [], "port": 8080, "has_dockerfile": False, "has_compose": False}
    try:
        for root, dirs, fnames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules","__pycache__")]
            for f in fnames:
                fp = os.path.join(root, f)
                try: c = open(fp, encoding="utf-8", errors="replace").read()
                except: continue
                if f == "package.json":
                    d = json.loads(c)
                    r["deps"] = list((d.get("dependencies",{}) or {}).keys())[:15]
                    r["port"] = 3000
                elif f == "requirements.txt":
                    r["deps"] = [l.split("==")[0] for l in c.splitlines() if l.strip() and not l.startswith("#")][:15]
                    r["port"] = 8000
                elif f == "Dockerfile":
                    r["has_dockerfile"] = True
                    m = re.search(r'EXPOSE\s+(\d+)', c)
                    if m: r["port"] = int(m.group(1))
                elif "docker-compose" in f.lower():
                    r["has_compose"] = True
    except: pass
    return r

_DF = {
    "node": 'FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE {port}\nCMD ["npm","start"]\n',
    "python": 'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt ./\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE {port}\nCMD ["python","app.py"]\n',
    "go": 'FROM golang:1.22-alpine AS build\nWORKDIR /app\nCOPY go.* ./\nRUN go mod download\nCOPY . .\nRUN go build -o /app/server .\nFROM alpine:3.19\nCOPY --from=build /app/server /app/server\nEXPOSE {port}\nCMD ["/app/server"]\n',
    "rust": 'FROM rust:1.77-slim AS build\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\nFROM debian:bookworm-slim\nCOPY --from=build /app/target/release/* /app/\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "java": 'FROM maven:3-eclipse-temurin-21 AS build\nWORKDIR /app\nCOPY pom.xml .\nRUN mvn dependency:go-offline\nCOPY . .\nRUN mvn package -DskipTests\nFROM eclipse-temurin:21-jre\nCOPY --from=build /app/target/*.jar /app/app.jar\nEXPOSE {port}\nCMD ["java","-jar","/app/app.jar"]\n',
    "php": 'FROM php:8.2-apache\nWORKDIR /var/www/html\nCOPY . .\nRUN docker-php-ext-install pdo pdo_mysql\nEXPOSE 80\nCMD ["apache2-foreground"]\n',
    "static": 'FROM nginx:alpine\nCOPY . /usr/share/nginx/html\nEXPOSE 80\nCMD ["nginx","-g","daemon off;"]\n',
    "flutter": 'FROM nginx:alpine\nCOPY build/web /usr/share/nginx/html\nEXPOSE 80\nCMD ["nginx","-g","daemon off;"]\n',
    "unknown": 'FROM alpine:3.19\nWORKDIR /app\nCOPY . .\nEXPOSE {port}\nCMD ["echo","Container ready"]\n',
}

def _dockerfile(ptype: str, port: int = 8080) -> str:
    return _DF.get(ptype, _DF["unknown"]).format(port=port)

def _clone(url: str, target: str) -> tuple[bool, str]:
    """克隆 — 直连→镜像→ZIP"""
    for label, u in [
        ("直连", url),
        ("ghproxy", url.replace("github.com","ghproxy.com/github.com")),
        ("ghfast", url.replace("github.com","ghfast.top/github.com")),
    ]:
        try:
            r = subprocess.run(["git","clone","--depth","1",u,target], capture_output=True, text=True, timeout=120)
            if r.returncode == 0: return True, f"✅ {label}"
        except: pass
    # ZIP兜底
    for suffix in ["/archive/refs/heads/main.zip", "/archive/refs/heads/master.zip"]:
        try:
            zu = url.rstrip("/").rstrip(".git") + suffix
            zt = target + ".zip"
            urllib.request.urlretrieve(zu, zt)
            with zipfile.ZipFile(zt) as z: z.extractall(target)
            os.remove(zt)
            return True, "✅ ZIP下载"
        except: pass
    return False, "❌ 全部克隆策略失败"

@router.post("/deploy/start")
async def deploy_start(data: dict):
    url = data.get("url", "").strip()
    if not url: return {"success": False, "error": "需要 url"}
    did = hashlib.md5((url + str(time.time())).encode()).hexdigest()[:12]
    name = url.rstrip("/").split("/")[-1].replace(".git","")
    ptype = _detect_type(name)["type"]
    info = {"id": did, "name": name, "type": ptype, "status": "cloning",
            "progress": "排队中...", "port": 0, "deps": [], "clone_ok": False,
            "build_ok": False, "run_ok": False, "dockerfile": "", "nginx": "",
            "domain": f"{name}.autoevoai.com", "docker_cmd": ""}
    with _lock: _DEPLOYS[did] = info
    t = threading.Thread(target=_run_deploy, args=(did, url, name, ptype), daemon=True)
    t.start()
    return {"success": True, "id": did, "name": name, "type": ptype, "status": "cloning"}

def _run_deploy(did: str, url: str, name: str, ptype: str):
    def st(msg):
        with _lock:
            if did in _DEPLOYS: _DEPLOYS[did]["progress"] = msg
    clone_dir = DEPLOYS_DIR / did
    st("克隆仓库...")
    ok, msg = _clone(url, str(clone_dir))
    with _lock:
        if did in _DEPLOYS:
            _DEPLOYS[did]["clone_ok"] = ok
            _DEPLOYS[did]["status"] = "analyzing" if ok else "failed"
    st(msg if ok else "克隆失败")

    if not ok:
        st("❌ 克隆失败，部署终止")
        return

    # 分析
    st("分析源码...")
    a = _analyze(str(clone_dir))
    port = a.get("port", 8080)
    deps = a.get("deps", [])
    has_df = a.get("has_dockerfile", False)

    # Dockerfile
    st("生成配置...")
    df = _dockerfile(ptype, port)
    if not has_df:
        (clone_dir / "Dockerfile").write_text(df, encoding="utf-8")
    (OUTPUT_DIR / f"{did}_Dockerfile").write_text(df, encoding="utf-8")

    # Nginx
    domain = f"{name}.autoevoai.com"
    ng = f"""server {{\n    listen 80;\n    server_name {domain};\n    location / {{\n        proxy_pass http://127.0.0.1:{port};\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n    }}\n}}\n"""
    (OUTPUT_DIR / f"{did}_nginx.conf").write_text(ng, encoding="utf-8")
    # Try to install nginx config
    try:
        (Path(f"/etc/nginx/sites-available/{domain}")).write_text(ng, encoding="utf-8")
        subprocess.run(["ln","-sf",f"/etc/nginx/sites-available/{domain}",f"/etc/nginx/sites-enabled/{domain}"], timeout=5)
        subprocess.run(["nginx","-s","reload"], timeout=5, capture_output=True)
    except: pass

    # Docker 构建
    st("Docker构建中...")
    cn = f"evo_{did[:10]}"
    build_ok = False
    try:
        r = subprocess.run(["docker","build","-t",cn,str(clone_dir)], capture_output=True, text=True, timeout=300)
        build_ok = r.returncode == 0
        if build_ok:
            subprocess.run(["docker","rm","-f",cn], capture_output=True, timeout=10)
            subprocess.run(["docker","run","-d","--name",cn,"--restart","unless-stopped","-p",f"{port}:{port}",cn], capture_output=True, timeout=30)
            st(f"✅ {cn} 运行中: 端口 {port}")
        else:
            st(f"⚠️ 构建失败: {r.stderr[:100]}")
    except Exception as e:
        st(f"⚠️ Docker跳过: {str(e)[:50]}")

    with _lock:
        if did in _DEPLOYS:
            _DEPLOYS[did].update({"port": port, "deps": deps, "build_ok": build_ok,
                "run_ok": build_ok, "status": "running" if build_ok else "built",
                "dockerfile": df[:200], "nginx": ng[:200], "domain": domain,
                "docker_cmd": f"docker run -d --name {cn} -p {port}:{port} {cn}"})

    # Save experience
    db = _load_db()
    db["projects"].append({"id": did, "name": name, "url": url, "type": ptype, "port": port, "deps": deps, "domain": domain, "created_at": time.time()})
    _save_db(db)

@router.get("/deploy/status/{deploy_id}")
async def deploy_status(deploy_id: str):
    with _lock: d = _DEPLOYS.get(deploy_id, {})
    if not d: return {"success": False, "error": "not found"}
    return {"success": True, **d}

@router.get("/deploy/list")
async def deploy_list():
    return {"success": True, "deploys": _load_db().get("projects", [])}

@router.delete("/deploy/stop/{deploy_id}")
async def deploy_stop(deploy_id: str):
    with _lock:
        d = _DEPLOYS.get(deploy_id)
        if d:
            cn = f"evo_{deploy_id[:10]}"
            try: subprocess.run(["docker","rm","-f",cn], capture_output=True, timeout=10)
            except: pass
    return {"success": True}
