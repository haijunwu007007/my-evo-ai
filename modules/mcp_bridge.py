"""MCP桥接 - 标准化工具接口"""
import logging, os, sqlite3
logger = logging.getLogger("evo.modules.mcp_bridge")
_DB=os.path.join(os.path.dirname(__file__),"..","data","mcp_bridge.db")
class McpBridge:
    def __init__(self): self._ready=True; self._conn=None
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn=sqlite3.connect(_DB)
            self._conn.execute("CREATE TABLE IF NOT EXISTS servers(name TEXT PRIMARY KEY, url TEXT, tools TEXT, status TEXT)")
        return self._conn
    def register_server(self,name,url):
        db=self._get_db()
        db.execute("INSERT OR REPLACE INTO servers VALUES(?,?,'[]','active')",(name,url))
        db.commit()
        return {"success":True,"server":name}
    def list_servers(self):
        db=self._get_db()
        rows=db.execute("SELECT name,url,status FROM servers").fetchall()
        return [{"name":r[0],"url":r[1],"status":r[2]} for r in rows]
    def status(self): return {"name":"mcp_bridge","ready":self._ready}
    def execute(self,a="",p=None):
        p=p or {}
        if a=="register": return self.register_server(p.get("name",""),p.get("url",""))
        if a=="list": return {"success":True,"servers":self.list_servers()}
        return self.status()
get_status = lambda: McpBridge().status()
register = lambda: {"name":"mcp_bridge","class":"McpBridge","description":"MCP桥接"}
