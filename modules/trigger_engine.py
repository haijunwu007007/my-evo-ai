"""触发器引擎 — 事件触发/规则匹配"""
import logging, time, re
logger = logging.getLogger('evo.modules.trigger_engine')
class TriggerEngine:
    def __init__(self): self._ready=True; self._triggers={}
    def add(self, name, pattern, action):
        tid=f'tr_{int(time.time())}'
        self._triggers[tid]={'id':tid,'name':name,'pattern':pattern,'action':action,'created':time.time(),'fired':0}
        return {'success':True,'trigger':self._triggers[tid]}
    def fire(self, event):
        matched=[]
        for t in self._triggers.values():
            try:
                if re.search(t['pattern'], str(event), re.IGNORECASE):
                    t['fired']+=1
                    matched.append({'trigger':t['name'],'action':t['action']})
            except: pass
        return {'success':True,'matched':matched,'count':len(matched)}
    def list(self): return {'success':True,'triggers':list(self._triggers.values())}
    def status(self): return {'name':'trigger_engine','ready':self._ready,'triggers':len(self._triggers)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='add': return self.add(p.get('name',''),p.get('pattern',''),p.get('action',''))
        if a=='fire': return self.fire(p.get('event',''))
        if a=='list': return self.list()
        return self.status()
get_status=lambda:TriggerEngine().status()
register=lambda:{'name':'trigger_engine','class':'TriggerEngine','description':'触发器引擎'}
