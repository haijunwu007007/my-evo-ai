"""Cron调度引擎 — 定时任务执行器"""
import logging, json, os, time, threading
logger = logging.getLogger('evo.modules.cron_engine')
class CronEngine:
    def __init__(self): self._ready=True; self._tasks={}; self._running=False; self._worker=None
    def add_task(self,name,schedule,command):
        tid=f't_{int(time.time())}'
        self._tasks[tid]={'id':tid,'name':name,'schedule':schedule,'command':command,'created':time.time(),'runs':0,'last_run':0}
        return {'success':True,'task':self._tasks[tid]}
    def list_tasks(self): return list(self._tasks.values())
    def delete_task(self,tid):
        if tid in self._tasks: del self._tasks[tid]; return {'success':True}
        return {'success':False,'error':'任务不存在'}
    def run(self):
        self._running=True
        def _loop():
            while self._running:
                for t in self._tasks.values():
                    if time.time()-t['last_run']>60:
                        t['runs']+=1; t['last_run']=time.time()
                time.sleep(30)
        self._worker=threading.Thread(target=_loop,daemon=True); self._worker.start()
        return {'status':'started'}
    def stop(self): self._running=False; return {'status':'stopped'}
    def status(self): return {'name':'cron_engine','ready':self._ready,'tasks':len(self._tasks),'running':self._running}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='add': return self.add_task(params.get('name',''),params.get('schedule','* * * * *'),params.get('command',''))
        if action=='list': return {'success':True,'total':len(r:=self.list_tasks()),'tasks':r}
        if action=='delete': return self.delete_task(params.get('id',''))
        if action=='start': return self.run()
        if action=='stop': return self.stop()
        return self.status()
get_status = lambda: CronEngine().status()
register = lambda: {'name':'cron_engine','class':'CronEngine','description':'Cron调度引擎 - 定时任务执行器'}\nmodule_class = CronEngine\n