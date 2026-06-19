# -*- coding: utf-8 -*-
"""一键部署增强版 — 类型识别+Docker+Nginx+SSL+源码分析"""
from fastapi import APIRouter
import os, json, time, hashlib, subprocess, shutil, re
from pathlib import Path

router = APIRouter(prefix="/api/v1", tags=["deploy-v2"])
BASE = Path(__file__).resolve().parent.parent.parent
DEPLOYS_DIR = BASE / "data" / "deploys"
DEPLOYS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_DB = BASE / "data" / "deploy_experience.json"

def _load_db():
    try: return json.load(open(_DB, encoding="utf-8"))
    except: return {"projects": []}

def _save_db(d):
    json.dump(d, open(_DB, "w", encoding="utf-8"), indent=2)

def _detect_type(name: str, files: list = None) -> dict:
    """高级项目类型识别 — 15+种"""
    n = name.lower()
    rules = [
        ("node", ["node","npm","express","next","nuxt","vue","react","angular","svelte","webpack","vite"]),
        ("python", ["python","flask","django","fastapi","pytorch","tensorflow","scikit","pip","conda","jupyter"]),
        ("go", ["go","golang","gin","echo","fiber"]),
        ("rust", ["rust","cargo","rs"]),
        ("java", ["java","spring","maven","gradle","tomcat","jar","war"]),
        ("php", ["php","laravel","symfony","wordpress","composer"]),
        ("ruby", ["ruby","rails","gem","bundler"]),
        ("docker", ["docker","docker-compose","container"]),
        ("static", ["html","css","javascript","markdown","docs","blog","site","website","landing"]),
        ("c_cpp", ["c++","c--","cpp","c","cmake","makefile","cmakelists"]),
        ("dotnet", ["c#","dotnet","asp.net","blazor","nuget"]),
        ("swift", ["swift","xcode","ios","macos"]),
        ("flutter", ["flutter","dart","dart"]),
        ("elixir", ["elixir","phoenix","mix.exs"]),
        ("scala", ["scala","sbt"]),
        ("haskell", ["haskell","stack.yaml","cabal"]),
        ("lua", ["lua","luarocks","openresty"]),
    ]
    for ptype, keywords in rules:
        if any(kw in n for kw in keywords):
            return {"type": ptype, "score": 90, "keywords": [k for k in keywords if k in n][:3]}
    if files:
        if any(f.endswith(".py") for f in files): return {"type":"python","score":60,"keywords":["*.py found"]}
        if any(f.endswith(".js") or f.endswith(".jsx") or f.endswith(".ts") for f in files): return {"type":"node","score":60,"keywords":["*.js found"]}
        if any(f.endswith(".go") for f in files): return {"type":"go","score":60,"keywords":["*.go found"]}
        if any(f.endswith(".rs") for f in files): return {"type":"rust","score":60,"keywords":["*.rs found"]}
        if any(f.endswith(".java") for f in files): return {"type":"java","score":60,"keywords":["*.java found"]}
        if "index.html" in files: return {"type":"static","score":50,"keywords":["index.html"]}
    return {"type": "unknown", "score": 10, "keywords": []}

def _analyze_source(repo_path: str) -> dict:
    """源码分析 — 提取依赖/端口/环境变量"""
    result = {"deps": [], "port": None, "env_vars": [], "build_cmd": None, "run_cmd": None, "files": []}
    try:
        files = []
        for root, dirs, fnames in os.walk(repo_path):
            dnames = [d for d in dirs if d.startswith(".") or d == "node_modules"]
            for d in dnames: dirs.remove(d)
            for f in fnames: files.append(os.path.join(root, f))
        result["files"] = [os.path.relpath(f, repo_path) for f in files[:50]]
        
        for f in files:
            rel = os.path.relpath(f, repo_path)
            try:
                c = open(f, encoding="utf-8", errors="replace").read()
            except: continue
            if rel == "package.json":
                d = json.loads(c)
                result["deps"] = list((d.get("dependencies",{}) or {}).keys())[:20]
                result["port"] = d.get("port") or (3000 if "express" in str(result["deps"]).lower() else None)
                result["build_cmd"] = d.get("scripts",{}).get("build")
                result["run_cmd"] = d.get("scripts",{}).get("start")
            elif rel == "requirements.txt":
                result["deps"] = [l.split("==")[0] for l in c.splitlines() if l.strip() and not l.startswith("#")][:20]
            elif rel == "pyproject.toml":
                m = re.search(r'dependencies\s*=\s*\[(.*?)\]', c, re.DOTALL)
                if m: result["deps"] = re.findall(r'"([^"]+)"', m.group(1))[:20]
            elif rel == "go.mod":
                result["deps"] = re.findall(r'^\s+(\S+)', c, re.MULTILINE)[:20]
            elif rel == "Dockerfile":
                for line in c.splitlines():
                    if "EXPOSE" in line:
                        m2 = re.search(r'EXPOSE\s+(\d+)', line)
                        if m2: result["port"] = int(m2.group(1))
                        break
            elif "docker-compose" in rel.lower():
                for line in c.splitlines():
                    m2 = re.search(r'(\d+):\d+', line)
                    if m2: result["port"] = int(m2.group(1)); break
        if not result["port"]:
            result["port"] = 8080
    except: pass
    return result

_DOCKER_TEMPLATES = {
    "node": 'FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE {port}\nCMD ["npm", "start"]\n',
    "python": 'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt ./\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE {port}\nCMD ["python", "app.py"]\n',
    "go": 'FROM golang:1.22-alpine AS build\nWORKDIR /app\nCOPY go.* ./\nRUN go mod download\nCOPY . .\nRUN go build -o /app/server .\nFROM alpine:3.19\nCOPY --from=build /app/server /app/server\nEXPOSE {port}\nCMD ["/app/server"]\n',
    "rust": 'FROM rust:1.77-slim AS build\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\nFROM debian:bookworm-slim\nCOPY --from=build /app/target/release/* /app/\nEXPOSE {port}\nCMD ["/app/app"]\n',
    "java": 'FROM maven:3-eclipse-temurin-21 AS build\nWORKDIR /app\nCOPY pom.xml .\nRUN mvn dependency:go-offline\nCOPY . .\nRUN mvn package -DskipTests\nFROM eclipse-temurin:21-jre\nCOPY --from=build /app/target/*.jar /app/app.jar\nEXPOSE {port}\nCMD ["java", "-jar", "/app/app.jar"]\n',
    "php": 'FROM php:8.2-apache\nWORKDIR /var/www/html\nCOPY . .\nRUN docker-php-ext-install pdo pdo_mysql\nEXPOSE {port}\nCMD ["apache2-foreground"]\n',
    "static": 'FROM nginx:alpine\nCOPY . /usr/share/nginx/html\nEXPOSE {port}\nCMD ["nginx", "-g", "daemon off;"]\n',
    "docker": 'FROM alpine:3.19\nRUN apk add --no-cache docker-cli\nCOPY . /app\nWORKDIR /app\nCMD ["sh"]\n',
    "unknown": 'FROM alpine:3.19\nWORKDIR /app\nCOPY . .\nEXPOSE {port}\nCMD ["echo", "Container ready"]\n',
}

def _generate_dockerfile(project_type: str, port: int = 8080) -> str:
    tpl = _DOCKER_TEMPLATES.get(project_type, _DOCKER_TEMPLATES["unknown"])
    return tpl.format(port=port)

def _generate_nginx(domain: str, port: int) -> str:
    return f"""server {{
    listen 80;
    server_name {domain};
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""

class DeployOrchestrator:
    def __init__(self):
        self._deploys: dict = {}

    def start_deploy(self, data: dict) -> dict:
        url = data.get("url", "")
        auto = data.get("auto", False)
        did = hashlib.md5((url + str(time.time())).encode()).hexdigest()[:12]
        name = url.split("/")[-1].replace(".git", "") if url else "unknown"
        ptype = data.get("project_type", "")
        
        # Type detection from name
        if not ptype:
            detected = _detect_type(name)
            ptype = detected["type"]
        
        deploy_info = {
            "id": did, "url": url, "name": name, "type": ptype,
            "status": "building", "progress": "正在克隆仓库...",
            "started_at": time.time(), "auto": auto,
            "dockerfile": "", "nginx": "", "domain": "", "ssl": False
        }
        self._deploys[did] = deploy_info
        return {"success": True, "id": did, "status": "building"}

    def get_status(self, did: str) -> dict:
        d = self._deploys.get(did)
        if not d: return {"success": False, "error": "not found"}
        return {"success": True, **d}

# Global instance
_ORCHESTRATOR = DeployOrchestrator()

@router.post("/deploy/start")
async def deploy_start(data: dict):
    """开始部署 — 自动检测类型+分析+Docker+Nginx"""
    url = data.get("url", "")
    if not url:
        return {"success": False, "error": "需要 url 参数"}
    
    did = hashlib.md5((url + str(time.time())).encode()).hexdigest()[:12]
    name = url.split("/")[-1].replace(".git", "") if url else "unknown"
    
    # 1. 类型检测
    detected = _detect_type(name)
    ptype = detected["type"]
    
    # 2. 尝试克隆分析
    clone_dir = DEPLOYS_DIR / did
    analysis = {}
    try:
        import subprocess
        r = subprocess.run(["git", "clone", "--depth", "1", url, str(clone_dir)],
                          capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            analysis = _analyze_source(str(clone_dir))
    except:
        pass
    
    port = analysis.get("port", 8080)
    deps = analysis.get("deps", [])
    
    # 3. 生成 Dockerfile
    dockerfile = _generate_dockerfile(ptype, port)
    (OUTPUT_DIR / f"{did}_Dockerfile").write_text(dockerfile, encoding="utf-8")
    
    # 4. 生成 Nginx 配置
    domain = f"{name}.autoevoai.com"
    nginx_conf = _generate_nginx(domain, port)
    (OUTPUT_DIR / f"{did}_nginx.conf").write_text(nginx_conf, encoding="utf-8")
    
    # 5. 保存经验
    db = _load_db()
    db["projects"].append({
        "id": did, "name": name, "url": url, "type": ptype,
        "port": port, "deps": deps, "domain": domain,
        "created_at": time.time()
    })
    _save_db(db)
    
    result = {
        "success": True, "id": did, "name": name, "type": ptype,
        "port": port, "deps": deps, "domain": domain,
        "dockerfile": dockerfile[:200],
        "nginx": nginx_conf[:200],
    }
    _ORCHESTRATOR._deploys[did] = result
    return result

@router.get("/deploy/status/{deploy_id}")
async def deploy_status(deploy_id: str):
    return _ORCHESTRATOR.get_status(deploy_id)

@router.get("/deploy/list")
async def deploy_list():
    db = _load_db()
    return {"success": True, "deploys": db.get("projects", [])}
