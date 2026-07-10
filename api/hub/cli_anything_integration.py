"""CLI-Anything 集成 — 将任意软件转为Agent工具"""
import logging
logger = logging.getLogger("evo.cli_anything_integration")

import os, json, subprocess, tempfile, time

CLI_HUB_INSTALLED = False

def check_cli_hub() -> dict:
    """检查是否安装了 cli-anything-hub"""
    try:
        r = subprocess.run(["pip", "list", "--format=columns"], capture_output=True, text=True, timeout=10)
        installed = "cli-anything" in r.stdout.lower()
        return {"ok": True, "installed": installed, "note": "已安装" if installed else "未安装，运行 pip install cli-anything-hub"}
    except: return {"ok": False, "data": "检查失败"}

def cli_hub_search(query: str) -> dict:
    """搜索CLI Hub中的工具"""
    try:
        r = subprocess.run(["cli-hub", "search", query], capture_output=True, text=True, timeout=15)
        out = (r.stdout + r.stderr)[:2000]
        return {"ok": r.returncode == 0, "data": out or "无结果", "source": "cli-hub"}
    except FileNotFoundError:
        return {"ok": False, "data": "cli-hub 未安装，请运行: pip install cli-anything-hub"}
    except Exception as e:
        return {"ok": False, "data": f"搜索失败: {e}"}

def cli_hub_install(name: str) -> dict:
    """安装CLI工具"""
    try:
        r = subprocess.run(["cli-hub", "install", name], capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "data": (r.stdout + r.stderr)[:1000]}
    except: return {"ok": False, "data": f"安装 {name} 失败"}

def cli_anything_generate(repo_url: str) -> dict:
    """为任意GitHub仓库生成CLI接口"""
    try:
        import httpx
        r = httpx.post("https://api.clianything.cc/v1/generate", json={
            "repo_url": repo_url, "auto_install": True
        }, timeout=300)
        return {"ok": r.is_success, "data": r.json() if r.is_success else r.text[:500]}
    except Exception as e:
        return {"ok": False, "data": f"生成失败: {e}"}

def cli_execute(command: str, cwd: str = None) -> dict:
    """执行CLI工具命令"""
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True,
                          timeout=60, cwd=cwd or os.getcwd())
        return {"ok": r.returncode == 0, "stdout": r.stdout[:3000], "stderr": r.stderr[:1000],
                "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "data": "执行超时(60s)"}
    except Exception as e:
        return {"ok": False, "data": f"执行失败: {e}"}
