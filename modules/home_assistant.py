"""HomeAssistant集成 — 智能家居"""
import logging
logger = logging.getLogger('evo.modules.home_assistant')
class HomeAssistant:
    def __init__(self): self._ready=True; self._url=''; self._token=''
    def config(self, url, token): self._url=url; self._token=token; return {'success':True}
    def get_state(self, entity):
        if not self._url: return {'success':False,'error':'未配置'}
        try:
            import httpx
            r=httpx.get(f'{self._url}/api/states/{entity}',headers={'Authorization':f'Bearer {self._token}'},timeout=10)
            return {'success':r.status_code==200,'entity':entity,'state':r.json().get('state','') if r.status_code==200 else 'unknown'}
        except Exception as e: return {'success':True,'entity':entity,'state':'offline','note':str(e)[:60]}
    def call(self, domain, service, data=None):
        if not self._url: return {'success':False,'error':'未配置'}
        try:
            import httpx
            r=httpx.post(f'{self._url}/api/services/{domain}/{service}',headers={'Authorization':f'Bearer {self._token}'},json=data or {},timeout=10)
            return {'success':r.status_code==200}
        except Exception as e: return {'success':False,'error':str(e)[:100]}
    def status(self): return {'name':'home_assistant','ready':self._ready,'configured':bool(self._url)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='config': return self.config(p.get('url',''),p.get('token',''))
        if a=='get_state': return self.get_state(p.get('entity',''))
        if a=='call_service': return self.call(p.get('domain',''),p.get('service',''),p.get('data',{}))
        return self.status()
get_status=lambda:HomeAssistant().status()
register=lambda:{'name':'home_assistant','class':'HomeAssistant','description':'HomeAssistant集成'}\nmodule_class = HomeAssistant\n