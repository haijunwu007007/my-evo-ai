"""审计日志 — 操作记录查询"""
import logging, json, os, time, sqlite3
logger = logging.getLogger('evo.modules.audit_log')
_DB = os.path.join(os.path.dirname(__file__),'..','data','audit.db')
class AuditLog:
    def __init__(self):
        self._ready = True; self._conn = None
    def _db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB), exist_ok=True)
            self._conn = sqlite3.connect(_DB)
            self._conn.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user TEXT,action TEXT,target TEXT,detail TEXT,ip TEXT,time REAL)')
        return self._conn
    def log(self, user='', action='', target='', detail='', ip=''):
        db=self._db()
        db.execute('INSERT INTO audit(user,action,target,detail,ip,time) VALUES(?,?,?,?,?,?)',(user,action,target,str(detail)[:500],ip,time.time()))
        db.commit()
        return {'success':True}
    def query(self, limit=50, user='', action=''):
        db=self._db()
        sql='SELECT * FROM audit WHERE 1=1'; p=[]
        if user: sql+=' AND user=?'; p.append(user)
        if action: sql+=' AND action=?'; p.append(action)
        sql+=' ORDER BY id DESC LIMIT ?'; p.append(limit)
        rows=db.execute(sql,p).fetchall()
        return [{'id':r[0],'user':r[1],'action':r[2],'target':r[3],'time':r[6]} for r in rows]
    def status(self): return {'name':'audit_log','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='log': return self.log(p.get('user',''),p.get('action',''),p.get('target',''),p.get('detail',''),p.get('ip',''))
        if a=='query': return {'success':True,'records':self.query(p.get('limit',50),p.get('user',''),p.get('action',''))}
        return self.status()
get_status=lambda:AuditLog().status()
register=lambda:{'name':'audit_log','class':'AuditLog','description':'审计日志 - 操作记录查询'}
