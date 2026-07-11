"""访问控制 — 基于角色的IP黑白名单管理"""
import logging, json, os
logger = logging.getLogger('evo.modules.access_control')
_DATA = os.path.join(os.path.dirname(__file__),'..','data','access_rules.json')
class AccessControl:
    def __init__(self):
        self._ready = True; self._rules = self._load()
    def _load(self):
        try:
            if os.path.exists(_DATA): return json.loads(open(__DATA,'r',encoding='utf-8').read())
        except: pass
        return {'whitelist':[],'blacklist':[],'ip_rules':{}}
    def _save(self):
        os.makedirs(os.path.dirname(_DATA), exist_ok=True)
        open(_DATA,'w',encoding='utf-8').write(json.dumps(self._rules, ensure_ascii=False, indent=2))
    def check(self, ip):
        if ip in self._rules['blacklist']: return {'allow':False,'reason':'IP被拉黑'}
        if self._rules['whitelist'] and ip not in self._rules['whitelist']: return {'allow':False,'reason':'IP不在白名单'}
        return {'allow':True}
    def add(self, ip, t='whitelist'):
        if t in self._rules and ip not in self._rules[t]: self._rules[t].append(ip); self._save()
        return {'success':True}
    def remove(self, ip, t='whitelist'):
        if t in self._rules and ip in self._rules[t]: self._rules[t].remove(ip); self._save()
        return {'success':True}
    def status(self): return {'name':'access_control','ready':self._ready,'wl':len(self._rules['whitelist']),'bl':len(self._rules['blacklist'])}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='check': return self.check(p.get('ip',''))
        if a=='add': return self.add(p.get('ip',''),p.get('type','whitelist'))
        if a=='remove': return self.remove(p.get('ip',''),p.get('type','whitelist'))
        return self.status()
get_status=lambda:AccessControl().status()
register=lambda:{'name':'access_control','class':'AccessControl','description':'访问控制 - IP黑白名单'}
