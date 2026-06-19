# -*- coding: utf-8 -*-
"""开源项目分析器 — 自动检测项目类型、提取配置、分析依赖"""
import os, json, re, subprocess, tempfile, shutil, hashlib

TYPES = {
    "node": {"files": ["package.json","yarn.lock","pnpm-lock.yaml","next.config.js"], "cmd": ["node","npm","yarn","pnpm"], "port_files": ["package.json","docker-compose.yml",".env.example"]},
    "python": {"files": ["requirements.txt","pyproject.toml","setup.py","Pipfile","poetry.lock","manage.py","wsgi.py"], "cmd": ["python3","python","pip3","pip"], "port_files": ["docker-compose.yml","app.py","main.py","manage.py",".env.example"]},
    "go": {"files": ["go.mod","go.sum","main.go"], "cmd": ["go"], "port_files": ["main.go","docker-compose.yml"]},
    "rust": {"files": ["Cargo.toml","Cargo.lock"], "cmd": ["cargo","rustc"], "port_files": ["Cargo.toml","docker-compose.yml"]},
    "java": {"files": ["pom.xml","build.gradle","gradlew","mvnw"], "cmd": ["mvn","gradle","java"], "port_files": ["application.yml","application.properties","docker-compose.yml"]},
    "docker": {"files": ["Dockerfile","docker-compose.yml"], "cmd": ["docker"], "port_files": ["docker-compose.yml"]},
    "static": {"files": ["index.html"], "cmd": [], "port_files": []},
}

def analyze(repo_path: str) -> dict:
    """分析项目目录，返回项目类型、配置、依赖等信息"""
    result = {"path": repo_path, "name": os.path.basename(repo_path), "type": None, "confidence": 0, "ports": [], "deps": [], "has_dockerfile": False, "has_compose": False, "readme": "", "build_cmd": None, "run_cmd": None, "env_vars": []}
    if not os.path.isdir(repo_path): return result
    files = os.listdir(repo_path) if os.path.isdir(repo_path) else []
    low = [f.lower() for f in files]
    # 检测类型
    for tname, tcfg in TYPES.items():
        score = sum(1 for f in tcfg["files"] if f.lower() in low or f in files)
        if score > result["confidence"]:
            result["type"] = tname
            result["confidence"] = score
    # Docker
    result["has_dockerfile"] = "Dockerfile" in files or "dockerfile" in files
    result["has_compose"] = "docker-compose.yml" in files or "docker-compose.yaml" in files
    # README
    for fn in files:
        if fn.lower().startswith("readme"):
            try: result["readme"] = open(os.path.join(repo_path, fn), errors="ignore").read()[:2000]
            except: pass
            break
    # 端口检测
    if result["type"] == "node" and "package.json" in files:
        try:
            pkg = json.load(open(os.path.join(repo_path, "package.json")))
            result["deps"] = list(pkg.get("dependencies", {}).keys())[:20]
            if "scripts" in pkg:
                scripts = pkg["scripts"]
                if isinstance(scripts, dict):
                    if "dev" in scripts or "start" in scripts: result["run_cmd"] = "npm run dev" if "dev" in scripts else "npm start"
                    if "build" in scripts: result["build_cmd"] = "npm run build"
        except: pass
    elif result["type"] in ("python","static") and "requirements.txt" in files:
        try: result["deps"] = [l.strip() for l in open(os.path.join(repo_path,"requirements.txt"),errors="ignore").readlines() if l.strip() and not l.startswith("#")][:20]
        except: pass
    elif result["type"] == "go" and "go.mod" in files:
        try:
            for l in open(os.path.join(repo_path,"go.mod"),errors="ignore").readlines():
                if "require" in l: break
                result["deps"].append(l.strip())
        except: pass
    # 端口
    if result["has_compose"]:
        try:
            import yaml
            compose = yaml.safe_load(open(os.path.join(repo_path,"docker-compose.yml")))
            for svc in (compose.get("services",{}) if compose else {}).values():
                if "ports" in svc:
                    for p in svc["ports"]:
                        result["ports"].append(str(p).split(":")[-1].split("/")[0])
        except: result["ports"].append("3000")
    if not result["ports"]:
        if result["type"] == "node": result["ports"].append("3000")
        elif result["type"] == "python": result["ports"].append("8000")
        elif result["type"] == "go": result["ports"].append("8080")
        elif result["type"] == "rust": result["ports"].append("8080")
        elif result["type"] == "java": result["ports"].append("8080")
        else: result["ports"].append("80")
    # 默认运行命令
    if not result["run_cmd"]:
        if result["type"] == "node": result["run_cmd"] = "npm start" if "package.json" in files else "node index.js"
        elif result["type"] == "python": result["run_cmd"] = "python3 app.py" if "app.py" in files else "python3 main.py" if "main.py" in files else "python3 manage.py runserver" if "manage.py" in files else "python3 -m http.server 8000"
        elif result["type"] == "go": result["run_cmd"] = "go run ."
        elif result["type"] == "rust": result["run_cmd"] = "cargo run"
        elif result["type"] == "java": result["run_cmd"] = "./mvnw spring-boot:run" if "mvnw" in files else "mvn spring-boot:run"
    return result

def clone(url: str, branch: str = "") -> str:
    """克隆仓库到临时目录，返回路径"""
    tmp = tempfile.mkdtemp(prefix="evo_repo_")
    cmd = ["git", "clone", "--depth=1"]
    if branch: cmd += ["-b", branch]
    cmd += [url, tmp]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0: return None, r.stderr[:500]
        return tmp, None
    except subprocess.TimeoutExpired: return None, "克隆超时"
    except Exception as e: return None, str(e)[:200]

def build(repo_path: str, info: dict) -> tuple:
    """构建项目"""
    cmd = {"python": "pip3 install -r requirements.txt 2>/dev/null; echo BUILD_OK",
           "node": "npm install 2>&1 | tail -3",
           "go": "go build -o /dev/null . 2>&1 | tail -3",
           "rust": "cargo build 2>&1 | tail -3",
           "docker": "echo DOCKER_OK",
           "static": "echo STATIC_OK"}.get(info.get("type",""), "echo UNKNOWN")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd=repo_path)
        return r.returncode == 0, r.stdout[-200:] + r.stderr[-200:]
    except: return False, "构建超时"

def gen_dockerfile(info: dict) -> str:
    """根据项目类型生成 Dockerfile"""
    t = info.get("type","static")
    tmpl = {
        "node": """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE {port}
CMD ["node", "index.js"]
""",
        "python": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . .
EXPOSE {port}
CMD ["python3", "app.py"]
""",
        "go": """FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o app .
FROM alpine
COPY --from=build /app/app /app/
EXPOSE {port}
CMD ["/app/app"]
""",
        "rust": """FROM rust:1.75-slim AS build
WORKDIR /app
COPY . .
RUN cargo build --release
FROM debian:bookworm-slim
COPY --from=build /app/target/release/* /app/
EXPOSE {port}
CMD ["/app/app"]
""",
        "static": """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""",
        "java": """FROM eclipse-temurin:17-jdk
WORKDIR /app
COPY mvnw pom.xml ./
RUN ./mvnw dependency:resolve
COPY src ./src
EXPOSE {port}
CMD ["./mvnw", "spring-boot:run"]
""",
    }.get(t, """FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE {port}
CMD ["python3", "-m", "http.server", "{port}"]
""")
    port = info.get("ports", ["3000"])[0]
    return tmpl.format(port=port)
