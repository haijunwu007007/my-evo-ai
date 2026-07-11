"""Sentry错误跟踪 — 错误监控"""
import logging, httpx, json
logger = logging.getLogger('evo.modules.sentry_tracker')
class SentryTracker:
    def __init__(self): self._ready=True; self._dsn=''; self._org=''; self._key=''
    def config(self, dsn, org='', key=''): self._dsn=dsn; self._org=org; self._key=key; return {'success':True}
    def list_issues(self, project=''):
        if not self._org or not self._key: return {'success':False,'error':'未配置凭证'}
        try:
            r=httpx.get(f'https://sentry.io/api/0/projects/{self._org}/{project}/issues/',headers={'Authorization':f'Bearer {self._key}'},timeout=10)
            return {'success':r.status_code==200,'issues':r.json()[:20] if r.status_code==200 else []}
        except Exception as e: return {'success':False,'error':str(e)[:100]}
    def status(self): return {'name':'sentry_tracker','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='config': return self.config(p.get('dsn',''),p.get('org',''),p.get('key',''))
        if a=='list_issues': return self.list_issues(p.get('project',''))
        return self.status()
get_status=lambda:SentryTracker().status()
register=lambda:{'name':'sentry_tracker','class':'SentryTracker','description':'Sentry错误跟踪'}
module_class = SentryTracker
