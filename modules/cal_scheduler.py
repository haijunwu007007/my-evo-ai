"""日历调度 — 事件管理"""
import logging, json, os, time, sqlite3
logger = logging.getLogger('evo.modules.cal_scheduler')
_DB = os.path.join(os.path.dirname(__file__),'..','data','calendar.db')
class CalScheduler:
    def __init__(self):
        self._ready = True; self._conn = None
    def _db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn = sqlite3.connect(_DB)
            self._conn.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,desc TEXT,start REAL,end REAL,created REAL)')
        return self._conn
    def add(self, title, desc='', start=0, end=0):
        db=self._db(); now=time.time()
        db.execute('INSERT INTO events(title,desc,start,end,created) VALUES(?,?,?,?,?)',(title,desc,start or now,end or start+3600 or now+3600,now))
        db.commit()
        return {'success':True,'title':title}
    def list(self, days=7):
        db=self._db()
        rows=db.execute('SELECT * FROM events WHERE start<? ORDER BY start LIMIT 50',(time.time()+days*86400,)).fetchall()
        return [{'id':r[0],'title':r[1],'start':r[3]} for r in rows]
    def delete(self, eid):
        self._db().execute('DELETE FROM events WHERE id=?',(eid,)); self._db().commit()
        return {'success':True}
    def status(self): return {'name':'cal_scheduler','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='add': return self.add(p.get('title',''),p.get('desc',''),p.get('start',0),p.get('end',0))
        if a=='list': return {'success':True,'events':self.list(p.get('days',7))}
        if a=='delete': return self.delete(p.get('id',0))
        return self.status()
get_status=lambda:CalScheduler().status()
register=lambda:{'name':'cal_scheduler','class':'CalScheduler','description':'日历调度 - 事件管理'}
