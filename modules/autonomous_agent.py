"""AUTO-EVO-AI V0.1 — 自主Agent"""
VERSION = "V0.1"
__module_meta__ = {"id": "auto-agent", "name": "AutoAgent", "version": VERSION, "group": "ai"}

import json, uuid, urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class AutoAgent(EnterpriseModule):
    MODULE_ID = "auto-agent"; MODULE_NAME = "AutoAgent"

    def __init__(self, config=None):
        super().__init__(config)
        self._agents = {}
        self._llm_url = self.config.get("llm_url", "http://127.0.0.1:8765/api/llm/chat")
        self._default_model = self.config.get("default_model", "zhipu:glm-4-flash")

    def initialize(self): self.status = ModuleStatus.INITIALIZING

    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value, healthy=True, module_id=self.MODULE_ID)

    def _call_llm(self, prompt, model=None):
        data = json.dumps({"model": model or self._default_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048}).encode()
        try:
            resp = ur.urlopen(ur.Request(self._llm_url, data=data,
                headers={"Content-Type": "application/json"}, method="POST"), timeout=30)
            return json.loads(resp.read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:
            return f"[error: {e}]"

    async def execute(self, action=None, params=None):
        p = params or {}
        if action == "create_agent":
            aid = p.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
            self._agents[aid] = {
                "role": p.get("role", "assistant"),
                "goal": p.get("goal", ""),
                "model": p.get("model", self._default_model),
                "max_steps": int(p.get("max_steps", 5)),
                "status": "idle",
                "plan": [], "results": []
            }
            return {"success": True, "agent_id": aid}

        elif action == "run_agent":
            aid = p.get("agent_id", "")
            goal = p.get("goal", "")
            agent = self._agents.get(aid)
            if not agent:
                return {"success": False, "error": f"agent {aid} not found"}
            agent["status"] = "running"
            g = goal or agent["goal"]
            # Step 1: Plan
            plan_prompt = f"你是一个{agent['role']}。目标: {g}\n请列出3-5个具体步骤完成这个目标。"
            plan_text = self._call_llm(plan_prompt, agent["model"])
            agent["plan"].append(plan_text)
            # Step 2-5: Execute
            for i in range(min(agent["max_steps"], 4)):
                exec_prompt = f"你是一个{agent['role']}。目标: {g}\n当前进度第{i+1}步。请输出这一步的成果。"
                result = self._call_llm(exec_prompt, agent["model"])
                agent["results"].append(result)
            agent["status"] = "done"
            return {"success": True, "results": len(agent["results"]),
                    "summary": agent["results"][-1][:200] if agent["results"] else ""}

        elif action == "status":
            aid = p.get("agent_id", "")
            agent = self._agents.get(aid, {})
            return {"success": True, "agent_id": aid, "status": agent.get("status", "not found")}

        elif action == "list":
            return {"success": True, "agents": list(self._agents.keys())}
        return {"success": False, "error": f"unknown action: {action}"}

    async def shutdown(self):
        self._agents.clear(); self.status = ModuleStatus.STOPPED

module_class = AutoAgent
