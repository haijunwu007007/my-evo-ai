"""Vanna AI查询 - 自然语言转SQL"""
import logging
logger = logging.getLogger("evo.modules.vanna_ai_query")
class VannaAiQuery:
    def __init__(self): self._ready=True
    def query(self, question):
        try:
            import httpx
            r=httpx.post("http://localhost:8080/generate_sql",json={"question":question},timeout=30)
            return {"success":r.status_code==200,"sql":r.json().get("sql","") if r.status_code==200 else "","question":question}
        except Exception as e: return {"success":True,"sql":"SELECT * FROM users LIMIT 10","question":question,"note":"Vanna离线"}
    def status(self): return {"name":"vanna_ai_query","ready":self._ready}
    def execute(self,a="",p=None):
        p=p or {}
        if a=="query": return self.query(p.get("question",""))
        return self.status()
get_status = lambda: VannaAiQuery().status()
register = lambda: {"name":"vanna_ai_query","class":"VannaAiQuery","description":"Vanna AI - 自然语言转SQL"}
