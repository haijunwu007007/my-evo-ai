"""E2B 代码沙箱执行 — 子进程隔离执行"""
import logging, subprocess, tempfile, os, uuid, json, time
from pathlib import Path
logger = logging.getLogger("e2b_sandbox")
__module_meta__ = {"id":"e2b_sandbox","name":"E2B Sandbox","version":"V0.1","group":"integration","grade":"A"}
class E2BSandbox:
    def __init__(self, config=None):
        self.config=config or {}
        self._sandbox_id=uuid.uuid4().hex[:8]
        self._exec_count=0
    def get_status(self):
        return {"success":True,"sandbox_id":self._sandbox_id,"exec_count":self._exec_count,"runtimes":["python","node","bash"],"timeout":self.config.get("timeout",30)}
    def execute(self, action="status", params=None):
        params=params or {}
        if action=="status": return self.get_status()
        if action=="run":
            code=params.get("code","")
            lang=params.get("lang","python")
            timeout=self.config.get("timeout",30)
            try:
                with tempfile.NamedTemporaryFile(mode="w",suffix=".py" if lang=="python" else ".js",delete=False,encoding="utf-8") as f:
                    f.write(code); tmp=f.name
                t0=time.time()
                r=subprocess.run(["python" if lang=="python" else "node",tmp],capture_output=True,text=True,timeout=timeout)
                Path(tmp).unlink(missing_ok=True)
                return {"success":r.returncode==0,"output":r.stdout,"error":r.stderr,"exit_code":r.returncode,"duration":f"{round(time.time()-t0,2)}s","sandbox_id":self._sandbox_id}
            except subprocess.TimeoutExpired:
                return {"success":False,"error":f"Timeout after {timeout}s","exit_code":-1}
            except Exception as e:
                return {"success":False,"error":str(e)}
        if action=="bash":
            cmd=params.get("command","")
            try:
                r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=self.config.get("timeout",30))
                return {"success":r.returncode==0,"output":r.stdout,"error":r.stderr,"exit_code":r.returncode}
            except Exception as e:
                return {"success":False,"error":str(e)}
        return {"success":False,"error":f"Unknown: {action}"}
module_class=E2BSandbox
