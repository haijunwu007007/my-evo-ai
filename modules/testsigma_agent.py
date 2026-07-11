"""TestSigma测试Agent — 自动化测试执行"""
import logging, httpx, json
logger = logging.getLogger('evo.modules.testsigma_agent')
class TestsigmaAgent:
    def __init__(self): self._ready=True; self._url=''; self._key=''
    def config(self, url, key): self._url=url.rstrip('/'); self._key=key; return {'success':True}
    def run_test(self, test_id):
        if not self._url: return {'success':False,'error':'未配置'}
        try:
            r=httpx.post(f'{self._url}/api/v1/test_suites/{test_id}/executions',headers={'Authorization':f'Bearer {self._key}'},timeout=60)
            return {'success':r.status_code==200,'execution':r.json() if r.status_code==200 else {}}
        except Exception as e: return {'success':False,'error':str(e)[:100]}
    def status(self): return {'name':'testsigma_agent','ready':self._ready,'configured':bool(self._url)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='config': return self.config(p.get('url',''),p.get('key',''))
        if a=='run_test': return self.run_test(p.get('test_id',''))
        return self.status()
get_status=lambda:TestsigmaAgent().status()
register=lambda:{'name':'testsigma_agent','class':'TestsigmaAgent','description':'TestSigma测试Agent'}\nmodule_class = TestsigmaAgent\n