"""
🛝 沙箱执行环境 — 编译+运行+调试 Agent 生成的代码
接收代码/文件 → 选构建工具 → Docker容器执行 → 返回结果
"""
from fastapi import APIRouter
import os, json, time, hashlib, subprocess, shutil, asyncio, re
from pathlib import Path

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])
BASE = Path(__file__).resolve().parent.parent.parent
SANDBOX_DIR = BASE / "data" / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

# === 构建适配器：每种项目类型的专用构建+运行指令 ===
_BUILD_ADAPTERS = {
    "node|npm": {
        "detect": ["package.json"],
        "install": "npm install",
        "build": "npm run build 2>/dev/null || echo 'no build script'",
        "test": "npm test 2>/dev/null || echo 'no tests'",
        "run": "npm start",
        "image": "node:20-alpine",
        "port_guess": 3000,
    },
    "node|yarn": {
        "detect": ["yarn.lock"],
        "install": "yarn install",
        "build": "yarn build 2>/dev/null || echo 'no build'",
        "test": "yarn test 2>/dev/null || echo 'no tests'",
        "run": "yarn start",
        "image": "node:20-alpine",
        "port_guess": 3000,
    },
    "python|pip": {
        "detect": ["requirements.txt", "setup.py"],
        "install": "pip install -r requirements.txt 2>/dev/null || pip install -e . 2>/dev/null || echo 'no deps'",
        "build": "python -m compileall . 2>/dev/null || echo 'ok'",
        "test": "python -m pytest 2>/dev/null || python -m unittest 2>/dev/null || echo 'no tests'",
        "run": "python app.py || python main.py || python -m flask run --host=0.0.0.0 --port=8000",
        "image": "python:3.11-slim",
        "port_guess": 8000,
    },
    "python|poetry": {
        "detect": ["pyproject.toml"],
        "install": "pip install poetry && poetry install",
        "build": "poetry build 2>/dev/null || echo 'ok'",
        "test": "poetry run pytest 2>/dev/null || echo 'no tests'",
        "run": "poetry run python app.py || python app.py",
        "image": "python:3.11-slim",
        "port_guess": 8000,
    },
    "go:mod": {
        "detect": ["go.mod"],
        "install": "go mod download",
        "build": "go build -o /app/server .",
        "test": "go test ./... 2>/dev/null || echo 'no tests'",
        "run": "/app/server",
        "image": "golang:1.22-alpine",
        "port_guess": 8080,
    },
    "rust|cargo": {
        "detect": ["Cargo.toml"],
        "install": "",
        "build": "cargo build --release",
        "test": "cargo test 2>/dev/null || echo 'no tests'",
        "run": "./target/release/*",
        "image": "rust:1.77-slim",
        "port_guess": 8080,
    },
    "java|maven": {
        "detect": ["pom.xml"],
        "install": "",
        "build": "mvn package -DskipTests -q",
        "test": "mvn test 2>/dev/null || echo 'no tests'",
        "run": "java -jar target/*.jar",
        "image": "maven:3-eclipse-temurin-21",
        "port_guess": 8080,
    },
    "java|gradle": {
        "detect": ["build.gradle", "build.gradle.kts"],
        "install": "",
        "build": "gradle build -x test -q",
        "test": "gradle test 2>/dev/null || echo 'no tests'",
        "run": "java -jar build/libs/*.jar",
        "image": "gradle:8-jdk21",
        "port_guess": 8080,
    },
    "php|composer": {
        "detect": ["composer.json"],
        "install": "composer install",
        "build": "echo 'ok'",
        "test": "./vendor/bin/phpunit 2>/dev/null || echo 'no tests'",
        "run": "php -S 0.0.0.0:8080 -t public",
        "image": "php:8.2-cli",
        "port_guess": 8080,
    },
    "static:nginx": {
        "detect": ["index.html"],
        "install": "",
        "build": "echo 'ok'",
        "test": "echo 'static'",
        "run": "",
        "image": "nginx:alpine",
        "port_guess": 80,
    },
    "_default": {
        "detect": [],
        "install": "echo 'auto-detect'",
        "build": "echo 'ok'",
        "test": "echo 'ok'",
        "run": "echo 'Container ready'",
        "image": "alpine:3.19",
        "port_guess": 8080,
    },
}

def _detect_build_adapter(files: list) -> dict:
    """根据文件列表选择最匹配的构建适配器"""
    fset = set(f.lower() for f in files)
    best = _BUILD_ADAPTERS["_default"]
    best_name = "auto"
    for name, adapter in _BUILD_ADAPTERS.items():
        if name == "_default": continue
        for d in adapter.get("detect", []):
            if d in fset or any(d in f for f in fset):
                return {**adapter, "_name": name}
    return {**best, "_name": best_name}

# === API ===

@router.post("/run")
async def sandbox_run(data: dict):
    """运行代码沙箱 — 接收代码字符串或文件列表，自动检测构建类型并执行"""
    code = data.get("code", "")
    files = data.get("files", [])
    language = data.get("language", "auto")

    sid = hashlib.md5((str(time.time()) + code[:50]).encode()).hexdigest()[:12]
    workdir = SANDBOX_DIR / sid
    workdir.mkdir(parents=True, exist_ok=True)

    # 写入代码
    if code:
        (workdir / "app.py" if "python" in code.lower() or not any(f.endswith((".js",".ts",".go",".rs")) for f in files) else workdir / "index.js").write_text(code, encoding="utf-8")

    # 检测适配器
    existing = list(f.name for f in workdir.iterdir()) + files
    adapter = _detect_build_adapter(existing)
    image = adapter.get("image", "alpine:3.19")
    install = adapter.get("install", "echo ok")
    build_cmd = adapter.get("build", "echo ok")
    run_cmd = adapter.get("run", "echo ok")

    container_name = f"evo_sandbox_{sid}"

    # 构建 Dockerfile
    df = f"""FROM {image}
WORKDIR /app
COPY . .
RUN {install}
RUN {build_cmd}
CMD {run_cmd}
"""
    (workdir / "Dockerfile").write_text(df, encoding="utf-8")

    # 执行
    logs = {"sid": sid, "adapter": adapter.get("_name", "auto"), "steps": []}
    try:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=10)
        r1 = subprocess.run(["docker", "build", "-t", container_name, str(workdir)], capture_output=True, text=True, timeout=300)
        logs["steps"].append({"step": "build", "ok": r1.returncode == 0, "output": r1.stdout[-500:] + r1.stderr[-500:]})

        r2 = subprocess.run(["docker", "run", "-d", "--rm", "--name", container_name, container_name], capture_output=True, text=True, timeout=30)
        logs["steps"].append({"step": "run", "ok": r2.returncode == 0, "output": r2.stdout[:200]})

        if r2.returncode == 0:
            time.sleep(3)
            r3 = subprocess.run(["docker", "logs", container_name], capture_output=True, text=True, timeout=15)
            logs["steps"].append({"step": "logs", "ok": True, "output": r3.stdout[-1000:]})
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=10)
    except Exception as e:
        logs["steps"].append({"step": "error", "ok": False, "output": str(e)[:200]})

    shutil.rmtree(workdir, ignore_errors=True)
    return {"success": True, "sandbox_id": sid, **logs}

@router.get("/adapters")
def list_adapters():
    """列出所有构建适配器"""
    return {"success": True, "adapters": [{"name": k, "image": v.get("image",""), "detect": v.get("detect",[])} for k, v in _BUILD_ADAPTERS.items() if k != "_default"]}

# === 集成: 验证部署 ===
def verify_deploy(url: str, port: int = 8080, timeout: int = 30) -> dict:
    """验证部署是否正常 — curl + 日志检查"""
    start = time.time()
    logs = []
    for i in range(3):
        try:
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://localhost:{port}"], capture_output=True, text=True, timeout=timeout)
            code = r.stdout.strip()
            if code in ("200", "301", "302"):
                return {"ok": True, "http_code": int(code), "attempts": i+1, "time": round(time.time()-start, 1)}
            logs.append(f"attempt {i+1}: HTTP {code}")
        except:
            logs.append(f"attempt {i+1}: timeout")
        time.sleep(5)
    return {"ok": False, "http_code": 0, "attempts": 3, "time": round(time.time()-start, 1), "logs": logs}
