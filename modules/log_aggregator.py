"""日志聚合 — 多源日志收集/搜索"""
import logging, os, sqlite3, time
logger = logging.getLogger('evo.modules.log_aggregator')
_DB=os.path.join(os.path.dirname(__file__),'..','data','logs_agg.db')
class LogAggregator:
    def __init__(self):
        self._ready=True; self._conn=None
    def _db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn=sqlite3.connect(_DB)
            self._conn.execute('CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT,level TEXT,msg TEXT,time REAL)')
        return self._conn
    def ingest(self, source, level, msg):
        self._db().execute('INSERT INTO logs(source,level,msg,time) VALUES(?,?,?,?)',(source,level,str(msg)[:1000],time.time())); self._db().commit()
        return {'success':True}
    def search(self, q='', level='', source='', limit=50):
        db=self._db(); sql='SELECT * FROM logs WHERE 1=1'; p=[]
        if q: sql+=' AND msg LIKE ?'; p.append(f'%{q}%')
        if level: sql+=' AND level=?'; p.append(level)
        if source: sql+=' AND source=?'; p.append(source)
        sql+=' ORDER BY id DESC LIMIT ?'; p.append(limit)
        return [{'id':r[0],'source':r[1],'level':r[2],'msg':r[3][:200],'time':r[4]} for r in db.execute(sql,p).fetchall()]
    def stats(self):
        rows=self._db().execute('SELECT level,COUNT(*) FROM logs GROUP BY level').fetchall()
        return {'total':sum(r[1] for r in rows),'by_level':{r[0]:r[1] for r in rows}}
    def status(self): return {'name':'log_aggregator','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='ingest': return self.ingest(p.get('source',''),p.get('level','info'),p.get('msg',''))
        if a=='search': return {'success':True,'logs':self.search(p.get('query',''),p.get('level',''),p.get('source',''),p.get('limit',50))}
        if a=='stats': return {'success':True,'stats':self.stats()}
        return self.status()
get_status=lambda:LogAggregator().status()
register=lambda:{'name':'log_aggregator','class':'LogAggregator','description':'日志聚合 - 多源收集搜索'}
