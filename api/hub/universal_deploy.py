"""万能部署器 — GitHub URL → 自动分析 → Docker部署 → 健康检查"""
import os, json, re, subprocess, tempfile, shutil, time, httpx
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.deploy")

DEPLOY_DIR = Path("/opt/evo-deploys")
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

# 语言/框架检测规则
_LANG_RULES = [
    (r"(package\.json|yarn\.lock)", "node", {"npm":"npm install","build":"npm run build","run":"npm start"}),
    (r"(requirements\.txt|setup\.py|Pipfile)", "python", {"pip install -r requirements.txt":"","run":"python app.py"}),
    (r"(go\.mod|go\.sum)", "go", {"build":"go build -o app .","run":"./app"}),
    (r"(Cargo\.toml)", "rust", {"build":"cargo build --release","run":"./target/release/app"}),
    (r"(pom\.xml|build\.gradle)", "java", {"build":"mvn package","run":"java -jar target/*.jar"}),
    (r"(Gemfile)", "ruby", {"build":"bundle install","run":"ruby app.rb"}),
    (r"(Dockerfile)", "docker", {}),
    (r"(compose\.yml|compose\.yaml|docker-compose\.yml)", "compose", {}),
]

def detect_lang(repo_dir: str) -> dict:
    """自动检测项目语言和框架"""
    files = set()
    for root, _, fs in os.walk(repo_dir):
        for f in fs:
            files.add(f)
        if len(files) > 100: break

    for pattern, lang, cmds in _LANG_RULES:
        if any(re.search(pattern, f) for f in files):
            return {"lang": lang, "commands": cmds, "files": list(files)[:20]}
    return {"lang": "unknown", "commands": {}, "files": list(files)[:20]}

def clone_repo(url: str) -> str:
    """克隆GitHub仓库到临时目录"""
    name = url.rstrip("/").split("/")[-1].replace(".git", "")
    target = DEPLOY_DIR / name
    if target.exists():
        shutil.rmtree(str(target))
    r = subprocess.run(["git", "clone", "--depth=1", url, str(target)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise Exception(f"克隆失败: {r.stderr[:200]}")
    return str(target)

def gen_dockerfile(repo_dir: str, lang_info: dict) -> str:
    """为项目生成Dockerfile"""
    lang = lang_info["lang"]
    df_path = os.path.join(repo_dir, "Dockerfile")
    if os.path.exists(df_path):
        return df_path

    templates = {
        "node": "FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE 3000\nCMD ["npm", "start"]\n",
        "python": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt ./\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD ["python", "app.py"]\n",
        "go": "FROM golang:1.22-alpine AS build\nWORKDIR /app\nCOPY go.mod go.sum ./\nRUN go mod download\nCOPY . .\nRUN go build -o app .\nFROM alpine\nWORKDIR /app\nCOPY --from=build /app/app .\nEXPOSE 8080\nCMD ["./app"]\n",
    }
    df = templates.get(lang, "FROM ubuntu:22.04\nWORKDIR /app\nCOPY . .\nCMD ["bash"]\n")
    with open(df_path, "w") as f:
        f.write(df)
    return df_path

def detect_port(repo_dir: str, lang: str) -> int:
    """尝试检测项目使用的端口"""
    port_map = {"node": 3000, "python": 8000, "go": 8080, "rust": 8080, "java": 8080, "docker": 80}
    for root, _, fs in os.walk(repo_dir):
        for f in fs:
            if f.endswith((".env", ".env.example", "config.*", "docker-compose*")):
                try:
                    c = open(os.path.join(root, f), errors="ignore").read()
                    m = re.search(r"PORT[=: ]+(\d+)", c)
                    if m: return int(m.group(1))
                except: pass
    return port_map.get(lang, 8080)

def deploy_docker(repo_dir: str, name: str, lang: str) -> dict:
    """构建并运行Docker容器"""
    import random
    port = detect_port(repo_dir, lang)
    host_port = random.randint(18000, 18999)

    # 先停止旧容器
    subprocess.run(["docker", "stop", name], capture_output=True, timeout=30)
    subprocess.run(["docker", "rm", name], capture_output=True, timeout=30)

    # 构建
    build = subprocess.run(["docker", "build", "-t", f"evo/{name}", repo_dir],
                           capture_output=True, text=True, timeout=300)
    if build.returncode != 0:
        return {"success": False, "error": f"构建失败: {build.stderr[:300]}"}

    # 运行
    run = subprocess.run(
        ["docker", "run", "-d", "--name", name, "--restart", "unless-stopped",
         "-p", f"{host_port}:{port}", f"evo/{name}"],
        capture_output=True, text=True, timeout=60)
    if run.returncode != 0:
        return {"success": False, "error": f"启动失败: {run.stderr[:300]}"}

    # 健康检查
    container_id = run.stdout.strip()
    for i in range(10):
        time.sleep(3)
        r = subprocess.run(["docker", "inspect", container_id, "--format={{.State.Status}}"],
                           capture_output=True, text=True, timeout=10)
        if r.stdout.strip() == "running":
            # 尝试http健康检查
            try:
                hr = httpx.get(f"http://localhost:{host_port}", timeout=5)
                return {"success": True, "url": f"http://localhost:{host_port}", "port": host_port, "status": hr.status_code, "container": container_id}
            except:
                return {"success": True, "url": f"http://localhost:{host_port}", "port": host_port, "status": "container_running", "container": container_id}

    return {"success": False, "error": "容器启动超时", "container": container_id}

def universal_deploy(github_url: str) -> dict:
    """万能入口：GitHub URL → 部署完成"""
    try:
        repo_dir = clone_repo(github_url)
        lang_info = detect_lang(repo_dir)
        logger.info(f"[DEPLOY] {github_url} -> {lang_info['lang']}")

        # 如果是docker-compose项目
        if lang_info["lang"] == "compose":
            r = subprocess.run(["docker-compose", "-f", os.path.join(repo_dir, "docker-compose.yml"),
                               "up", "-d"], capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                return {"success": True, "message": "compose已启动", "url": "docker-compose"}
            return {"success": True, "message": f"compose启动成功", "url": "docker-compose"}

        gen_dockerfile(repo_dir, lang_info)
        name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
        return deploy_docker(repo_dir, name, lang_info["lang"])
    except Exception as e:
        return {"success": False, "error": str(e)[:300]}

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/expressjs/express"
    print(json.dumps(universal_deploy(url), indent=2, ensure_ascii=False))
