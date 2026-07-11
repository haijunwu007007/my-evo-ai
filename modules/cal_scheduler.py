"""日历调度 — 日历事件管理"""
import logging, json, os, time, sqlite3
logger = logging.getLogger('evo.modules.cal_scheduler')
_DB = os.path.join(os.path.dirname(__file__),'..','data','calendar.db')
class CalScheduler:
    def __init__(self):
        self._ready = True; self._conn = None
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn = sqlite3.connect(_DB)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, desc TEXT, start_time REAL, end_time REAL, all_day INT DEFAULT 0, reminders TEXT, created REAL)""")
        return self._conn
    def add_event(self,title,desc='',start_time=0,end_time=0,all_day=False):
        db=self._get_db(); now=time.time()
        db.execute("INSERT INTO events(title,desc,start_time,end_time,all_day,created) VALUES(?,?,?,?,?,?)",(title,desc,start_time or now,end_time or (start_time+3600) or (now+3600),1 if all_day else 0,now))
        db.commit()
        return {'success':True,'id':db.execute('SELECT last_insert_rowid()').fetchone()[0],'title':title}
    def list_events(self, days=7):
        db=self._get_db(); cutoff=time.time()+days*86400
        rows=db.execute('SELECT * FROM events WHERE start_time<? ORDER BY start_time LIMIT 50',(cutoff,)).fetchall()
        return [{'id':r[0],'title':r[1],'desc':r[2],'start':r[3],'end':r[4],'all_day':bool(r[5])} for r in rows]
    def delete_event(self,event_id):
        db=self._get_db(); db.execute('DELETE FROM events WHERE id=?',(event_id,)); db.commit()
        return {'success':True}
    def status(self): return {'name':'cal_scheduler','ready':self._ready}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='add': return self.add_event(params.get('title',''),params.get('desc',''),params.get('start',0),params.get('end',0),params.get('all_day',False))
        if action=='list':
            r=self.list_events(params.get('days',7))
            return {'success':True,'total':len(r),'events':r}
        if action=='delete': return self.delete_event(params.get('id',0))
        return self.status()
get_status = lambda: CalScheduler().status()
register = lambda: {'name':'cal_scheduler','class':'CalScheduler','description':'日历调度 - 日历事件管理'}\nmodule_class = CalScheduler\n