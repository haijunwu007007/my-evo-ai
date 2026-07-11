"""访问控制 — 基于角色的IP白名单/黑名单管理"""
import logging, json, os, time
logger = logging.getLogger('evo.modules.access_control')
_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'access_rules.json')
class AccessControl:
    def __init__(self):
        self._ready = True; self._rules = self._load()
    def _load(self):
        try:
            if os.path.exists(_DATA_FILE): return json.loads(open(_DATA_FILE,'r',encoding='utf-8').read())
        except: pass
        return {'whitelist':[],'blacklist':[],'ip_rules':{}}
    def _save(self):
        os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)
        open(_DATA_FILE,'w',encoding='utf-8').write(json.dumps(self._rules, ensure_ascii=False, indent=2))
    def check_access(self, ip, user=''):
        if ip in self._rules['blacklist']: return {'allow':False, 'reason':'IP被拉黑'}
        if self._rules['whitelist'] and ip not in self._rules['whitelist']: return {'allow':False, 'reason':'IP不在白名单'}
        return {'allow':True}
    def add_rule(self, ip, rule_type='whitelist'):
        if rule_type in self._rules:
            if ip not in self._rules[rule_type]: self._rules[rule_type].append(ip); self._save()
            return {'success':True, 'ip':ip, 'type':rule_type}
        return {'success':False, 'error':'规则类型错误'}
    def remove_rule(self, ip, rule_type='whitelist'):
        if rule_type in self._rules and ip in self._rules[rule_type]:
            self._rules[rule_type].remove(ip); self._save()
            return {'success':True}
        return {'success':False, 'error':'规则不存在'}
    def status(self): return {'name':'access_control','ready':self._ready,'whitelist':len(self._rules['whitelist']),'blacklist':len(self._rules['blacklist'])}
    def execute(self, action='', params=None):
        params=params or {}
        if action=='check': return self.check_access(params.get('ip',''),params.get('user',''))
        if action=='add': return self.add_rule(params.get('ip',''),params.get('type','whitelist'))
        if action=='remove': return self.remove_rule(params.get('ip',''),params.get('type','whitelist'))
        return self.status()
module_class = AccessControl
