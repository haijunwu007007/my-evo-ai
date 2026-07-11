"""触发器引擎 — 事件触发/注册/执行"""
import logging, json, os, sqlite3, time
logger = logging.getLogger('evo.modules.trigger_engine')
_DB=os.path.join(os.path.dirname(__file__),'..','data','triggers.db')
class TriggerEngine:
    def __init__(self):
        self._ready=True; self._conn=None; self._triggers={}
    def _get_db(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(_DB),exist_ok=True)
            self._conn=sqlite3.connect(_DB)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS triggers(id TEXT PRIMARY KEY, name TEXT, type TEXT, config TEXT, enabled INT DEFAULT 1, created REAL)""")
            rows=self._conn.execute('SELECT id,name,type,config,enabled FROM triggers').fetchall()
            for r in rows:
                self._triggers[r[0]]={'id':r[0],'name':r[1],'type':r[2],'config':json.loads(r[3] or '{}'),'enabled':bool(r[4])}
        return self._conn
    def register(self, name, trigger_type, config=None):
        tid=f'tr_{int(time.time())}'
        cfg=config or {}
        self._triggers[tid]={'id':tid,'name':name,'type':trigger_type,'config':cfg,'enabled':True}
        db=self._get_db()
        db.execute("INSERT OR REPLACE INTO triggers VALUES(?,?,?,?,?,?)",(tid,name,trigger_type,json.dumps(cfg,ensure_ascii=False),1,time.time()))
        db.commit()
        return {'success':True,'trigger':self._triggers[tid],'trigger_count':len(self._triggers)}
    def fire(self, trigger_id, payload=None):
        tr=self._triggers.get(trigger_id)
        if not tr: return {'success':False,'error':'触发器不存在'}
        if not tr['enabled']: return {'success':False,'error':'触发器已禁用'}
        return {'success':True,'trigger':tr['name'],'fired':True,'payload':payload}
    def status(self):
        self._get_db()
        return {'name':'trigger_engine','ready':self._ready,'triggers':len(self._triggers),'enabled':sum(1 for t in self._triggers.values() if t['enabled'])}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='register': return self.register(params.get('name',''),params.get('type',''),params.get('config',{}))
        if action=='fire': return self.fire(params.get('id',''),params.get('payload',{}))
        if action=='list': return {'success':True,'total':len(self._triggers),'triggers':list(self._triggers.values())}
        return self.status()
get_status = lambda: TriggerEngine().status()
register = lambda: {'name':'trigger_engine','class':'TriggerEngine','description':'触发器引擎 - 事件触发/注册/执行'}\nmodule_class = TriggerEngine\n