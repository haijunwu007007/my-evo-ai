"""审计日志 — 操作记录查询与导出"""
import logging, json, os, time, sqlite3
logger = logging.getLogger('evo.modules.audit_log')
_DB = os.path.join(os.path.dirname(__file__),'..','data','audit.db')
class AuditLog:
    def __init__(self):
        self._ready = True; self._conn = None
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB), exist_ok=True)
            self._conn = sqlite3.connect(_DB)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, target TEXT, detail TEXT, ip TEXT, time REAL)""")
        return self._conn
    def log(self, user='', action='', target='', detail='', ip=''):
        db=self._get_db()
        db.execute("INSERT INTO audit(user,action,target,detail,ip,time) VALUES(?,?,?,?,?,?)",(user,action,target,json.dumps(detail,ensure_ascii=False)[:500] if isinstance(detail,dict) else str(detail)[:500],ip,time.time()))
        db.commit()
        return {'success':True,'id':db.execute('SELECT last_insert_rowid()').fetchone()[0]}
    def query(self, limit=50, user='', action=''):
        db=self._get_db()
        sql='SELECT * FROM audit WHERE 1=1'; params=[]
        if user: sql+=' AND user=?'; params.append(user)
        if action: sql+=' AND action=?'; params.append(action)
        sql+=' ORDER BY id DESC LIMIT ?'; params.append(limit)
        rows=db.execute(sql,params).fetchall()
        return [{'id':r[0],'user':r[1],'action':r[2],'target':r[3],'detail':r[4],'ip':r[5],'time':r[6]} for r in rows]
    def status(self): return {'name':'audit_log','ready':self._ready}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='log': return self.log(params.get('user',''),params.get('action',''),params.get('target',''),params.get('detail',''),params.get('ip',''))
        if action=='query':
            r=self.query(params.get('limit',50),params.get('user',''),params.get('action',''))
            return {'success':True,'total':len(r),'records':r}
        return self.status()
get_status = lambda: AuditLog().status()
register = lambda: {'name':'audit_log','class':'AuditLog','description':'审计日志 - 操作记录查询与导出'}
