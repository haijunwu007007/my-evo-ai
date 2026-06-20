# -*- coding: utf-8 -*-
"""
🔧 CLI 能力网关 — 统一管理所有 CLI 工具
桥接: aichat(LLM) / lazydocker(容器) / thefuck(纠错) / fzf(搜索) / goose(Agent)
"""
import os, json, subprocess, shutil, asyncio, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/cli", tags=["cli"])

# ===== 注册的 CLI 工具 =====
CLI_TOOLS = {
    "aichat": {"name": "AIChat", "desc": "终端 LLM 对话", "cmd": "aichat", "install": "pip install aichat", "builtin": True},
    "goose": {"name": "Goose", "desc": "Agent 框架", "cmd": "goose", "install": "pip install goose-ai", "builtin": False},
    "thefuck": {"name": "TheFuck", "desc": "命令纠错", "cmd": "fuck", "install": "pip install thefuck", "builtin": True},
    "fzf": {"name": "FZF", "desc": "模糊搜索", "cmd": "fzf", "install": "apt install fzf", "builtin": True},
    "lazydocker": {"name": "LazyDocker", "desc": "Docker TUI", "cmd": "lazydocker", "install": "curl ... | bash", "builtin": False},
    "pipx": {"name": "PipX", "desc": "Python CLI 管理", "cmd": "pipx", "install": "pip install pipx", "builtin": True},
    "ffmpeg": {"name": "FFmpeg", "desc": "视频处理", "cmd": "ffmpeg", "install": "apt install ffmpeg", "builtin": True},
    "btop": {"name": "BTop", "desc": "系统监控 TUI", "cmd": "btop", "install": "apt install btop", "builtin": True},
    "officecli": {"name": "OfficeCLI", "desc": "Word/Excel/PPT CLI", "cmd": "officecli", "install": "bash scripts/setup_new_server.sh", "builtin": False},
    "n8n": {"name": "n8n", "desc": "工作流引擎 CLI", "cmd": "n8n", "install": "npm install -g n8n", "builtin": False},
}

def _check_tool(name: str) -> bool:
    """检查 CLI 工具是否已安装"""
    info = CLI_TOOLS.get(name)
    if not info:
        return False
    cmd = info["cmd"]
    r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
    return r.returncode == 0

def _get_path():
    """获取完整 PATH"""
    return os.environ.get("PATH", "") + ":" + os.path.expanduser("~/.local/bin") + ":/usr/local/bin"

@router.get("/tools")
def list_tools():
    """列出所有已注册 CLI 工具及安装状态"""
    tools = {}
    for name, info in CLI_TOOLS.items():
        installed = _check_tool(name)
        tools[name] = {**info, "installed": installed}
    return {"success": True, "tools": tools}

class ExecRequest(BaseModel):
    cmd: str
    args: str = ""
    timeout: int = 30

@router.post("/exec")
async def exec_cli(data: ExecRequest):
    """执行 CLI 命令（安全受限）"""
    # 安全: 只允许白名单命令
    allowed = list(CLI_TOOLS.keys()) + ["docker", "docker-compose", "git", "node", "npm", "python3", "pip3", "curl", "wget"]
    cmd_name = data.cmd.split()[0]
    if cmd_name not in allowed:
        return {"success": False, "error": f"命令 {cmd_name} 不在白名单中"}
    
    env = os.environ.copy()
    env["PATH"] = _get_path()
    try:
        full_cmd = f"{data.cmd} {data.args}".strip()
        r = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=data.timeout, env=env)
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout[-2000:],
            "stderr": r.stderr[-500:],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"执行超时 ({data.timeout}s)"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.post("/aichat")
async def cli_aichat(data: dict):
    """通过 AIChat CLI 与 LLM 对话"""
    if not _check_tool("aichat"):
        return {"success": False, "error": "aichat 未安装", "install": "pip install aichat"}
    msg = data.get("message", "")
    if not msg:
        return {"success": False, "error": "需要 message 参数"}
    env = os.environ.copy()
    env["PATH"] = _get_path()
    try:
        r = subprocess.run(["aichat", msg], capture_output=True, text=True, timeout=60, env=env)
        return {"success": r.returncode == 0, "result": r.stdout[-2000:], "error": r.stderr[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.get("/docker/ps")
def docker_ps():
    """Docker 容器列表"""
    try:
        r = subprocess.run(["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                          capture_output=True, text=True, timeout=10)
        lines = [l.split("\t") for l in r.stdout.strip().split("\n") if l.strip()]
        containers = [{"id": l[0], "name": l[1], "status": l[2], "ports": l[3] if len(l)>3 else ""} for l in lines]
        return {"success": True, "containers": containers, "total": len(containers)}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.get("/docker/images")
def docker_images():
    """Docker 镜像列表"""
    try:
        r = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}"],
                          capture_output=True, text=True, timeout=10)
        images = [{"name": l.split("\t")[0], "size": l.split("\t")[1] if "\t" in l else ""}
                  for l in r.stdout.strip().split("\n") if l.strip()]
        return {"success": True, "images": images, "total": len(images)}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.post("/docker/exec")
async def docker_exec(data: dict):
    """执行 Docker 命令"""
    cmd = data.get("cmd", "ps")
    try:
        r = subprocess.run(["docker"] + cmd.split(), capture_output=True, text=True, timeout=30)
        return {"success": r.returncode == 0, "stdout": r.stdout[-2000:], "stderr": r.stderr[-200:]}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.get("/thefuck")
def cli_thefuck(cmd: str = ""):
    """命令纠错"""
    if not _check_tool("thefuck"):
        return {"success": False, "error": "thefuck 未安装"}
    if not cmd:
        return {"success": False, "error": "需要 cmd 参数"}
    env = os.environ.copy()
    env["PATH"] = _get_path()
    try:
        r = subprocess.run(f"echo '{cmd}' | thefuck", shell=True, capture_output=True, text=True, timeout=15, env=env)
        return {"success": True, "correction": r.stdout.strip(), "original": cmd}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}
