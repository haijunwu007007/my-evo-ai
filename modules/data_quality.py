"""数据质量检查"""
import logging
logger = logging.getLogger('evo.modules.data_quality')
class DataQuality:
    def __init__(self): self._ready=True
    def check_null(self, data, fields):
        if not data: return {'success':False,'error':'无数据'}
        results=[]
        for f in fields:
            nc=sum(1 for row in (data if isinstance(data,list) else [data]) if row.get(f) is None or row.get(f)=='')
            t=len(data) if isinstance(data,list) else 1
            results.append({'field':f,'nulls':nc,'total':t,'rate':round(nc/t*100,1) if t else 0})
        return {'success':True,'checks':results}
    def status(self): return {'name':'data_quality','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='check_null': return self.check_null(p.get('data',[]),p.get('fields',[]))
        return self.status()
get_status=lambda:DataQuality().status()
register=lambda:{'name':'data_quality','class':'DataQuality','description':'数据质量 - 完整性检查'}
