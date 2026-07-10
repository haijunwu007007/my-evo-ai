"""示例插件 — Hello World"""
import logging
logger = logging.getLogger("evo.hello")

from api.agent_tools import _tools

def hello_tool(args, **kw):
    name = args.get("name", "World")
    return {"ok": True, "data": f"Hello, {name}! (来自插件)", "tool": "hello"}

def register():
    _tools["hello"] = hello_tool
    logger.info("[plugin] hello tool registered")
