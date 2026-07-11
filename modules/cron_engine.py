"""Cron调度引擎 — 定时任务"""
import logging, time, threading
logger = logging.getLogger('evo.modules.cron_engine')
class CronEngine:
    def __init__(self): self._ready=True; self._tasks={}; self._running=False; self._w=None
    def add(self, name, schedule, cmd):
        tid=f't_{int(time.time())}'
        self._tasks[tid]={'id':tid,'name':name,'schedule':schedule,'command':cmd,'runs':0,'last':0}
        return {'success':True,'task':self._tasks[tid]}
    def list(self): return list(self._tasks.values())
    def delete(self, tid):
        if tid in self._tasks: del self._tasks[tid]; return {'success':True}
        return {'success':False,'error':'不存在'}
    def start(self):
        self._running=True
        def _l():
            while self._running:
                for t in self._tasks.values():
                    if time.time()-t['last']>60: t['runs']+=1; t['last']=time.time()
                time.sleep(30)
        self._w=threading.Thread(target=_l,daemon=True); self._w.start()
        return {'status':'started'}
    def stop(self): self._running=False; return {'status':'stopped'}
    def status(self): return {'name':'cron_engine','ready':self._ready,'tasks':len(self._tasks),'running':self._running}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='add': return self.add(p.get('name',''),p.get('schedule',''),p.get('command',''))
        if a=='list': return {'success':True,'tasks':self.list()}
        if a=='delete': return self.delete(p.get('id',''))
        if a=='start': return self.start()
        if a=='stop': return self.stop()
        return self.status()
get_status=lambda:CronEngine().status()
register=lambda:{'name':'cron_engine','class':'CronEngine','description':'Cron调度引擎'}
