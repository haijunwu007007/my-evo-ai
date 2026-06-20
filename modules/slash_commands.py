from modules._base.enterprise_module import EnterpriseModule
"""
Grade: A
AUTO-EVO-AI V0.1 — 斜杠命令系统
注册式命令解析，支持 /help /status /review /search /context /clear /compact /plan
"""
from __future__ import annotations

__module_meta__ = {
    "id": "slash-commands",
    "name": "斜杠命令系统",
    "version": "V0.1",
    "group": "developer",
    "grade": "A",
    "description": "注册式斜杠命令解析，支持 /help /status /review /search /context /clear /compact /plan",
    "tags": ["slash", "commands", "chat"],
}

import re, time, json
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Command(EnterpriseModule):
    name: str
    description: str
    usage: str
    handler: Callable
    aliases: list[str] = field(default_factory=list)
    category: str = "general"


_commands: dict[str, Command] = {}
_command_history: list[dict] = []


def register(name: str, description: str, usage: str = "",
             aliases: list[str] | None = None,
             category: str = "general"):
    """装饰器方式注册命令"""
    def decorator(func):
        cmd = Command(
            name=name,
            description=description,
            usage=usage or f"/{name}",
            handler=func,
            aliases=aliases or [],
            category=category,
        )
        _commands[name] = cmd
        for alias in (aliases or []):
            _commands[alias] = cmd
        return func
    return decorator


def get_command(name: str) -> Optional[Command]:
    return _commands.get(name.lstrip("/"))


def list_commands(category: str = "") -> list[dict]:
    """列出命令，可选分类过滤"""
    result = []
    seen = set()
    for name, cmd in _commands.items():
        if cmd.name in seen:
            continue
        seen.add(cmd.name)
        if category and cmd.category != category:
            continue
        result.append({
            "name": cmd.name,
            "description": cmd.description,
            "usage": cmd.usage,
            "aliases": cmd.aliases,
            "category": cmd.category,
        })
    return result


def parse(text: str) -> Optional[dict]:
    """解析文本中的斜杠命令"""
    m = re.match(r'^/(\w+)\s*(.*)', text.strip())
    if not m:
        return None
    cmd_name = m.group(1)
    args = m.group(2).strip()
    cmd = get_command(cmd_name)
    if not cmd:
        return {"error": f"未知命令: /{cmd_name}，输入 /help 查看所有命令"}
    return {"command": cmd_name, "args": args, "handler": cmd.handler}


async def execute(text: str, context: dict | None = None) -> dict:
    """执行斜杠命令"""
    start = time.time()
    parsed = parse(text)
    if not parsed:
        return {"success": False, "error": "不是有效的斜杠命令", "type": "not_command"}

    if "error" in parsed:
        return {"success": False, "error": parsed["error"], "type": "unknown"}

    try:
        result = await parsed["handler"](parsed["args"], context or {})
        elapsed = int((time.time() - start) * 1000)
        _command_history.append({
            "command": parsed["command"],
            "args": parsed["args"],
            "time": time.time(),
            "duration_ms": elapsed,
        })
        return {"success": True, "command": parsed["command"], "data": result, "duration_ms": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e), "type": "error"}


def get_history(limit: int = 50) -> list[dict]:
    return _command_history[-limit:]


# ===== 内置命令注册 =====

@register("help", "显示所有可用命令", "/help [命令名]",
          aliases=["h", "?"], category="general")
async def cmd_help(args: str, ctx: dict) -> dict:
    if args:
        cmd = get_command(args)
        if cmd:
            return {
                "type": "help_detail",
                "command": cmd.name,
                "description": cmd.description,
                "usage": cmd.usage,
                "aliases": cmd.aliases,
                "category": cmd.category,
            }
        return {"type": "error", "message": f"未知命令: {args}"}

    cats = {}
    seen = set()
    for name, cmd in _commands.items():
        if cmd.name in seen:
            continue
        seen.add(cmd.name)
        cat = cmd.category
        if cat not in cats:
            cats[cat] = []
        cats[cat].append({"name": cmd.name, "description": cmd.description, "usage": cmd.usage})
    return {"type": "help_list", "categories": cats}


@register("status", "查看系统状态", "/status",
          aliases=["s", "stats"], category="system")
async def cmd_status(args: str, ctx: dict) -> dict:
    import os, psutil
    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "type": "status",
            "cpu": f"{cpu}%",
            "memory": f"{mem.percent}%",
            "memory_used": f"{mem.used / 1024**3:.1f}GB",
            "memory_total": f"{mem.total / 1024**3:.1f}GB",
            "processes": len(psutil.pids()),
        }
    except Exception:
        return {"type": "status", "message": "系统状态获取失败"}


@register("search", "搜索文件或模块", "/search <关键词>",
          aliases=["find", "grep"], category="developer")
async def cmd_search(args: str, ctx: dict) -> dict:
    if not args:
        return {"type": "error", "message": "请提供搜索关键词"}
    from pathlib import Path
    base = Path(__file__).parent.parent
    results = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".html", ".js", ".css", ".md", ".json", ".yaml", ".yml"):
            if args.lower() in p.name.lower():
                try:
                    size = p.stat().st_size
                    results.append({"path": str(p.relative_to(base)), "size": size})
                except Exception:
                    pass
        if len(results) >= 30:
            break
    return {"type": "search_results", "keyword": args, "results": results, "total": len(results)}


@register("context", "查看上下文Token用量", "/context",
          aliases=["ctx", "token"], category="developer")
async def cmd_context(args: str, ctx: dict) -> dict:
    from modules.context_monitor import get_monitor
    mon = get_monitor()
    return {"type": "context_status", "data": mon.get_status()}


@register("clear", "清空当前对话上下文", "/clear",
          aliases=["cls", "reset"], category="developer")
async def cmd_clear(args: str, ctx: dict) -> dict:
    from modules.context_monitor import get_monitor
    mon = get_monitor()
    mon.clear()
    return {"type": "cleared", "message": "上下文已清空"}


@register("compact", "压缩上下文节省Token", "/compact",
          aliases=["compress"], category="developer")
async def cmd_compact(args: str, ctx: dict) -> dict:
    from modules.context_monitor import get_monitor
    mon = get_monitor()
    result = mon.compact()
    return {"type": "compacted", "message": f"上下文已压缩, 释放 {result.get('freed', 0)} tokens", "data": result}


@register("plan", "进入/退出计划模式", "/plan [on|off]",
          aliases=["模式"], category="developer")
async def cmd_plan(args: str, ctx: dict) -> dict:
    from modules.plan_mode import get_planner
    planner = get_planner()
    if args in ("off", "false", "0"):
        planner.deactivate()
        return {"type": "plan_mode", "active": False, "message": "计划模式已关闭，可自由执行"}
    if args in ("on", "true", "1") or not args:
        planner.activate()
        return {"type": "plan_mode", "active": True, "message": "计划模式已开启，先输出方案，审批后执行"}
    return {"type": "error", "message": "用法: /plan [on|off]"}


@register("review", "审查当前代码变更", "/review [working|commit|branch]",
          aliases=["rev", "code-review"], category="developer")
async def cmd_review(args: str, ctx: dict) -> dict:
    from modules.code_review import get_reviewer
    reviewer = get_reviewer()
    target = args or "working"
    if target == "commit":
        r = reviewer.review_commit("HEAD")
    elif target == "branch":
        r = reviewer.review_branch()
    else:
        r = reviewer.review_working_tree()
    return {"type": "review_result", "data": vars(r) if hasattr(r, '__dict__') else r}


# 导出注册表
def get_registry() -> dict:
    return {name: cmd for name, cmd in _commands.items()}


def get_module() -> dict:
    """供模块系统使用的注入点"""
    return {"id": "slash-commands", "commands": list_commands()}
