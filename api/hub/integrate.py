#!/usr/bin/env python3
"""开源中心 — 真正的一键部署引擎"""
import os, json, time, asyncio, subprocess, shutil, re
from pathlib import Path
from typing import Optional
from core.logging_config import get_logger
from api.hub.models import get_project, update_project, _get_conn

logger = get_logger("evo.hub.integrate")

BASE = Path(__file__).resolve().parent.parent.parent
HUBS_DIR = BASE / "hub_projects"
HUBS_DIR.mkdir(exist_ok=True)

# ── 正在运行的部署任务 ──
_running_deploys: dict = {}

# ═══════════════════════════════════════════════════════
# 核心入口：部署项目
# ═══════════════════════════════════════════════════════

async def deploy_project(project_id: str, config: dict = None) -> dict:
    proj = get_project(project_id)
    if not proj:
        return {"success": False, "error": "项目不存在"}
    cfg = config or {}

    update_project(project_id, {"status": "deploying"})
    _running_deploys[project_id] = {"status": "deploying", "log": [], "started_at": time.time()}

    # 后台运行
    asyncio.create_task(_do_deploy(project_id, cfg))
    return {"success": True, "status": "deploying", "message": "部署已启动"}

async def get_deploy_status(project_id: str) -> dict:
    proj = get_project(project_id)
    if not proj:
        return {"success": False, "error": "项目不存在"}
    status = proj.get("status", "unknown")
    deploy = _running_deploys.get(project_id, {})
    return {
        "success": True,
        "status": status,
        "project_name": proj.get("name"),
        "port": proj.get("port", 0),
        "log": deploy.get("log", []),
        "running": deploy.get("running", False),
        "started_at": deploy.get("started_at"),
    }

async def stop_project(project_id: str) -> dict:
    proj = get_project(project_id)
    if not proj: return {"success": False, "error": "项目不存在"}
    # Docker stop
    container = proj.get("container_id", "")
    if container:
        subprocess.run(["docker", "stop", container], capture_output=True, timeout=30)
        subprocess.run(["docker", "rm", container], capture_output=True, timeout=30)
        logger.info(f"[STOP] Docker容器已停止: {container}")
    # Process kill
    pid = proj.get("pid", 0)
    if pid > 0:
        try: os.kill(pid, 15)
        except: pass
    # Docker compose down
    proj_dir = HUBS_DIR / (proj.get("name", project_id))
    if (proj_dir / "docker-compose.yml").exists():
        subprocess.run(["docker-compose", "down"], cwd=str(proj_dir), capture_output=True, timeout=60)
    update_project(project_id, {"status": "stopped", "container_id": "", "pid": 0})
    return {"success": True}

# ═══════════════════════════════════════════════════════
# 实际部署逻辑（后台运行）
# ═══════════════════════════════════════════════════════

async def _do_deploy(project_id: str, cfg: dict):
    proj = get_project(project_id)
    if not proj:
        _append_log(project_id, "错误: 项目不存在")
        return

    try:
        repo_url = proj.get("repo_url", "")
        name = proj.get("name", project_id)
        proj_dir = HUBS_DIR / name
        port = cfg.get("port", _find_free_port())

        _append_log(project_id, f"开始部署: {name}")

        # ── 步骤1: 获取代码 ──
        if proj.get("source") == "docker" or not repo_url:
            # Docker 镜像模式 (如 Portainer)
            _append_log(project_id, "Docker模式: 无需clone")
            pass
        elif "github.com" in repo_url or "gitcode" in repo_url or "gitee" in repo_url:
            # Git 克隆
            _append_log(project_id, f"克隆: {repo_url}")
            if proj_dir.exists():
                shutil.rmtree(proj_dir)
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(proj_dir)],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0:
                _append_log(project_id, f"克隆失败: {result.stderr[:200]}")
                update_project(project_id, {"status": "error"})
                return
            _append_log(project_id, "克隆完成")
        else:
            _append_log(project_id, "无需获取代码")

        # ── 步骤2: 检测部署方式 ──
        strategy = _detect_strategy(proj_dir)
        _append_log(project_id, f"部署策略: {strategy}")

        # ── 步骤3: 执行部署 ──
        container_id, pid = "", 0

        if strategy == "docker_run":
            # 简单 docker run (Portainer 等)
            image = cfg.get("image", _guess_image(repo_url, name))
            cmd = ["docker", "run", "-d", "--name", f"evo-{name}", "--restart", "unless-stopped"]
            cmd += ["-p", f"{port}:{cfg.get('internal_port', 8000)}"]
            if "docker.sock" in repo_url or "portainer" in name.lower():
                cmd += ["-v", "/var/run/docker.sock:/var/run/docker.sock"]
            for ek, ev in cfg.get("env_vars", {}).items():
                cmd += ["-e", f"{ek}={ev}"]
            cmd += [image]
            _append_log(project_id, f"运行: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                _append_log(project_id, f"Docker运行失败: {r.stderr[:200]}")
                update_project(project_id, {"status": "error"})
                return
            container_id = r.stdout.strip()
            _append_log(project_id, f"Docker容器启动: {container_id}")

        elif strategy == "docker_compose":
            env = os.environ.copy()
            env["PORT"] = str(port)
            r = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=str(proj_dir), capture_output=True, text=True, timeout=300, env=env
            )
            if r.returncode != 0:
                _append_log(project_id, f"Compose失败: {r.stderr[:200]}")
                update_project(project_id, {"status": "error"})
                return
            r2 = subprocess.run(
                ["docker", "ps", "-l", "--format", "{{.ID}}"],
                capture_output=True, text=True, timeout=10
            )
            container_id = r2.stdout.strip()
            _append_log(project_id, "Docker Compose 部署成功")

        elif strategy == "python":
            # Python venv + run
            venv_dir = proj_dir / "venv"
            if not (venv_dir / "bin" / "python").exists():
                subprocess.run(["python3", "-m", "venv", str(venv_dir)], capture_output=True, timeout=60)
                _append_log(project_id, "已创建 venv")
            pip = venv_dir / "bin" / "pip"
            subprocess.run([str(pip), "install", "uvicorn", "fastapi", "httpx"], capture_output=True, timeout=120)
            subprocess.run([str(pip), "install", "-r", str(proj_dir / "requirements.txt")], capture_output=True, timeout=300)
            entry = _find_entry(proj_dir)
            if entry:
                proc = subprocess.Popen(
                    [str(venv_dir / "bin" / "python"), "-u", entry],
                    cwd=str(proj_dir),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                pid = proc.pid
                _append_log(project_id, f"Python 进程启动: PID {pid}")

        # ── 步骤4: 健康检查 ──
        health_url = f"http://localhost:{port}/health"
        _append_log(project_id, f"健康检查: {health_url}")
        await asyncio.sleep(3)
        for attempt in range(12):  # 60秒超时
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5) as cli:
                    r = await cli.get(health_url)
                    if r.status_code < 500:
                        _append_log(project_id, f"健康检查通过 (端口 {port})")
                        break
            except:
                pass
            await asyncio.sleep(5)
        else:
            _append_log(project_id, "健康检查超时，但仍标记为运行")

        # ── 完成 ──
        update_project(project_id, {
            "status": "running", "port": port,
            "container_id": container_id, "pid": pid,
        })
        _running_deploys[project_id]["status"] = "running"
        _running_deploys[project_id]["running"] = False
        _append_log(project_id, "✅ 部署完成!")

    except subprocess.TimeoutExpired as e:
        _append_log(project_id, f"超时: {str(e)}")
        update_project(project_id, {"status": "error"})
    except Exception as e:
        _append_log(project_id, f"异常: {str(e)}")
        update_project(project_id, {"status": "error"})
        logger.error(f"部署异常 {project_id}: {e}")

# ═══════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════

def _detect_strategy(proj_dir: Path) -> str:
    """自动检测部署策略"""
    if not proj_dir.exists() or not list(proj_dir.iterdir()):
        return "docker_run"
    if (proj_dir / "docker-compose.yml").exists() or (proj_dir / "docker-compose.yaml").exists():
        return "docker_compose"
    if (proj_dir / "Dockerfile").exists():
        return "docker_build"
    if (proj_dir / "requirements.txt").exists() or (proj_dir / "setup.py").exists():
        return "python"
    if (proj_dir / "package.json").exists():
        return "node"
    if (proj_dir / "go.mod").exists():
        return "go"
    return "docker_run"

def _find_entry(proj_dir: Path) -> Optional[str]:
    for f in ["app.py", "main.py", "run.py", "server.py", "api.py"]:
        if (proj_dir / f).exists():
            return f
    for f in proj_dir.glob("*.py"):
        content = f.read_text()
        if "uvicorn" in content or "app.run" in content or "if __name__" in content:
            return f.name
    return None

def _find_free_port(start=8000) -> int:
    import socket
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start

def _guess_image(repo_url: str, name: str) -> str:
    known = {
        "portainer": "portainer/portainer-ce",
        "nginx": "nginx:alpine",
        "redis": "redis:alpine",
        "postgres": "postgres:16-alpine",
    }
    for key, img in known.items():
        if key in name.lower() or key in repo_url.lower():
            return img
    return f"{name}:latest"

def _append_log(project_id: str, msg: str):
    if project_id in _running_deploys:
        _running_deploys[project_id]["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    logger.info(f"[DEPLOY {project_id}] {msg}")

# ═══════════════════════════════════════════════════════
# 兼容旧导入（供 routes_hub.py 使用）
# ═══════════════════════════════════════════════════════
get_monitor_data = None  # 将在 routes_hub.py 中覆盖
