"""内容人性化 — AI文本润色"""
import logging
logger = logging.getLogger('evo.modules.humanizer')
class Humanizer:
    def __init__(self): self._ready=True
    def humanize(self, text, style='natural'):
        if not text: return {'success':False,'error':'输入为空'}
        try:
            from api.agent_llm import call_llm
            content,_=call_llm([{'role':'user','content':f'请将以下内容改写成自然人性化风格({style})，保持原意：\n\n{text[:3000]}'}],timeout=15)
            if content and len(content)>10: return {'success':True,'result':content[:2000]}
        except: pass
        return {'success':True,'result':text[:2000],'note':'LLM不可用，返回原文'}
    def status(self): return {'name':'humanizer','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='humanize': return self.humanize(p.get('text',''),p.get('style','natural'))
        return self.status()
get_status=lambda:Humanizer().status()
register=lambda:{'name':'humanizer','class':'Humanizer','description':'内容人性化 - AI文本润色'}
