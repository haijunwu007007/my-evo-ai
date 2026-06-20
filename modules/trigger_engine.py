"""
AUTO-EVO-AI V0.1 — 触发引擎：条件触发+动作执行
"""
VERSION = "V0.1"
__module_meta__ = {"id": "trigger", "name": "TriggerEngine", "version": VERSION, "group": "automation"}

import json, time, threading, re
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class TriggerEngine(PersistMixin, EnterpriseModule):
    MODULE_ID = "trigger"; MODULE_NAME = "TriggerEngine"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "trigger")
        self._triggers = []
        self._events = []
        self._running = False
    
    def get_status(self): return {"triggers": len(self._triggers), "events": len(self._events)}
    
    def execute(self, action, **kwargs):
        if action == "create":
            tid = f"t{len(self._triggers)+1}"
            trigger = {"id": tid, "condition": kwargs.get("condition",""), "action": kwargs.get("action",""), "params": kwargs.get("params",{}), "active": True}
            self._triggers.append(trigger)
            self.persist(f"trigger:{tid}", json.dumps(trigger))
            return trigger
        if action == "fire":
            event = {"type": kwargs.get("type",""), "data": kwargs.get("data",{}), "ts": time.time()}
            self._events.append(event)
            matched = []
            for t in self._triggers:
                if not t["active"]: continue
                if t["condition"] in str(event) or t["condition"] == "*":
                    matched.append(t)
            return {"event": event, "matched": len(matched), "triggers": [t["id"] for t in matched]}
        if action == "list_triggers": return self._triggers
        if action == "recent_events": return self._events[-20:]
        return {"error": "unknown: " + str(action)}
