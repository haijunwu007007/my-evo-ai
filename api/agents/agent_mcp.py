"""智能体 — MCP协议支持（外部工具桥接）"""
import json, httpx, time
from pathlib import Path

class MCPServer:
    """MCP服务器 — API端点代理（兼容外部调用）"""
    def __init__(self, servers=None):
        self.servers = servers or {}
    
    def list_tools(self):
        return [{"server": s, "tools": []} for s in self.servers]

class MCPClient:
    """轻量MCP客户端——连接外部MCP服务器"""
    def __init__(self, config_path=None):
        self.servers = {}
        if config_path and Path(config_path).exists():
            try:
                cfg = json.loads(Path(config_path).read_text())
                self.servers = cfg.get("mcp_servers", {})
            except Exception:
                pass

    def register_server(self, name, url, api_key=""):
        self.servers[name] = {"url": url, "api_key": api_key}

    def list_tools(self):
        """列出所有外部MCP工具"""
        all_tools = []
        for sname, srv in self.servers.items():
            try:
                r = httpx.get(f"{srv['url'].rstrip('/')}/tools", headers={"Authorization": f"Bearer {srv['api_key']}"} if srv.get("api_key") else {}, timeout=10)
                if r.status_code == 200:
                    tools = r.json().get("tools", [])
                    for t in tools:
                        t["server"] = sname
                    all_tools.extend(tools)
            except Exception:
                pass
        return all_tools

    def call_tool(self, server_name, tool_name, args):
        """调用外部MCP工具"""
        srv = self.servers.get(server_name)
        if not srv: return {"success": False, "error": f"MCP服务器{server_name}未注册"}
        try:
            r = httpx.post(
                f"{srv['url'].rstrip('/')}/call",
                json={"tool": tool_name, "args": args},
                headers={"Authorization": f"Bearer {srv['api_key']}"} if srv.get("api_key") else {},
                timeout=30
            )
            if r.status_code == 200: return {"success": True, "data": r.json()}
            return {"success": False, "error": f"MCP调用失败: {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# 全局实例
mcp_client = MCPClient()
