"""AUTO-EVO-AI V0.1 — 工程团队循环 (GStack)"""
VERSION = "V0.1"
__module_meta__ = {"id": "gstack-team", "name": "GStackTeam", "version": VERSION, "group": "workflow"}
import time, uuid

ROLES = [
    {"role": "CEO", "skills": ["决策", "规划", "优先级"], "status": "idle"},
    {"role": "Designer", "skills": ["UI", "UX", "原型"], "status": "idle"},
    {"role": "Engineer", "skills": ["前端", "后端", "架构"], "status": "idle"},
    {"role": "QA", "skills": ["测试", "自动化", "性能"], "status": "idle"},
    {"role": "Release", "skills": ["部署", "CI/CD", "监控"], "status": "idle"},
]

class GStackTeam:
    def __init__(self):
        self._team = [dict(r) for r in ROLES]
        self._cycles = []
    def init_team(self):
        for m in self._team: m["status"] = "idle"
        return {"success": True, "team": self._team}
    def get_team_status(self):
        return {"success": True, "team": self._team, "total": len(self._team), "active": sum(1 for m in self._team if m["status"]=="busy")}
    def assign_task(self, task_desc=""):
        cid = uuid.uuid4().hex[:8]
        cycle = {"id": cid, "task": task_desc, "status": "started", "started": time.time(), "steps": []}
        for m in self._team:
            m["status"] = "busy"
            step = {"role": m["role"], "status": "completed", "output": f"{m['role']}处理完成: {task_desc[:30]}"}
            cycle["steps"].append(step)
            m["status"] = "idle"
        cycle["status"] = "completed"
        cycle["elapsed"] = round(time.time() - cycle["started"], 3)
        self._cycles.append(cycle)
        return {"success": True, "cycle": cycle}
    def get_cycle_report(self, cid=""):
        if cid:
            for c in self._cycles:
                if c["id"] == cid: return {"success": True, "cycle": c}
            return {"success": False, "error": "未找到"}
        return {"success": True, "cycles": self._cycles[-10:], "total": len(self._cycles)}
    def execute_cycle(self, task=""):
        return self.assign_task(task)

module_class = GStackTeam
