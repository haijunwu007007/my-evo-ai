# -*- coding: utf-8 -*-
"""
🌐 Skills 平台集成网关 — 发现/安装/桥接任意第三方 Skills
支持: GitHub Skills仓库 / MCP市场 / 自定义Skills源
"""
from fastapi import APIRouter, Query
import os, json, subprocess, re, urllib.request, tempfile, shutil
from pathlib import Path

router = APIRouter(prefix="/api/v1/skills-platform", tags=["skills-platform"])
BASE = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = Path(os.path.expanduser("~/.workbuddy/skills/auto-discovered"))

# ===== 内置 Skills 源 =====
SKILL_SOURCES = {
    "github-trending": {
        "name": "GitHub Trending Skills",
        "desc": "从GitHub扫描热门AI Skills仓库",
        "type": "github",
    },
    "mcp-marketplace": {
        "name": "MCP Marketplace",
        "desc": "MCP协议工具市场",
        "type": "mcp",
    },
    "custom": {
        "name": "自定义Skills",
        "desc": "手动注册的Skills",
        "type": "custom",
    }
}

# ===== 预定义热门Skills模板 =====
BUILTIN_SKILLS = {
    "web-scraper": {"name": "网页抓取", "desc": "抓取网页内容转为Markdown", "source": "builtin", "cmd": "python3 -c \"import requests;print('ok')\""},
    "image-ocr": {"name": "图片OCR", "desc": "从图片提取文字", "source": "builtin", "cmd": "python3 -c \"import pytesseract;print('ocr')\""},
    "code-executor": {"name": "代码执行", "desc": "沙箱执行代码片段", "source": "builtin", "cmd": "python3 -c \"print('code')\""},
    "data-viz": {"name": "数据可视化", "desc": "生成图表", "source": "builtin", "cmd": "python3 -c \"import matplotlib;print('viz')\""},
    "translation": {"name": "翻译", "desc": "多语言翻译", "source": "builtin", "cmd": "python3 -c \"print('translate')\""},
    "summarizer": {"name": "摘要生成", "desc": "文本摘要", "source": "builtin", "cmd": "python3 -c \"print('sum')\""},
    "web-search": {"name": "网页搜索", "desc": "搜索引擎查询", "source": "builtin", "cmd": "python3 -c \"print('search')\""},
    "mcp-filesystem": {"name": "文件系统MCP", "desc": "读写文件系统", "source": "mcp", "cmd": "filesystem"},
    "mcp-github": {"name": "GitHub MCP", "desc": "GitHub API操作", "source": "mcp", "cmd": "github"},
    "mcp-puppeteer": {"name": "浏览器MCP", "desc": "Headless浏览器", "source": "mcp", "cmd": "puppeteer"},
}

@router.get("/sources")
def list_sources():
    """列出所有 Skills 源"""
    sources = {}
    for k, v in SKILL_SOURCES.items():
        sources[k] = v
    return {"success": True, "sources": sources}

@router.get("/list")
def list_skills(source: str = "", search: str = ""):
    """列出可用的Skills（支持按源过滤和搜索）"""
    result = []
    for name, info in BUILTIN_SKILLS.items():
        if source and info["source"] != source:
            continue
        if search and search.lower() not in name.lower() and search.lower() not in info["name"].lower():
            continue
        result.append({**info, "id": name})
    
    # 从文件系统扫描已安装的Skills
    if SKILLS_DIR.exists():
        for f in SKILLS_DIR.glob("**/SKILL.md"):
            try:
                c = f.read_text(encoding="utf-8")
                m = re.search(r'name:\s*["\']?(.+?)["\']?\n', c)
                sn = m.group(1).strip() if m else f.parent.name
                result.append({"name": sn, "desc": c[:80].replace("\n"," "), "source": "installed", "id": f.parent.name})
            except:
                pass
    
    return {"success": True, "skills": result, "total": len(result)}

@router.post("/install")
def install_skill(data: dict):
    """安装Skills到本地系统"""
    skill_id = data.get("skill_id", "")
    skill_info = BUILTIN_SKILLS.get(skill_id)
    if not skill_info:
        return {"success": False, "error": f"未找到Skills: {skill_id}"}
    
    # 创建SKILL.md
    target = SKILLS_DIR / skill_id
    target.mkdir(parents=True, exist_ok=True)
    skill_md = f"""---
name: "{skill_info['name']}"
description: "{skill_info['desc']}"
source: "{skill_info['source']}"
version: "1.0.0"
---

# {skill_info['name']}

{skill_info['desc']}

## 使用方法
{skill_info['cmd']}
"""
    (target / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return {"success": True, "skill": skill_id, "path": str(target)}

@router.delete("/{skill_id}")
def uninstall_skill(skill_id: str):
    """卸载Skills"""
    target = SKILLS_DIR / skill_id
    if target.exists():
        shutil.rmtree(target)
        return {"success": True, "removed": skill_id}
    return {"success": False, "error": "not found"}

@router.get("/discover")
def discover_skills():
    """自动发现系统已安装的Skills"""
    results = []
    # 检测外部CLI工具
    cli_checks = {
        "aichat": {"name": "AIChat", "cmd": "aichat"},
        "officecli": {"name": "OfficeCLI", "cmd": "officecli"},
        "lazydocker": {"name": "LazyDocker", "cmd": "lazydocker"},
        "n8n": {"name": "n8n", "cmd": "n8n"},
    }
    for name, info in cli_checks.items():
        r = subprocess.run(["which", info["cmd"]], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            results.append({"name": info["name"], "type": "cli", "status": "available", "path": r.stdout.strip()})
    
    # 检测MCP服务器
    mcp_config = Path.home() / ".workbuddy" / "mcp.json"
    if mcp_config.exists():
        try:
            mcps = json.loads(mcp_config.read_text())
            for name in mcps.get("mcpServers", {}):
                results.append({"name": name, "type": "mcp", "status": "available"})
        except:
            pass
    
    return {"success": True, "discovered": results, "total": len(results)}
