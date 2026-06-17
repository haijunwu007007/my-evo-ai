"""AnySearch + CLI-Anything + WebSocket + ConfigHotReload + RBAC 工具"""
from .registry import tool

# ── AnySearch ──
try:
    from api.hub.anysearch_integration import anysearch_search, anysearch_batch
    @tool("anysearch_search", "搜索", "AnySearch 统一实时搜索")
    def _(args, **kw):
        from api._response import StandardAPIResponse
        q = args.get("query", args.get("q", ""))
        domain = args.get("domain", "general")
        if not q: return StandardAPIResponse(False, "请输入搜索关键词").to_dict()
        r = anysearch_search(q, domain)
        return StandardAPIResponse(r["ok"], r["data"]).to_dict()
    @tool("anysearch_batch", "搜索", "AnySearch 批量并行搜索")
    def _(args, **kw):
        queries = args.get("queries", [])
        if not queries: return {"ok": False, "data": "请输入查询列表"}
        r = anysearch_batch(queries)
        return {"ok": r["ok"], "data": r["data"]}
    print("[plugin] AnySearch tools OK")
except Exception as e:
    print(f"[plugin] AnySearch skipped: {e}")

# ── CLI-Anything ──
try:
    from api.hub.cli_anything_integration import cli_hub_search, cli_hub_install, cli_execute
    @tool("cli_hub_search", "开发工具", "CLI Hub 搜索可用工具")
    def _(args, **kw):
        return cli_hub_search(args.get("query", ""))
    @tool("cli_hub_install", "开发工具", "安装 CLI Hub 工具")
    def _(args, **kw):
        return cli_hub_install(args.get("name", ""))
    @tool("cli_execute", "开发工具", "执行 CLI 命令")
    def _(args, **kw):
        return cli_execute(args.get("command", ""), args.get("cwd"))
    print("[plugin] CLI-Anything tools OK")
except Exception as e:
    print(f"[plugin] CLI-Anything skipped: {e}")

# ── WebSocket ──
_ws_clients = set()
def ws_register(ws):
    _ws_clients.add(ws)
def ws_unregister(ws):
    _ws_clients.discard(ws)
def ws_broadcast(msg):
    import json
    dead = set()
    for ws in _ws_clients:
        try:
            ws.send_text(json.dumps(msg, ensure_ascii=False))
        except:
            dead.add(ws)
    _ws_clients -= dead

@tool("ws_send", "系统", "通过 WebSocket 发送实时消息")
def _(args, **kw):
    import time
    msg = {"type": "tool_result", "data": args.get("message", ""), "time": time.time()}
    ws_broadcast(msg)
    return {"ok": True, "data": "WebSocket 消息已发送"}

# ── 配置热加载 ──
@tool("config_reload", "系统", "热加载配置文件")
def _(args, **kw):
    from api._config_loader import load_config
    cfg = load_config()
    return {"ok": True, "data": f"配置已重载: {len(cfg)} 项"}

# ── RBAC ──
@tool("rbac_check", "系统", "检查当前用户权限")
def _(args, **kw):
    from api._rbac import check_permission
    user = args.get("user", "anonymous")
    action = args.get("action", "read")
    return check_permission(user, action)
