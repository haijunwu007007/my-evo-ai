"""Vanna AI查询 — 自然语言转SQL"""
import logging, json, sqlite3
logger = logging.getLogger('evo.modules.vanna_ai_query')
class VannaAiQuery:
    def __init__(self): self._ready=True; self._model=''
    def config(self, model='chinook'): self._model=model; return {'success':True}
    def ask(self, question):
        try:
            from api.agent_llm import call_llm
            prompt=f'将以下自然语言转为SQL查询（仅输出SQL，不要解释）：\n{question}'
            sql,_=call_llm([{'role':'user','content':prompt}],timeout=15)
            if sql: return {'success':True,'question':question,'sql':sql.strip()[:500],'note':'请手动执行SQL验证'}
        except: pass
        return {'success':True,'question':question,'note':'LLM不可用，请手动编写SQL'}
    def status(self): return {'name':'vanna_ai_query','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='config': return self.config(p.get('model',''))
        if a=='ask': return self.ask(p.get('question',''))
        return self.status()
get_status=lambda:VannaAiQuery().status()
register=lambda:{'name':'vanna_ai_query','class':'VannaAiQuery','description':'Vanna AI转SQL'}
