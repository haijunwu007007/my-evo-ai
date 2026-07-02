"""RAVEN 集成桥接 — 连接 RAVEN 自我进化智能体框架
- RAVEN 存在时：委托其处理（10万技能+自进化+记忆）
- RAVEN 不存在时：回到本系统自有能力（yoyo_evolve+agent_memos）
"""
import os, json, subprocess, shutil, time
from pathlib import Path
from typing import Optional

from core.logging_config import get_logger
logger = get_logger("evo.raven")

RAVEN_HOME = Path.home() / ".raven"
RAVEN_BIN = shutil.which("raven") or RAVEN_HOME / "bin" / "raven"
RAVEN_INSTALLED = RAVEN_BIN.exists() or RAVEN_BIN.parent.exists()
EVEROS_HOME = Path.home() / ".everos"
EVEROS_INSTALLED = EVEROS_HOME.exists()

# ════════════════════════════════════════════════════════════
# 安装管理
# ════════════════════════════════════════════════════════════

def is_installed() -> bool:
    """检查 RAVEN 是否已安装"""
    return RAVEN_INSTALLED or shutil.which("raven") is not None

def install() -> dict:
    """一键安装 RAVEN + EverOS"""
    import subprocess as sp
    try:
        logger.info("[RAVEN] 开始安装...")
        r = sp.run(
            ["curl", "-fsSL", "https://raven.evermind.ai/install.sh"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            return {"success": False, "error": f"下载安装脚本失败: {r.stderr[:200]}"}
        # 执行安装
        r2 = sp.run(["bash"], input=r.stdout, capture_output=True, text=True, timeout=300)
        if r2.returncode == 0:
            logger.info("[RAVEN] 安装成功")
            global RAVEN_INSTALLED
            RAVEN_INSTALLED = True
            return {"success": True, "message": "RAVEN+EverOS 安装成功"}
        return {"success": False, "error": f"安装执行失败: {r2.stderr[:200]}"}
    except sp.TimeoutExpired:
        return {"success": False, "error": "安装超时（>5分钟）"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

# ════════════════════════════════════════════════════════════
# RAVEN 命令执行桥接
# ════════════════════════════════════════════════════════════

def _run_raven(args: list, timeout: int = 60) -> dict:
    """执行 RAVEN CLI 命令"""
    if not is_installed():
        return {"success": False, "fallback": True, "error": "RAVEN 未安装"}
    try:
        cmd = [str(RAVEN_BIN) if RAVEN_BIN.exists() else "raven"] + args
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"success": r.returncode == 0, "stdout": r.stdout[:2000], "stderr": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "超时"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

# ════════════════════════════════════════════════════════════
# 核心 API 桥接
# ════════════════════════════════════════════════════════════

def search_skills(query: str, limit: int = 20) -> list:
    """搜索 RAVEN 的 10 万技能（无 RAVEN 时返回空列表）"""
    if not is_installed():
        return []
    result = _run_raven(["skills", "search", query, "--limit", str(limit)])
    if result.get("success"):
        try:
            return json.loads(result.get("stdout", "[]"))
        except json.JSONDecodeError:
            pass
    return []

def apply_evolution(target: str) -> dict:
    """触发 RAVEN 自我进化（聚焦指定目标）"""
    if not is_installed():
        return {"success": False, "fallback": True, "message": "RAVEN 未安装，使用本地 yoyo_evolve"}
    return _run_raven(["evolve", target], timeout=120)

def get_memory(query: str) -> dict:
    """从 EverOS 记忆层检索（无 EverOS 时使用本地 agent_memos）"""
    if not EVEROS_INSTALLED:
        return {"success": False, "fallback": True}
    result = _run_raven(["memory", "search", query])
    return result if result.get("success") else {"success": False, "fallback": True}

# ════════════════════════════════════════════════════════════
# 统一入口（RAVEN 优先 → 本地降级）
# ════════════════════════════════════════════════════════════

def full_cycle() -> dict:
    """全栈自进化：优先用 RAVEN，降级到本地 yoyo_evolve"""
    if is_installed():
        logger.info("[RAVEN] 使用 RAVEN 执行全栈进化")
        return _run_raven(["evolve", "--full-cycle"], timeout=300)
    logger.info("[RAVEN] RAVEN 未安装，使用本地 yoyo_evolve")
    from api.agents.yoyo_evolve import auto_evolve
    return auto_evolve()

def auto_fix_all(base_dir=None) -> dict:
    """自动修复：优先用 RAVEN 修复引擎"""
    if is_installed():
        return _run_raven(["fix", "--all"], timeout=180)
    from api.agents.yoyo_evolve import auto_fix_all as local_fix
    return local_fix(base_dir)

def get_status() -> dict:
    """获取 RAVEN + 本系统状态"""
    raven_st = {"installed": is_installed()}
    if is_installed():
        r = _run_raven(["status"])
        raven_st["version"] = r.get("stdout", "").strip()[:100] if r.get("success") else "unknown"
        raven_st["skills_count"] = "100k+"
    # 本地状态
    from api.agents.yoyo_evolve import get_status as local_status
    local_st = local_status()
    return {
        "raven": raven_st,
        "local_yoyo_evolve": local_st,
        "active": "raven" if is_installed() else "local",
    }
