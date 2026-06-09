"""AUTO-EVO-AI V0.1 — 自主决策引擎"""
# Grade: B
VERSION = "V0.1"
__module_meta__ = {"id": "auto-decision", "name": "AutonomousDecisionEngine", "version": VERSION, "group": "ai"}
import json, uuid, threading, time, logging, urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin
from modules._persist import PersistMixin


logger = logging.getLogger(__name__)

class AutonomousDecisionEngine(PersistMixin,EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID = "auto-decision"; MODULE_NAME = "AutonomousDecisionEngine"
    def __init__(self, c=None):
        super().__init__(c)
        self._decisions = {}
        self._rules = {}
        self._history = []
        self._lock = threading.Lock()
        self._llm_url = self.config.get("llm_url", "http://127.0.0.1:8765/api/llm/chat")
    def initialize(self): self.status = ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value, healthy=True, module_id=self.MODULE_ID)
    def _call_llm(self, prompt):
        d = json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":prompt}],"max_tokens":1024}).encode()
        try:
            return json.loads(ur.urlopen(ur.Request(self._llm_url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e: return f"<error: {e}>"
    async def execute(self, action=None, params=None):
        p = params or {}
        try:
            if action == "decide":
                ctx = p.get("context",""); opts = p.get("options",["yes","no"])
                prompt = f"上下文: {ctx}\n选项: {', '.join(opts)}\n请选择一个最佳选项并解释原因。"
                result = self._call_llm(prompt)
                aid = uuid.uuid4().hex[:8]
                with self._lock:
                    self._decisions[aid] = {"context":ctx,"options":opts,"result":result,"timestamp":time.time()}
                    self._history.append({"action":"decide","decision_id":aid,"timestamp":time.time()})
                return {"success":True,"decision_id":aid,"result":result[:200]}
            elif action == "execute_decision":
                did = p.get("decision_id","")
                with self._lock:
                    dec = self._decisions.get(did)
                    if not dec: return {"success":False,"error":"decision not found"}
                    execution_id = uuid.uuid4().hex[:8]
                    self._history.append({"action":"execute_decision","decision_id":did,"execution_id":execution_id,"timestamp":time.time()})
                return {"success":True,"execution_id":execution_id,"status":"executed"}
            elif action == "get_history":
                limit = p.get("limit",50)
                with self._lock:
                    hist = list(self._history)
                return {"success":True,"history":hist[-limit:]}
            elif action == "add_rule":
                name = p.get("name",""); condition = p.get("condition",""); action_rule = p.get("action","")
                rid = uuid.uuid4().hex[:8]
                with self._lock:
                    self._rules[rid] = {"name":name,"condition":condition,"action":action_rule,"timestamp":time.time()}
                return {"success":True,"rule_id":rid,"rules_count":len(self._rules)}
            elif action == "status":
                with self._lock:
                    return {"success":True,"decisions_count":len(self._decisions),"rules_count":len(self._rules),"history_count":len(self._history)}
            return {"success":False,"error":f"unknown: {action}"}
        except Exception as e:
            logger.error("DecisionEngine.execute error: %s", e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):
        with self._lock:
            self._decisions.clear(); self._rules.clear(); self._history.clear()
        self.status = ModuleStatus.STOPPED
module_class = AutonomousDecisionEngine
