"""
AUTO-EVO-AI V0.1 — 进程看门狗：监控+保活
"""
VERSION = "V0.1"
__module_meta__ = {"id": "watchdog", "name": "ProcessWatchdog", "version": VERSION, "group": "monitor"}

import json, subprocess, time, threading, os, signal
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class ProcessWatchdog(PersistMixin, EnterpriseModule):
    MODULE_ID = "watchdog"; MODULE_NAME = "ProcessWatchdog"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "watchdog")
        self._watches = {}
        self._running = False
    
    def get_status(self): return {"watching": len(self._watches)}
    
    def execute(self, action, **kwargs):
        if action == "watch":
            name = kwargs.get("name", "process")
            cmd = kwargs.get("command", "")
            if not cmd: return {"error": "command required"}
            self._watches[name] = {"cmd": cmd, "pid": None, "alive": False}
            self.persist(f"watch:{name}", json.dumps(self._watches[name]))
            return {"watching": name}
        if action == "check":
            name = kwargs.get("name", "")
            if name: targets = {name: self._watches.get(name, {})}
            else: targets = self._watches
            results = {}
            for n, w in targets.items():
                pid = subprocess.run(["pgrep","-f",w.get("cmd","__none__")], capture_output=True, text=True, timeout=5)
                results[n] = {"alive": pid.returncode == 0, "pid": pid.stdout.strip()}
            return results
        if action == "restart":
            name = kwargs.get("name", "")
            if name not in self._watches: return {"error": f"unknown: {name}"}
            w = self._watches[name]
            try:
                r = subprocess.run(w["cmd"], shell=True, capture_output=True, text=True, timeout=30)
                return {"restarted": name, "status": r.returncode}
            except Exception as e: return {"error": str(e)}
        if action == "list_watches": return list(self._watches.keys())
        return {"error": "unknown: " + str(action)}
