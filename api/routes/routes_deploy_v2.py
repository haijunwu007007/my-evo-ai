# -*- coding: utf-8 -*-
"""一键部署增强版 — 真Docker构建+Monorepo+微服务+K8s支持"""
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

def _detect_type(name: str, files: list = None) -> dict:
    n = name.lower()
    rules = [
        ("node", ["node","npm","express","next","nuxt","vue","react","angular","svelte","webpack","vite"]),
        ("python", ["python","flask","django","fastapi","pytorch","tensorflow","scikit","pip","conda"]),
        ("go", ["go","golang","gin","echo","fiber"]),
        ("rust", ["rust","cargo","rs"]),
        ("java", ["java","spring","maven","gradle","tomcat"]),
        ("php", ["php","laravel","symfony","wordpress","composer"]),
        ("flutter", ["flutter","dart"]),
        ("static", ["html","css","javascript","docs","blog","website","landing"]),
        ("c_cpp", ["c++","cpp","c--","c","makefile","cmake","cmakelists"]),
        ("dotnet", ["c#","dotnet","asp.net","blazor","nuget","csharp"]),
        ("elixir", ["elixir","phoenix"]),
        ("haskell", ["haskell","stack","cabal"]),
        ("scala", ["scala","sbt"]),
        ("swift", ["swift","xcode","ios","macos"]),
        ("zig", ["zig"]),
        ("deno", ["deno"]),
    ]
    for ptype, keywords in rules:
        if any(kw in n for kw in keywords):
            return {"type": ptype, "score": 90}
    if files:
        if any(f.endswith((".py")) for f in files): return {"type":"python","score":60}
        if any(f.endswith((".js",".jsx",".ts",".tsx")) for f in files): return {"type":"node","score":60}
        if any(f.endswith(".go") for f in files): return {"type":"go","score":60}
        if any(f.endswith(".java") for f in files): return {"type":"java","score":60}
        if any(f.endswith((".yaml",".yml")) for f in files): return {"type":"docker","score":60}
        if any(os.path.basename(f) in ("index.html","index.htm") for f in files): return {"type":"static","score":50}
        if any(f.endswith(".c") or f.endswith(".cpp") or f.endswith(".cc") or f.endswith(".cxx") for f in files): return {"type":"c_cpp","score":60}
        if any(f.endswith(".cs") or f.endswith(".vb") for f in files): return {"type":"dotnet","score":60}
        if any(f.endswith(".ex") or f.endswith(".exs") for f in files): return {"type":"elixir","score":60}
        if any(f.endswith(".hs") for f in files): return {"type":"haskell","score":60}
        if any(f.endswith(".scala") for f in files): return {"type":"scala","score":60}
        if any(f.endswith(".swift") for f in files): return {"type":"swift","score":60}
        if any(f.endswith(".zig") for f in files): return {"type":"zig","score":60}
    return {"type": "unknown", "score": 10}

def _analyze_source(repo_path: str) -> dict:
    """源码分析 — 支持 Monorepo/微服务/Docker Compose"""
    result = {"deps":[],"port":None,"env_vars":[],"build_cmd":None,"run_cmd":None,"files":[],"has_dockerfile":False,"has_compose":False,"is_monorepo":False,"monorepo_type":None,"packages":[],"services":[],"dockerfiles":[],"readme":""}
    try:
        for root, dirs, fnames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__" and d != "target"]
            for f in fnames:
                fp = os.path.join(root, f); rel = os.path.relpath(fp, repo_path)
                result["files"].append(rel)
                try: c = open(fp, encoding="utf-8", errors="replace").read()
                except: continue

                # Monorepo 检测
                if rel == "pnpm-workspace.yaml": result.update({"is_monorepo":True,"monorepo_type":"pnpm"})
                elif rel == "turbo.json": result.update({"is_monorepo":True,"monorepo_type":"turbo"})
                elif rel == "nx.json": result.update({"is_monorepo":True,"monorepo_type":"nx"})
                elif rel == "lerna.json": result.update({"is_monorepo":True,"monorepo_type":"lerna"})
                elif rel == "rush.json": result.update({"is_monorepo":True,"monorepo_type":"rush"})
                elif rel == "package.json" and os.path.dirname(rel) != ".":
                    result["packages"].append(os.path.dirname(rel))
                elif rel == "docker-compose.yml" or rel == "docker-compose.yaml":
                    result["has_compose"] = True
                    # 提取所有 service 名称
                    for m in re.finditer(r'^\s+(\w[\w-]*):', c, re.MULTILINE):
                        result["services"].append(m.group(1))
                    for m in re.finditer(r'"(\d+):\d+', c):
                        result["port"] = int(m.group(1))
                elif rel == "Dockerfile": result["has_dockerfile"] = True; result["dockerfiles"].append(rel)
                elif re.search(r'Dockerfile\.\w+$', rel): result["dockerfiles"].append(rel)
                elif rel == "README.md": result["readme"] = c[:500]
                # 边缘构建系统检测
                elif rel == "Makefile" or rel.lower() == "makefile": result["build_cmd"] = "make"
                elif rel == "CMakeLists.txt": result["build_cmd"] = "cmake --build ."
                elif rel == "build.sh" or rel == "compile.sh" or rel == "build": result["build_cmd"] = f"./{rel}"
                elif rel == "gradlew": result["build_cmd"] = "./gradlew build"
                elif rel == "mvnw": result["build_cmd"] = "./mvnw package"
                elif rel == "Cargo.toml" and not result.get("build_cmd"): result["build_cmd"] = "cargo build --release"
                elif rel == "mix.exs": result["build_cmd"] = "mix compile"
                elif rel == "stack.yaml": result["build_cmd"] = "stack build"
                elif rel == "build.sbt": result["build_cmd"] = "sbt compile"
                elif rel == "package.json" and os.path.dirname(rel) == "." and not result.get("build_cmd"):
                    d2 = json.loads(c); result["build_cmd"] = d2.get("scripts",{}).get("build"); result["run_cmd"] = d2.get("scripts",{}).get("start")
    except: pass
    result["files"] = result["files"][:30]
    if not result["port"]: result["port"] = 8080
    return result

_DOCKER_TEMPLATES = {
    "node": 'FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE {port}\nCMD ["npm", "start"]\n',
    "python": 'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt ./\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE {port}\nCMD ["python", "app.py"]\n',
    "go": 'FROM golang:1.22-alpine AS build\nWORKDIR /app\nCOPY go.* ./\nRUN go mod download\nCOPY . .\nRUN go build -o /app/server .\nFROM alpine:3.19\nCOPY --from=build /app/server /app/server\nEXPOSE {port}\nCMD ["/app/server"]\n',
    "rust": 'FROM rust:1.77-slim AS build\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\nFROM debian:bookworm-slim\nCOPY --from=build /app/target/release/* /app/\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "java": 'FROM maven:3-eclipse-temurin-21 AS build\nWORKDIR /app\nCOPY pom.xml .\nRUN mvn dependency:go-offline\nCOPY . .\nRUN mvn package -DskipTests\nFROM eclipse-temurin:21-jre\nCOPY --from=build /app/target/*.jar /app/app.jar\nEXPOSE {port}\nCMD ["java", "-jar", "/app/app.jar"]\n',
    "php": 'FROM php:8.2-apache\nWORKDIR /var/www/html\nCOPY . .\nRUN docker-php-ext-install pdo pdo_mysql\nEXPOSE {port}\nCMD ["apache2-foreground"]\n',
    "static": 'FROM nginx:alpine\nCOPY . /usr/share/nginx/html\nEXPOSE 80\nCMD ["nginx", "-g", "daemon off;"]\n',
    "c_cpp": 'FROM gcc:13-bookworm AS build\nWORKDIR /app\nCOPY . .\nRUN if [ -f CMakeLists.txt ]; then cmake --build .; elif [ -f Makefile ]; then make; else gcc -o /app/app *.c -lm; fi\nFROM debian:bookworm-slim\nCOPY --from=build /app/app /app/app\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "dotnet": 'FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build\nWORKDIR /app\nCOPY . .\nRUN dotnet publish -c Release -o /app/out\nFROM mcr.microsoft.com/dotnet/aspnet:8.0\nWORKDIR /app\nCOPY --from=build /app/out .\nEXPOSE {port}\nCMD ["dotnet", "app.dll"]\n',
    "elixir": 'FROM elixir:1.17-alpine AS build\nWORKDIR /app\nCOPY mix.exs mix.lock ./\nRUN mix deps.get\nCOPY . .\nRUN mix compile\nFROM elixir:1.17-alpine\nCOPY --from=build /app .\nEXPOSE {port}\nCMD ["mix", "run"]\n',
    "haskell": 'FROM haskell:9.6-slim AS build\nWORKDIR /app\nCOPY stack.yaml package.yaml ./\nCOPY src/ ./src/\nRUN stack build\nFROM debian:bookworm-slim\nCOPY --from=build /app/.stack-work/dist/*/build/*/app /app/app\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "scala": 'FROM sbtscala/scala-sbt:eclipse-temurin-21-22.4.0_1.10.10_3.5.2 AS build\nWORKDIR /app\nCOPY build.sbt ./\nCOPY src/ ./src/\nRUN sbt compile\nFROM eclipse-temurin:21-jre\nCOPY --from=build /app/target/scala-*/*.jar /app/app.jar\nEXPOSE {port}\nCMD ["java", "-jar", "/app/app.jar"]\n',
    "zig": 'FROM ziglang/zig:0.14 AS build\nWORKDIR /app\nCOPY . .\nRUN zig build-exe -O ReleaseFast src/main.zig --name app\nFROM alpine:3.19\nCOPY --from=build /app/app /app/app\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "deno": 'FROM denoland/deno:alpine\nWORKDIR /app\nCOPY . .\nRUN deno cache main.ts\nEXPOSE {port}\nCMD ["deno", "run", "-A", "main.ts"]\n',
    "unknown": 'FROM alpine:3.19\nRUN apk add --no-cache bash curl make gcc musl-dev\nWORKDIR /app\nCOPY . .\nRUN if [ -f Makefile ]; then make; elif [ -f build.sh ]; then chmod +x build.sh && ./build.sh; fi\nEXPOSE {port}\nCMD ["./app || echo Container ready"]\n',
}

# Monorepo 专用构建模板
_MONOREPO_DOCKERFILES = {
    "pnpm": 'FROM node:20-alpine\nRUN npm install -g pnpm\nWORKDIR /app\nCOPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./\nCOPY packages/ ./packages/\nRUN pnpm install\nRUN pnpm build\nEXPOSE {port}\nCMD ["pnpm", "start"]\n',
    "turbo": 'FROM node:20-alpine\nRUN npm install -g turbo\nWORKDIR /app\nCOPY package.json turbo.json ./\nCOPY apps/ ./apps/\nCOPY packages/ ./packages/\nRUN npm install\nRUN turbo build\nEXPOSE {port}\nCMD ["npm", "start"]\n',
    "nx": 'FROM node:20-alpine\nRUN npm install -g nx\nWORKDIR /app\nCOPY package.json nx.json ./\nCOPY apps/ ./apps/\nCOPY libs/ ./libs/\nRUN npm install\nRUN nx build\nEXPOSE {port}\nCMD ["npm", "start"]\n',
    "lerna": 'FROM node:20-alpine\nRUN npm install -g lerna\nWORKDIR /app\nCOPY package.json lerna.json ./\nCOPY packages/ ./packages/\nRUN npm install\nRUN lerna run build\nEXPOSE {port}\nCMD ["npm", "start"]\n',
}

# K8s yaml 模板
_K8S_YAMLS = {
    "deployment": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  labels:
    app: {name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {name}:latest
        ports:
        - containerPort: {port}
        env:
        - name: PORT
          value: "{port}"
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
spec:
  selector:
    app: {name}
  ports:
  - port: {port}
    targetPort: {port}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
spec:
  rules:
  - host: {name}.autoevoai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {name}
            port:
              number: {port}
""",
    "compose": """version: '3.8'
services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - PORT={port}
    restart: unless-stopped
"""
}

def _generate_compose(name: str, port: int, services: list = None) -> str:
    if services:
        y = f"version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - \"{port}:{port}\"\n    restart: unless-stopped\n"
        for s in services:
            y += f"  {s}:\n    image: {s}:latest\n    ports:\n      - \"{s}:{s}\"\n"
        return y
    return _K8S_YAMLS["compose"].format(name=name, port=port)

def _clone_repo(url: str, target: str, did: str) -> bool:
    strategies = [url, url.replace("github.com","ghproxy.com/github.com")]
    for i, u in enumerate(strategies):
        try:
            r = subprocess.run(["git","clone","--depth","1",u,target], capture_output=True, text=True, timeout=120)
            if r.returncode == 0: _update_status(did,f"克隆成功"); return True
        except: _update_status(did,f"策略{i+1}失败")
    try:
        zurl = url.rstrip("/").replace(".git","") + "/archive/refs/heads/main.zip"
        import urllib.request, zipfile
        urllib.request.urlretrieve(zurl, target+".zip")
        with zipfile.ZipFile(target+".zip") as zf: zf.extractall(target)
        _update_status(did,"ZIP下载成功"); return True
    except: pass
    return False

def _update_status(did: str, msg: str):
    with _lock:
        if did in _DEPLOYS: _DEPLOYS[did]["progress"] = msg

@router.post("/deploy/start")
async def deploy_start(data: dict):
    url = data.get("url","").strip()
    if not url: return {"success":False,"error":"需要 url"}
    did = hashlib.md5((url+str(time.time())).encode()).hexdigest()[:12]
    name = url.rstrip("/").split("/")[-1].replace(".git","")
    clone_dir = DEPLOYS_DIR / did
    info = {"id":did,"url":url,"name":name,"type":"detecting","port":8080,"status":"cloning","progress":"克隆中...","started_at":time.time(),"deps":[],"domain":f"{name}.autoevoai.com","is_monorepo":False,"has_compose":False,"services":[],"dockerfile":"","compose":"","k8s":"","clone_ok":False,"build_ok":False,"run_ok":False}
    with _lock: _DEPLOYS[did] = info
    asyncio.create_task(_do_deploy(did, url, name, clone_dir))
    return {"success":True,"id":did,"name":name,"type":"detecting","status":"cloning"}

async def _do_deploy(did: str, url: str, name: str, clone_dir: Path):
    _update_status(did,"克隆仓库...")
    ok = _clone_repo(url, str(clone_dir), did)
    with _lock: d = _DEPLOYS.get(did,{}); d["clone_ok"]=ok; d["status"]="analyzing" if ok else "failed"; d["progress"]="分析中..." if ok else "克隆失败"; _DEPLOYS[did]=d
    if not ok: return

    analysis = _analyze_source(str(clone_dir))
    ptype = _detect_type(name, analysis["files"])["type"]
    port = analysis.get("port",8080)
    is_monorepo = analysis.get("is_monorepo",False)
    mr_type = analysis.get("monorepo_type")
    has_compose = analysis.get("has_compose",False)
    services = analysis.get("services",[])
    deps = analysis.get("deps",[])

    with _lock:
        _DEPLOYS[did].update({"type":ptype,"port":port,"deps":deps,"is_monorepo":is_monorepo,"has_compose":has_compose,"services":services,"status":"building","progress":"生成部署配置..."})

    # 生成 Dockerfile
    df_path = clone_dir / "Dockerfile"
    if is_monorepo and mr_type and mr_type in _MONOREPO_DOCKERFILES:
        dockerfile = _MONOREPO_DOCKERFILES[mr_type].format(port=port)
    elif not (clone_dir / "Dockerfile").exists():
        dockerfile = _DOCKER_TEMPLATES.get(ptype, _DOCKER_TEMPLATES["unknown"]).format(port=port)
    else:
        dockerfile = open(clone_dir / "Dockerfile").read()
    df_path.write_text(dockerfile, encoding="utf-8")
    (OUTPUT_DIR / f"{did}_Dockerfile").write_text(dockerfile, encoding="utf-8")
    with _lock: _DEPLOYS[did]["dockerfile"] = dockerfile[:300]; _DEPLOYS[did]["build_ok"]=True

    # 生成 Docker Compose (微服务/多数据库项目)
    if has_compose:
        compose_file = "\n".join(open(clone_dir / f).read() for f in ["docker-compose.yml","docker-compose.yaml"] if (clone_dir/f).exists())
    elif services or (deps and any(d in str(deps) for d in ["mysql","postgres","redis","mongo","kafka"])):
        compose_file = _generate_compose(name, port, services)
    else:
        compose_file = ""
    if compose_file:
        (OUTPUT_DIR / f"{did}_docker-compose.yml").write_text(compose_file, encoding="utf-8")
        with _lock: _DEPLOYS[did]["compose"] = compose_file[:200]

    # 生成 K8s yaml
    k8s_yaml = _K8S_YAMLS["deployment"].format(name=name.split("/")[-1], port=port)
    (OUTPUT_DIR / f"{did}_k8s.yaml").write_text(k8s_yaml, encoding="utf-8")
    with _lock: _DEPLOYS[did]["k8s"] = k8s_yaml[:200]

    # Nginx
    domain = f"{name}.autoevoai.com"
    nginx_conf = f"""server {{
    listen 80;
    server_name {domain};
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}"""
    (OUTPUT_DIR / f"{did}_nginx.conf").write_text(nginx_conf, encoding="utf-8")
    nginx_target = Path(f"/etc/nginx/sites-available/{name}.autoevoai.com")
    try:
        nginx_target.write_text(nginx_conf, encoding="utf-8")
        subprocess.run(["ln","-sf",str(nginx_target),f"/etc/nginx/sites-enabled/{name}.autoevoai.com"], timeout=5)
        subprocess.run(["nginx","-s","reload"], timeout=5)
        with _lock: _DEPLOYS[did]["run_ok"]=True
    except: pass
    with _lock: _DEPLOYS[did].update({"nginx":nginx_conf[:200],"domain":domain})

    # Docker 构建
    container_name = f"evo_{name[:10]}_{did[:8]}"
    try:
        subprocess.run(["docker","build","-t",container_name,str(clone_dir)], capture_output=True, text=True, timeout=300)
        subprocess.run(["docker","rm","-f",container_name], capture_output=True, text=True, timeout=10)
        subprocess.run(["docker","run","-d","--name",container_name,"--restart","unless-stopped","-p",f"{port}:{port}",container_name], capture_output=True, text=True, timeout=30)
        with _lock: _DEPLOYS[did].update({"status":"running","docker_cmd":f"docker run -d --name {container_name} -p {port}:{port} {container_name}"})
        _update_status(did,f"运行中 http://localhost:{port}")
    except Exception as e:
        _update_status(did,f"Docker跳过: {str(e)[:50]}")

    # 经验库
    db = _load_db()
    db["projects"].append({"id":did,"name":name,"url":url,"type":ptype,"port":port,"deps":deps,"domain":domain,"is_monorepo":is_monorepo,"has_compose":has_compose,"created_at":time.time()})
    _save_db(db)

@router.get("/deploy/status/{deploy_id}")
async def deploy_status(deploy_id: str):
    d = _DEPLOYS.get(deploy_id)
    if not d: return {"success":False,"error":"not found"}
    return {"success":True,**d}

@router.get("/deploy/list")
async def deploy_list():
    return {"success":True,"deploys":_load_db().get("projects",[])}
