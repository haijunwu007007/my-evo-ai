"""AUTO-EVO-AI — 源码项目自动构建部署"""
import os, json, re, asyncio, shutil
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.hub.auto_build")
BASE = Path(__file__).resolve().parent.parent.parent
HUBS_DIR = BASE / "hub_projects"
HUBS_DIR.mkdir(exist_ok=True)

def detect_lang(files: list) -> dict:
    patterns = {
        "node": {"files": ["package.json", "yarn.lock", "pnpm-lock.yaml"], "build": "npm install && npm run build", "run": "npm start", "port": 3000},
        "python": {"files": ["requirements.txt", "Pipfile", "setup.py", "pyproject.toml", "Pipfile.lock"], "build": "pip install -r requirements.txt", "run": "python app.py", "port": 5000},
        "go": {"files": ["go.mod", "go.sum"], "build": "go build -o app .", "run": "./app", "port": 8080},
        "rust": {"files": ["Cargo.toml", "Cargo.lock"], "build": "cargo build --release", "run": "./target/release/app", "port": 8080},
        "java-maven": {"files": ["pom.xml"], "build": "mvn package -DskipTests", "run": "java -jar $(ls -1t target/*.jar 2>/dev/null | head -1)", "port": 8080},
        "java-gradle": {"files": ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"], "build": "gradle build -x test", "run": "java -jar $(ls -1t build/libs/*.jar 2>/dev/null | head -1)", "port": 8080},
        "php": {"files": ["composer.json", "index.php"], "build": "composer install", "run": "php -S 0.0.0.0:8080 -t public", "port": 8080},
        "dotnet": {"files": ["*.csproj", "*.sln"], "build": "dotnet publish -c Release -o out", "run": "dotnet out/$(ls -1t *.csproj 2>/dev/null | head -1 | sed 's/\\.csproj//').dll", "port": 5000},
        "vue": {"files": ["vue.config.js", "nuxt.config.js", "nuxt.config.ts"], "build": "npm install && npm run build", "run": "npm run serve", "port": 8080},
        "react": {"files": ["vite.config.js", "vite.config.ts", "next.config.js", "craco.config.js"], "build": "npm install && npm run build", "run": "npm start", "port": 5173},
        "django": {"files": ["manage.py"], "build": "pip install -r requirements.txt", "run": "python manage.py runserver 0.0.0.0:8000", "port": 8000},
        "flask": {"files": ["app.py", "wsgi.py"], "build": "pip install -r requirements.txt", "run": "python app.py", "port": 5000},
        "spring": {"files": ["mvnw", "gradlew", "gradlew.bat"], "build": "./mvnw package -DskipTests 2>/dev/null || ./gradlew build -x test", "run": "java -jar $(ls -1t target/*.jar 2>/dev/null; ls -1t build/libs/*.jar 2>/dev/null | head -1)", "port": 8080},
    }
    fset = {f.lower() for f in files}
    for lang, cfg in patterns.items():
        for pat in cfg["files"]:
            if pat in fset:
                return {"lang": lang, **cfg}
            if pat.startswith("*."):
                ext = pat[1:]
                if any(f.endswith(ext) for f in fset):
                    return {"lang": lang, **cfg}
        # Also check parent dirs for wrapper scripts
        if "mvnw" in fset or "gradlew" in fset:
            return {"lang": "spring", "files": ["mvnw/gradlew"], "build": "(./mvnw package -DskipTests || ./gradlew build -x test) 2>/dev/null", "run": "java -jar $(ls -1t target/*.jar build/libs/*.jar 2>/dev/null | head -1)", "port": 8080}
    return {"lang": "unknown", "build": "", "run": "", "port": 0}

def detect_services(files: list) -> list:
    """检测项目需要的依赖服务（MySQL/Redis/PostgreSQL等）"""
    fset = {f.lower() for f in files}
    content_str = " ".join(files)
    services = []
    # Config files
    has_docker = any("docker-compose" in f or f.endswith("docker-compose.yml") or f == ".env.example" for f in fset)
    if has_docker:
        return []  # Has docker-compose, it handles services itself
    # Detect by config files
    if any("application.yml" in f or "application.properties" in f or "application-dev.yml" in f for f in fset):
        services.append("mysql:8.0")
    if any(f.endswith("redis.conf") or f == "redis.yml" for f in fset):
        services.append("redis:7-alpine")
    if "wp-config.php" in fset:
        services.append("mysql:5.7")
    # Detect by known config patterns
    return [f"-d --network host {svc}" for svc in services]

async def auto_build(proj_dir: Path, pid: str) -> dict:
    """检测并构建源码项目"""
    files = [str(f.name) for f in proj_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
    config = detect_lang(files)
    if config["lang"] == "unknown":
        # LLM fallback
        try:
            from api.agent_llm import call_llm
            prompt = f"分析项目 {proj_dir.name} 的文件列表，判断这是什么技术栈的项目（只输出技术栈名）：{', '.join(files[:30])}"
            text, _ = call_llm([{"role":"user","content":prompt}])
            if text:
                return {"lang": "unknown", "build": "", "run": f"{text} 项目，请手动配置部署", "port": 0}
        except: pass
        return {"lang": "unknown", "build": "", "run": "无法自动检测项目类型", "port": 0}
    proj_name = proj_dir.name.lower().replace("_", "-")
    build_log = ""
    if config["build"]:
        build_log += f"构建命令: {config['build']}\n"
    run_cmd = config["run"]
    port = config.get("port", 8080)
    return {"lang": config["lang"], "build": config["build"], "run": run_cmd, "port": port, "proj_name": proj_name}

async def auto_build_with_services(proj_dir: Path, pid: str) -> dict:
    """检测并构建 + 自动部署依赖服务（MySQL/Redis等）"""
    files = [str(f.name) for f in proj_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
    config = await auto_build(proj_dir, pid)
    services = detect_services(files)
    if services:
        svc_cmds = []
        for svc_name in services:
            name = svc_name.split(":")[0]
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"docker run -d --name {pid}_{name} --network host {svc_name}",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                out, _ = await proc.communicate()
                svc_cmds.append(f"{name}: {out.decode().strip()[:20]}")
            except Exception as e:
                svc_cmds.append(f"{name}: {e}")
        config["services"] = "; ".join(svc_cmds)
    return config

async def auto_deploy_source(pid: str, full_name: str, branch: str = "main") -> dict:
    """源码项目自动部署（无 Docker 时调用）"""
    from api.hub.models import update_project
    proj_dir = HUBS_DIR / full_name.replace("/", "_")
    if not proj_dir.exists():
        return {"success": False, "error": "项目目录不存在"}
    update_project(pid, {"status": "building"})
    build_info = await auto_build_with_services(proj_dir, pid)
    if not isinstance(build_info, dict) or build_info.get("lang") == "unknown":
        update_project(pid, {"status": "error"})
        err = build_info.get("run", "无法检测项目类型") if isinstance(build_info, dict) else str(build_info)
        return {"success": False, "error": err}
    logger.info(f"[{pid}] 检测到 {build_info['lang']}, 端口={build_info.get('port',0)}")
    # 自动安装依赖
    if build_info.get("build"):
        try:
            cmd = build_info["build"]
            proc = await asyncio.create_subprocess_shell(cmd, cwd=str(proj_dir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"[{pid}] build err: {err.decode()[:200]}")
        except Exception as e:
            logger.warning(f"[{pid}] build exception: {e}")
    update_project(pid, {"status": "ready",
        "port": build_info.get("port", 8080),
        "language": build_info.get("lang", "unknown"),
        "run_cmd": build_info.get("run", ""),
        "services": build_info.get("services", "")})
    return {"success": True, "project_id": pid, "language": build_info.get("lang"),
        "run": build_info.get("run"), "port": build_info.get("port", 8080),
        "services": build_info.get("services", "")}
