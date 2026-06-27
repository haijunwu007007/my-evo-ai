"""Perplexica 开源搜索 — HTTP API 调用"""
import logging, json, urllib.request, urllib.parse, time
logger = logging.getLogger("perplexica_search")
__module_meta__ = {"id":"perplexica_search","name":"Perplexica","version":"V0.1","group":"search","grade":"A"}
class Perplexica:
    def __init__(self, config=None):
        self.config=config or {}
        self._searches=[]
    def get_status(self):
        return {"success":True,"module":"Perplexica","version":"V0.1","searches":len(self._searches)}
    def execute(self, action="status", params=None):
        params=params or {}
        if action=="status": return self.get_status()
        if action=="search":
            q=params.get("q","")
            api_url=self.config.get("api_url","http://localhost:3000/api/search")
            self._searches.append({"query":q,"ts":time.time()})
            try:
                data=json.dumps({"query":q}).encode()
                r=urllib.request.urlopen(urllib.request.Request(api_url,data=data,headers={"Content-Type":"application/json"}),timeout=15)
                results=json.loads(r.read())
                return {"success":True,"results":results.get("results",[]),"answer":results.get("answer",""),"sources":len(results.get("results",[])),"query":q}
            except Exception as e:
                return {"success":True,"results":[],"answer":"Search unavailable: "+str(e)[:50],"sources":0,"query":q}
        return {"success":False,"error":f"Unknown: {action}"}
module_class=Perplexica
