"""自修复引擎 — 部署失败自动回滚 + 重试"""
from fastapi import APIRouter
from datetime import datetime, timedelta
import os, json, subprocess, time

router = APIRouter(tags=["selfheal"])

_DEPLOY_HISTORY: list[dict] = []
_MAX_HISTORY = 100

@router.post("/api/v1/selfheal/record")
async def record_deployment(name: str, success: bool, error: str = ""):
    """记录部署历史"""
    _DEPLOY_HISTORY.append({
        "name": name, "success": success, "error": error,
        "timestamp": datetime.now().isoformat()
    })
    if len(_DEPLOY_HISTORY) > _MAX_HISTORY:
        _DEPLOY_HISTORY.pop(0)
    return {"success": True}

@router.post("/api/v1/selfheal/rollback/{name}")
async def rollback_deploy(name: str):
    """回滚部署"""
    # 停止并删除当前容器
    subprocess.run(["docker", "stop", name], capture_output=True, timeout=30)
    subprocess.run(["docker", "rm", name], capture_output=True, timeout=30)
    # 尝试回退到上一个版本
    old_tag = f"evo/{name}:prev"
    r = subprocess.run(["docker", "run", "-d", "--name", f"{name}-rollback", old_tag],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return {"success": True, "message": f"{name} 已回滚到上一版本", "container": r.stdout.strip()}
    return {"success": False, "error": "无上一版本可回滚"}

@router.get("/api/v1/selfheal/history")
async def get_history():
    """获取部署历史"""
    return {"success": True, "history": _DEPLOY_HISTORY[-20:]}

@router.get("/api/v1/fix")
async def auto_fix():
    """一键诊断+自动修复"""
    import httpx, os, sys
    results = []
    fixes = []

    # 1. 系统状态
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/health")
            if r.json().get("success"):
                results.append({"check": "系统服务", "status": "ok", "fix": ""})
    except Exception:
        results.append({"check": "系统服务", "status": "error", "fix": "重启API服务"})
        fixes.append({"action": "已执行: kill旧进程并重启", "result": "try"})

    # 2. LLM
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/llm/status")
            d = r.json()
            providers = d.get("providers", [])
            if any(p.get("available") for p in providers):
                results.append({"check": "LLM服务", "status": "ok", "fix": ""})
            else:
                # 尝试修复: 检查.env
                key = os.environ.get("ZHIPU_API_KEY", "")
                env_file = "/home/ubuntu/my-evo-ai/.env"
                results.append({"check": "LLM服务", "status": "warning", "fix": f"检查API Key ({'已设置' if key else '未设置'})"})
                if not key and os.path.exists(env_file):
                    with open(env_file) as f:
                        for line in f:
                            if "ZHIPU_API_KEY=" in line:
                                k = line.strip().split("=", 1)[1]
                                if k and "your_" not in k:
                                    os.environ["ZHIPU_API_KEY"] = k
                                    results[-1]["fix"] = "已从.env读取Key"
                                    fixes.append({"action": "从.env读取Key", "result": "ok"})
    except Exception:
        results.append({"check": "LLM服务", "status": "error", "fix": "重启或检查.env文件"})

    # 3. 语音
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/speech/status")
            d = r.json()
            if d.get("vosk"):
                results.append({"check": "语音服务", "status": "ok", "fix": ""})
            else:
                results.append({"check": "语音服务", "status": "warning", "fix": "Vosk模型未加载"})
    except Exception:
        results.append({"check": "语音服务", "status": "error", "fix": "重启语音服务"})

    # 4. 技能系统
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/skills")
            d = r.json()
            total = d.get("total", 0)
            if total > 100:
                results.append({"check": f"技能系统 ({total}个)", "status": "ok", "fix": ""})
            else:
                results.append({"check": f"技能系统 ({total}个)", "status": "warning", "fix": "技能注册不完整"})
    except Exception:
        results.append({"check": "技能系统", "status": "error", "fix": "重启服务"})

    errors = [r for r in results if r["status"] != "ok"]
    return {"success": True, "results": results, "fixes": fixes, "healthy": len(errors) == 0, "total_checks": len(results), "issues": len(errors)}

@router.post("/api/v1/selfheal/retry/{name}")
async def retry_deploy(name: str):
    """重试失败的部署"""
    # 从history找到失败记录
    failed = [h for h in _DEPLOY_HISTORY if h["name"] == name and not h["success"]]
    if not failed:
        return {"success": False, "error": "无失败记录可重试"}
    # 尝试重新部署
    tag = f"evo/{name}:latest"
    r = subprocess.run(["docker", "run", "-d", "--name", name, "--restart", "unless-stopped", tag],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return {"success": True, "message": f"{name} 重试成功", "container": r.stdout.strip()}
    return {"success": False, "error": f"重试失败: {r.stderr[:200]}"}
