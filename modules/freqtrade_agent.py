"""FreqTrade量化交易"""
import logging,subprocess,os,sys
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger=logging.getLogger("evo.modules.freqtrade_agent")
class FreqtradeAgent(EnterpriseModule):
 def __init__(s):s._ready=True;s._dir=""
 def config(s,dir):s._dir=dir;return{"success":True}
 def backtest(s,strategy=""):
  if not s._dir:return{"success":False,"error":"未配置目录"}
  try:r=subprocess.run([sys.executable,"-m","freqtrade","backtesting","--datadir",s._dir,"--strategy",strategy or"SampleStrategy"],capture_output=True,text=True,timeout=300);return{"success":r.returncode==0,"result":r.stdout[-1000:]}
  except Exception as e:return{"success":False,"error":str(e)}
 def status(s):return{"name":"freqtrade_agent","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="config":return s.config(p.get("dir",""))
  if a=="backtest":return s.backtest(p.get("strategy",""))
  return s.status()
get_status=lambda:FreqtradeAgent().status()
register=lambda:{"name":"freqtrade_agent","class":"FreqtradeAgent","description":"FreqTrade量化交易"}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "freqtrade_agent", "ready": getattr(self, "_ready", True),
         "status": self.status.value if hasattr(self, "status") else "running"}

def health_check(self):
 return HealthReport(status=self.status.value if hasattr(self, "status") else "running",
                    healthy=getattr(self, "_ready", True), module_id=self.MODULE_ID)

def initialize(self):
 self.status = ModuleStatus.RUNNING
 return {"success": True}

def shutdown(self):
 self.status = ModuleStatus.STOPPED
 return {"success": True}

module_class = FreqtradeAgent
