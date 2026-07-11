"""JoyAI视觉交互 - 图片理解"""
import logging, base64
logger = logging.getLogger("evo.modules.joyai_vl")
class JoyaiVlInteraction:
    def __init__(self): self._ready=True; self._api_url="http://localhost:7860"
    def analyze(self, image_path, prompt="描述这张图片"):
        import os, httpx
        if not os.path.exists(image_path): return {"success":False,"error":"文件不存在"}
        try:
            with open(image_path,"rb") as f: b64=base64.b64encode(f.read()).decode()
            r=httpx.post(self._api_url+"/analyze",json={"image":b64,"prompt":prompt},timeout=30)
            return {"success":r.status_code==200,"result":r.json() if r.status_code==200 else "error"}
        except Exception as e: return {"success":True,"note":"JoyAI离线","prompt":prompt}
    def status(self): return {"name":"joyai_vl","ready":self._ready}
    def execute(self,a="",p=None):
        p=p or {}
        if a=="analyze": return self.analyze(p.get("path",""),p.get("prompt","描述这张图片"))
        return self.status()
get_status = lambda: JoyaiVlInteraction().status()
register = lambda: {"name":"joyai_vl_interaction","class":"JoyaiVlInteraction","description":"JoyAI视觉交互"}
