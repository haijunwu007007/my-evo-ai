"""日志聚合 — 多源日志收集/搜索/分析"""
import logging, json, os, sqlite3, time
logger = logging.getLogger('evo.modules.log_aggregator')
_DB=os.path.join(os.path.dirname(__file__),'..','data','logs_aggregated.db')
class LogAggregator:
    def __init__(self):
        self._ready=True; self._conn=None
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn=sqlite3.connect(_DB)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, level TEXT, msg TEXT, time REAL)""")
        return self._conn
    def ingest(self, source, level, msg):
        db=self._get_db(); db.execute('INSERT INTO logs(source,level,msg,time) VALUES(?,?,?,?)',(source,level,str(msg)[:1000],time.time())); db.commit()
        return {'success':True}
    def search(self, query='', level='', source='', limit=50):
        db=self._get_db(); sql='SELECT * FROM logs WHERE 1=1'; params=[]
        if query: sql+=' AND msg LIKE ?'; params.append(f'%{query}%')
        if level: sql+=' AND level=?'; params.append(level)
        if source: sql+=' AND source=?'; params.append(source)
        sql+=' ORDER BY id DESC LIMIT ?'; params.append(limit)
        rows=db.execute(sql,params).fetchall()
        return [{'id':r[0],'source':r[1],'level':r[2],'msg':r[3][:200],'time':r[4]} for r in rows]
    def stats(self):
        db=self._get_db()
        total=db.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
        levels=db.execute('SELECT level,COUNT(*) FROM logs GROUP BY level').fetchall()
        return {'success':True,'total':total,'by_level':{r[0]:r[1] for r in levels}}
    def status(self): return {'name':'log_aggregator','ready':self._ready}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='ingest': return self.ingest(params.get('source',''),params.get('level','info'),params.get('msg',''))
        if action=='search':
            r=self.search(params.get('query',''),params.get('level',''),params.get('source',''),params.get('limit',50))
            return {'success':True,'total':len(r),'logs':r}
        if action=='stats': return self.stats()
        return self.status()
get_status = lambda: LogAggregator().status()
register = lambda: {'name':'log_aggregator','class':'LogAggregator','description':'日志聚合 - 多源日志收集/搜索'}\nmodule_class = LogAggregator\n