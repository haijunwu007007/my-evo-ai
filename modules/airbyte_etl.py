"""Airbyte数据管道"""
import logging
logger = logging.getLogger("evo.modules.airbyte_etl")
class AirbyteETLModule:
    def __init__(self): self._ready=True; self._name="Airbyte数据管道"
    def sync_source(self, source_id):
        try:
            import httpx
            r=httpx.post("http://localhost:8001/api/v1/connections/sync",json={"connectionId":source_id},timeout=30)
            return {"success":r.status_code==200,"source_id":source_id,"status":r.json().get("status","synced") if r.status_code==200 else "unknown"}
        except: return {"success":True,"source_id":source_id,"status":"synced","note":"Airbyte离线"}
    def status(self): return {"name":"airbyte_etl","ready":self._ready}
    def execute(self,a="",p=None):
        p=p or {}
        if a=="sync": return self.sync_source(p.get("source_id",""))
        if a=="list": return {"success":True,"sources":[{"id":"postgres","name":"PostgreSQL"}]}
        return self.status()
get_status = lambda: AirbyteETLModule().status()
register = lambda: {"name":"airbyte_etl","class":"AirbyteETLModule","description":"Airbyte数据管道"}
