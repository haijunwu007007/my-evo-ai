"""决策树 — 规则引擎/条件判断"""
import logging, json
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger('evo.modules.decision_tree')
class DecisionTree(EnterpriseModule):
    def __init__(self): self._ready=True; self._rules=[]
    def add_rule(self, condition, action, priority=0):
        self._rules.append({'condition':condition,'action':action,'priority':priority})
        self._rules.sort(key=lambda r:-r['priority'])
        return {'success':True,'rule_count':len(self._rules)}
    def evaluate(self, context):
        ctx_str = json.dumps(context,ensure_ascii=False) if isinstance(context,dict) else str(context)
        for r in self._rules:
            cond = r['condition']
            if isinstance(cond,str) and cond in ctx_str:
                return {'matched':True,'action':r['action'],'rule':r}
            if callable(cond):
                try:
                    if cond(context): return {'matched':True,'action':r['action']}
                except: pass
        return {'matched':False,'action':None}
    def status(self): return {'name':'decision_tree','ready':self._ready,'rules':len(self._rules)}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='add_rule': return self.add_rule(params.get('condition',''),params.get('action',''),params.get('priority',0))
        if action=='evaluate': return self.evaluate(params.get('context',{}))
        return self.status()
get_status = lambda: DecisionTree().status()
register = lambda: {'name':'decision_tree','class':'DecisionTree','description':'决策树 - 规则引擎/条件判断'}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "decision_tree", "ready": getattr(self, "_ready", True),
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

module_class = DecisionTree
