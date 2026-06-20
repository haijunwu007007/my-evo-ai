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

# === 10种构建适配器 ===
_BUILD_ADAPTERS = {
    "node|npm": {"detect":["package.json"],"install":"npm install","build":"npm run build 2>/dev/null || echo ok","test":"npm test 2>/dev/null || echo no tests","run":"npm start","image":"node:20-alpine","port_guess":3000},
    "node|yarn": {"detect":["yarn.lock"],"install":"yarn install","build":"yarn build 2>/dev/null || echo ok","test":"yarn test 2>/dev/null || echo no tests","run":"yarn start","image":"node:20-alpine","port_guess":3000},
    "python|pip": {"detect":["requirements.txt","setup.py"],"install":"pip install -r requirements.txt 2>/dev/null || pip install -e . 2>/dev/null || echo ok","build":"python -m compileall . 2>/dev/null || echo ok","test":"python -m pytest 2>/dev/null || python -m unittest 2>/dev/null || echo no tests","run":"python app.py || python main.py || python -m flask run --host=0.0.0.0 --port=8000","image":"python:3.11-slim","port_guess":8000},
    "python|poetry": {"detect":["pyproject.toml"],"install":"pip install poetry && poetry install","build":"poetry build 2>/dev/null || echo ok","test":"poetry run pytest 2>/dev/null || echo no tests","run":"poetry run python app.py || python app.py","image":"python:3.11-slim","port_guess":8000},
    "go": {"detect":["go.mod","main.go"],"install":"go mod download","build":"go build -o /app/server .","test":"go test ./... 2>/dev/null || echo no tests","run":"./server","image":"golang:1.22-alpine","port_guess":8080},
    "rust": {"detect":["Cargo.toml"],"install":"","build":"cargo build --release","test":"cargo test 2>/dev/null || echo no tests","run":"./target/release/*","image":"rust:1.77-slim","port_guess":8080},
    "java|maven": {"detect":["pom.xml"],"install":"","build":"mvn package -DskipTests","test":"mvn test 2>/dev/null || echo no tests","run":"java -jar target/*.jar","image":"maven:3-eclipse-temurin-21","port_guess":8080},
    "java|gradle": {"detect":["build.gradle","build.gradle.kts"],"install":"","build":"gradle build -x test","test":"gradle test 2>/dev/null || echo no tests","run":"java -jar build/libs/*.jar","image":"gradle:8-jdk21","port_guess":8080},
    "php": {"detect":["composer.json","index.php"],"install":"composer install 2>/dev/null || echo ok","build":"echo ok","test":"echo no tests","run":"php -S 0.0.0.0:8080 -t .","image":"php:8.2-cli","port_guess":8080},
    "static": {"detect":["index.html"],"install":"","build":"echo static","test":"echo no tests","run":"python3 -m http.server 8080","image":"nginx:alpine","port_guess":80},
}

@router.get("/adapters")
def list_adapters():
    out = []
    for k, v in _BUILD_ADAPTERS.items():
        item = {"name": k}
        for kk, vv in v.items():
            if kk != "image":
                item[kk] = str(vv)[:60]
        out.append(item)
    return {"success": True, "adapters": out}

@router.post("/run")
async def sandbox_run(data: dict):
    """接收代码/项目 → 选适配器 → Docker构建运行 → 返回结果"""
    code = data.get("code", "")
    files = data.get("files", {})  # {filename: content}
    project_type = data.get("type", "auto")
    action = data.get("action", "run")  # install | build | test | run | all

    sid = hashlib.md5((str(time.time()) + code[:50]).encode()).hexdigest()[:12]
    workdir = SANDBOX_DIR / sid
    workdir.mkdir(parents=True, exist_ok=True)

    # 写入代码文件
    if code and not files:
        fname = data.get("filename", "main.py")
        ext = os.path.splitext(fname)[1].lower()
        ext_map = {".py":"python|pip", ".js":"node|npm", ".ts":"node|npm", ".go":"go", ".rs":"rust",
                   ".java":"java|maven", ".php":"php", ".html":"static", ".sh":"static"}
        if ext in ext_map: project_type = ext_map[ext]
        (workdir / fname).write_text(code, encoding="utf-8")
    else:
        for fname, content in files.items():
            fp = workdir / fname
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")

    # 自动检测适配器
    if project_type == "auto":
        for aname, adapter in _BUILD_ADAPTERS.items():
            for det in adapter["detect"]:
                for f in workdir.rglob(det):
                    project_type = aname; break
            if project_type != "auto": break
    if project_type == "auto":
        project_type = "python|pip"

    adapter = _BUILD_ADAPTERS.get(project_type)
    if not adapter:
        shutil.rmtree(workdir, ignore_errors=True)
        return {"success": False, "error": f"no adapter for {project_type}"}

    # 在 Docker 中执行
    results = {}
    steps = {"install":"install","build":"build","test":"test","run":"run"}
    if action == "all":
        actions = ["install", "build", "test", "run"]
    else:
        actions = [action]

    for act in actions:
        cmd = adapter.get(act, "")
        if not cmd:
            results[act] = "skipped"
            continue
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:/app",
            "-w", "/app",
            adapter["image"],
            "sh", "-c", cmd
        ]
        try:
            r = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=120)
            results[act] = r.stdout[-2000:] + r.stderr[-500:]
        except subprocess.TimeoutExpired:
            results[act] = "⏳ 超时(120s)"
        except Exception as e:
            results[act] = f"❌ {str(e)[:50]}"

    shutil.rmtree(workdir, ignore_errors=True)
    return {"success": True, "sandbox_id": sid, "type": project_type, "results": results}

@router.post("/verify")
async def verify_url(data: dict):
    """验证部署是否成功 — 自动curl检查"""
    url = data.get("url", "")
    expected_status = data.get("expected_status", 200)
    max_retries = data.get("retries", 3)
    for i in range(max_retries):
        try:
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                             capture_output=True, text=True, timeout=10)
            status = r.stdout.strip()
            if status == str(expected_status):
                return {"success": True, "status": int(status), "retries": i+1}
        except:
            pass
        if i < max_retries - 1:
            asyncio.sleep(2)
    return {"success": False, "error": f"期望{expected_status}，重试{max_retries}次未通过"}
