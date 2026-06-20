"""
AUTO-EVO-AI V0.1 — MCP协议桥接：标准化外部工具接口
"""
VERSION = "V0.1"
__module_meta__ = {"id": "mcp-bridge", "name": "MCPBridge", "version": VERSION, "group": "tools"}

import json, subprocess, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class MCPBridge(EnterpriseModule):
    MODULE_ID = "mcp-bridge"; MODULE_NAME = "MCPBridge"
    _tools = {}
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"tools": len(self._tools)}
    
    def execute(self, action, **kwargs):
        if action == "register":
            name = kwargs.get("name", "")
            desc = kwargs.get("description", "")
            cmd = kwargs.get("command", "")
            if not name: return {"error": "name required"}
            self._tools[name] = {"description": desc, "command": cmd}
            return {"registered": name}
        if action == "call":
            tool = kwargs.get("tool", "")
            args = kwargs.get("args", "")
            if tool not in self._tools: return {"error": f"tool {tool} not found"}
            info = self._tools[tool]
            try:
                cmd = info["command"].replace("{args}", str(args))
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                return {"stdout": r.stdout[:2000], "stderr": r.stderr[:200], "code": r.returncode}
            except Exception as e: return {"error": str(e)}
        if action == "list": return {"tools": list(self._tools.keys()), "details": self._tools}
        return {"error": "unknown: " + str(action)}
