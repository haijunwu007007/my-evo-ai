"""通用研究 — 搜索+分析"""
import logging, json
logger = logging.getLogger('evo.modules.research')
class Research:
    def __init__(self): self._ready=True; self._results=[]
    def search(self, q, count=10):
        from skills.builtin.search_web import execute as _search
        try:
            r=_search({'query':q,'count':count})
            items=r.get('results',[])
            self._results.extend(items)
            return {'success':True,'results':items[:count],'total':len(items)}
        except Exception as e: return {'success':False,'error':str(e)[:100]}
    def status(self): return {'name':'research','ready':self._ready,'results':len(self._results)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='search': return self.search(p.get('q',''),p.get('count',10))
        return self.status()
get_status=lambda:Research().status()
register=lambda:{'name':'research','class':'Research','description':'通用研究搜索'}
