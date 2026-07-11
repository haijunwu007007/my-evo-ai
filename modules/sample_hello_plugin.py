"""示例Hello插件 — 插件开发模板"""
import logging
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger('evo.modules.sample_hello_plugin')
class SampleHelloPlugin(EnterpriseModule):
    def __init__(self): self._ready=True; self._name='HelloPlugin'
    def hello(self, name='World'): return {'success':True,'message':f'Hello, {name}! 这是示例插件'}
    def echo(self, text): return {'success':True,'echo':text}
    def status(self): return {'name':'sample_hello_plugin','ready':self._ready,'name':self._name}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='hello': return self.hello(p.get('name','World'))
        if a=='echo': return self.echo(p.get('text',''))
        return self.status()
get_status=lambda:SampleHelloPlugin().status()
register=lambda:{'name':'sample_hello_plugin','class':'SampleHelloPlugin','description':'示例Hello插件'}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "sample_hello_plugin", "ready": getattr(self, "_ready", True),
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

module_class = SampleHelloPlugin
