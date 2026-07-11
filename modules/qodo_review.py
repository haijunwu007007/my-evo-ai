"""Qodo代码审查 — AI代码审查"""
import logging, httpx
logger = logging.getLogger('evo.modules.qodo_review')
class QodoReview:
    def __init__(self): self._ready=True; self._key=''
    def config(self, api_key): self._key=api_key; return {'success':True}
    def review(self, code, lang='python'):
        if not self._key: return {'success':False,'error':'未配置'}
        try:
            r=httpx.post('https://api.qodo.ai/v1/review',headers={'Authorization':f'Bearer {self._key}'},json={'language':lang,'code':code[:10000]},timeout=30)
            return {'success':r.status_code==200,'review':r.json() if r.status_code==200 else {}}
        except Exception as e: return {'success':False,'error':str(e)[:100]}
    def status(self): return {'name':'qodo_review','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='config': return self.config(p.get('api_key',''))
        if a=='review': return self.review(p.get('code',''),p.get('lang','python'))
        return self.status()
get_status=lambda:QodoReview().status()
register=lambda:{'name':'qodo_review','class':'QodoReview','description':'Qodo AI代码审查'}
module_class = QodoReview
