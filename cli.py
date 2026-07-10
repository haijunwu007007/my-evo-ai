"""
AUTO-EVO-AI CLI — 命令行使用全部系统功能

用法:
  python cli.py chat "你的问题"          聊天/查询
  python cli.py status                   系统状态
  python cli.py agents                   智能体列表
  python cli.py team "任务描述"          团队讨论
  python cli.py industry <编号>          启动行业
  python cli.py tools                    工具状态
  python cli.py workflow <名称>          执行工作流
  python cli.py help                     帮助
"""

import sys, json, os, subprocess, time, textwrap

# Windows 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "http://127.0.0.1:8765/api/v1"
BASE = os.path.dirname(os.path.abspath(__file__))

def _req(method, path, data=None):
    import urllib.request, urllib.error
    url = API + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
        headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

def cmd_chat(args):
    """聊天/查询 — python cli.py chat "你的问题" """
    logger.info( args: return print("用法: python cli.py chat \"你的问题\""))
    r = _req("POST", "/chat", {"message": " ".join(args)})
    result = r.get("result", r.get("error", json.dumps(r)))
    logger.info(textwrap.dedent(result)))

def cmd_status(args):
    """系统状态 — python cli.py status"""
    r = _req("GET", "/status")
    if r.get("success"):
        logger.info(f"✅ 系统运行中"))
        logger.info(f"   模块: {r.get('modules_loaded',0)}/{r.get('modules_total',0)}"))
        logger.info(f"   版本: {r.get('api_version','-')}"))
    else:
        logger.info(f"❌ 获取状态失败: {r.get('error','-')}"))

def cmd_agents(args):
    """列出智能体 — python cli.py agents"""
    r = _req("GET", "/agents")
    if r.get("success"):
        logger.info(f"🤖 可用智能体 ({len(r['agents'])}个):"))
        for a in r["agents"]:
            logger.info(f"  {a['emoji']} {a['name']} — {a['role']}"))
    else:
        logger.info(f"❌ 错误: {r.get('error','-')}"))

def cmd_team(args):
    """团队讨论 — python cli.py team "任务描述" """
    logger.info( args: return print("用法: python cli.py team \"任务描述\""))
    task = " ".join(args)
    room = _req("POST", "/agents/rooms", {"task": task})
    if not room.get("success"):
        logger.info( print(f"❌ 创建房间失败: {room.get('error','')}"))
    rid = room["room_id"]
    logger.info(f"📋 任务: {task}"))
    logger.info(f"👥 参与: {', '.join(room['agents'])}"))
    logger.info("🔄 智能体讨论中..."))
    disc = _req("POST", f"/agents/rooms/{rid}/start")
    if disc.get("success"):
        r = _req("GET", f"/agents/rooms/{rid}")
        if r.get("success"):
            for m in r["room"]["messages"]:
                logger.info(f"\n[{m['emoji']} {m['name']}] {m['content']}"))
    logger.info("\n✅ 讨论完成"))

def cmd_industry(args):
    """启动行业 — python cli.py industry <编号>"""
    logger.info( args: return print("用法: python cli.py industry <编号1-100>"))
    n = args[0]
    logger.info(f"🏭 启动行业 #{n}..."))
    subprocess.Popen(["python", os.path.join(BASE, "_deploy_industry.py"), n],
        cwd=BASE, shell=True)
    logger.info(f"✅ 行业 #{n} 启动中，打开 http://localhost:8765/ 使用"))

def cmd_tools(args):
    """工具状态 — python cli.py tools"""
    r = _req("GET", "/tools/health")
    if r.get("success"):
        alive = r.get("alive", 0)
        total = r.get("total", 0)
        logger.info(f"🔧 工具状态: {alive}/{total} 运行中"))
        for name, info in r.get("tools", {}).items():
            status = "✅ 运行中" if info.get("alive") else "⏹️ 已停止"
            logger.info(f"  {status} {name} (:${info.get('port','?')})"))
    else:
        logger.info(f"❌ 错误: {r.get('error','-')}"))

def cmd_workflow(args):
    """执行工作流 — python cli.py workflow <名称>"""
    if not args:
        r = _req("GET", "/workflows")
        if r.get("success"):
            logger.info("📋 可用工作流:"))
            for w in r.get("workflows", []):
                logger.info(f"  • {w['name']} ({w['id']}) — {w.get('description','')}"))
        return
    name = args[0]
    r = _req("POST", f"/workflow/run/{name}")
    if r.get("success"):
        logger.info(f"✅ 工作流 {name} 已执行 (ID: {r.get('execution_id','')})"))
    else:
        logger.info(f"❌ 错误: {r.get('error','-')}"))

def cmd_help(args):
    """显示帮助"""
    logger.info(__doc__))

CMDS = {
    "chat": cmd_chat, "c": cmd_chat,
    "status": cmd_status, "st": cmd_status,
    "agents": cmd_agents, "a": cmd_agents,
    "team": cmd_team, "t": cmd_team,
    "industry": cmd_industry, "i": cmd_industry,
    "tools": cmd_tools,
    "workflow": cmd_workflow, "w": cmd_workflow,
    "help": cmd_help, "h": cmd_help,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        logger.info(__doc__))
        sys.exit(0)
    CMDS[sys.argv[1]](sys.argv[2:])
