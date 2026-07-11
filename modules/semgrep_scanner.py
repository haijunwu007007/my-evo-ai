"""Semgrep扫描 — 静态代码安全扫描"""
import logging, subprocess, json, os
logger = logging.getLogger('evo.modules.semgrep_scanner')
class SemgrepScanner:
    def __init__(self): self._ready=True
    def scan(self, path, config='auto'):
        if not os.path.exists(path): return {'success':False,'error':'路径不存在'}
        try:
            r=subprocess.run(['semgrep','--config',config,'--json',path],capture_output=True,text=True,timeout=120)
            if r.returncode in (0,1):
                data=json.loads(r.stdout) if r.stdout else {}
                return {'success':True,'results':data.get('results',[]),'count':len(data.get('results',[])),'errors':data.get('errors',[])}
            return {'success':False,'error':r.stderr[:200]}
        except Exception as e: return {'success':False,'error':str(e)}
    def status(self): return {'name':'semgrep_scanner','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='scan': return self.scan(p.get('path',''),p.get('config','auto'))
        return self.status()
get_status=lambda:SemgrepScanner().status()
register=lambda:{'name':'semgrep_scanner','class':'SemgrepScanner','description':'Semgrep安全扫描'}
module_class = SemgrepScanner
