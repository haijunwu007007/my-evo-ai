"""MCP协议桥接 — 标准化外部工具接口"""
import logging, json, os, sqlite3, time
logger = logging.getLogger('evo.modules.mcp_bridge')
_DB=os.path.join(os.path.dirname(__file__),'..','data','mcp_servers.db')
class MCPBridge:
    def __init__(self):
        self._ready=True; self._conn=None
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn=sqlite3.connect(_DB)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS servers(name TEXT PRIMARY KEY, url TEXT, type TEXT, tools TEXT, enabled INT DEFAULT 1, created REAL)""")
        return self._conn
    def register_server(self, name, url, server_type='http'):
        db=self._get_db()
        db.execute("INSERT OR REPLACE INTO servers(name,url,type,tools,enabled,created) VALUES(?,?,?,?,?,?)",(name,url,server_type,'[]',1,time.time()))
        db.commit()
        count=db.execute('SELECT COUNT(*) FROM servers').fetchone()[0]
        return {'success':True,'server':name,'type':server_type,'server_count':count}
    def list_servers(self):
        db=self._get_db()
        rows=db.execute('SELECT name,url,type,enabled FROM servers').fetchall()
        return [{'name':r[0],'url':r[1],'type':r[2],'enabled':bool(r[3])} for r in rows]
    def delete_server(self,name):
        db=self._get_db(); db.execute('DELETE FROM servers WHERE name=?',(name,)); db.commit()
        return {'success':True}
    def status(self): return {'name':'mcp_bridge','ready':self._ready}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='register': return self.register_server(params.get('name',''),params.get('url',''),params.get('type','http'))
        if action=='list': return {'success':True,'total':len(r:=self.list_servers()),'servers':r}
        if action=='delete': return self.delete_server(params.get('name',''))
        return self.status()
get_status = lambda: MCPBridge().status()
register = lambda: {'name':'mcp_bridge','class':'MCPBridge','description':'MCP协议桥接 - 标准化外部工具接口'}
