"""BrowserAct + codebase-memory-mcp 工具代理"""
import logging
logger = logging.getLogger("evo.agent_tools_browseract")

import subprocess, shutil, json, os, httpx
from api.infra import logger

# ════════════════════════════════════════════════════
# BrowserAct 工具
# ════════════════════════════════════════════════════

def browseract_stealth_extract(url: str) -> dict:
    """BrowserAct：反爬提取页面内容"""
    if not shutil.which("browser-act"):
        return {"success": False, "error": "browser-act 未安装，执行: pip install browser-act-skills"}
    try:
        r = subprocess.run(["browser-act", "stealth-extract", url], capture_output=True, text=True, timeout=120)
        return {"success": r.returncode == 0, "data": r.stdout[:3000], "error": r.stderr[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def browseract_browse(url: str, session: str = "evo") -> dict:
    """BrowserAct：打开浏览器访问页面"""
    if not shutil.which("browser-act"):
        return {"success": False, "error": "browser-act 未安装"}
    try:
        r = subprocess.run(["browser-act", "--session", session, "browser", "open", url],
                          capture_output=True, text=True, timeout=60)
        return {"success": r.returncode == 0, "data": r.stdout[:2000]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ════════════════════════════════════════════════════
# codebase-memory-mcp 工具
# ════════════════════════════════════════════════════

_CODEMEM_BIN = shutil.which("codebase-memory-mcp") or os.path.expanduser("~/.local/bin/codebase-memory-mcp")

def codemem_index(path: str) -> dict:
    """codebase-memory-mcp：索引代码库"""
    if not os.path.exists(_CODEMEM_BIN):
        return {"success": False, "error": "codebase-memory-mcp 未安装", "fix": "pip install codebase-memory-mcp"}
    try:
        r = subprocess.run([_CODEMEM_BIN, "index", "--path", path], capture_output=True, text=True, timeout=300)
        return {"success": r.returncode == 0, "data": r.stdout[:2000]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def codemem_query(path: str, query: str) -> dict:
    """codebase-memory-mcp：查询代码知识"""
    if not os.path.exists(_CODEMEM_BIN):
        return {"success": False, "error": "codebase-memory-mcp 未安装"}
    try:
        r = subprocess.run([_CODEMEM_BIN, "query", "--path", path, "--query", query],
                          capture_output=True, text=True, timeout=60)
        return {"success": r.returncode == 0, "data": r.stdout[:3000]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ════════════════════════════════════════════════════
# 注册到工具系统
# ════════════════════════════════════════════════════

_TOOLS = [
    {"name": "browseract_extract", "fn": browseract_stealth_extract,
     "desc": "BrowserAct 反爬提取页面内容（绕过验证码/反爬）"},
    {"name": "browseract_browse", "fn": browseract_browse,
     "desc": "BrowserAct 打开浏览器访问网页"},
    {"name": "codemem_index", "fn": codemem_index,
     "desc": "codebase-memory-mcp 索引代码库为知识图谱"},
    {"name": "codemem_query", "fn": codemem_query,
     "desc": "codebase-memory-mcp 查询代码知识"},
]

def get_browseract_tools():
    return _TOOLS
