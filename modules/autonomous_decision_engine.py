"""
AUTO-EVO-AI V0.1 — 决策引擎：规则引擎+评分决策
"""
VERSION = "V0.1"
__module_meta__ = {"id": "decision-engine", "name": "DecisionEngine", "version": VERSION, "group": "ai"}

import json, time, re
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class DecisionEngine(PersistMixin, EnterpriseModule):
    MODULE_ID = "decision-engine"; MODULE_NAME = "DecisionEngine"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "decision_engine")
        self._rules = []
    
    def get_status(self): return {"rules": len(self._rules)}
    
    def execute(self, action, **kwargs):
        if action == "add_rule":
            rule = {"condition": kwargs.get("condition",""), "score": kwargs.get("score",0), "label": kwargs.get("label","")}
            self._rules.append(rule)
            self.persist(f"rule:{len(self._rules)}", json.dumps(rule))
            return rule
        if action == "evaluate":
            data = kwargs.get("data", {})
            total = 0
            results = []
            for r in self._rules:
                if r["condition"] in str(data):
                    total += r["score"]
                    results.append(r["label"])
            return {"score": total, "matched": results}
        if action == "list_rules": return self._rules
        return {"error": "unknown: " + str(action)}
