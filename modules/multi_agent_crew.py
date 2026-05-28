"""AUTO-EVO-AI V0.1 — 多Agent编排器"""
VERSION = "V0.1"
__module_meta__ = {"id": "multi-agent-crew", "name": "MultiAgentCrew", "version": VERSION, "group": "ai"}

import asyncio, uuid
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin

class Message:
    def __init__(self, role="user", content="", sender="", receiver=""):
        self.role = role; self.content = content
        self.sender = sender; self.receiver = receiver

class MultiAgentCrew(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID = "multi-agent-crew"; MODULE_NAME = "MultiAgentCrew"

    def __init__(self, config=None):
        super().__init__(config)
        self._agents = {}
        self._messages = []
        self._llm_url = self.config.get("llm_url", "http://127.0.0.1:8765/api/llm/chat")
        self._default_model = self.config.get("default_model", "zhipu:glm-4-flash")

    def initialize(self):
        self.status = ModuleStatus.INITIALIZING

    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value, healthy=True, module_id=self.MODULE_ID)

    async def execute(self, action, params=None):
        import json, urllib.request as ur

        p = params or {}

        if action == "register_agent":
            aid = p.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
            self._agents[aid] = {
                "role": p.get("role", ""),
                "goal": p.get("goal", ""),
                "model": p.get("model", self._default_model),
                "system_prompt": p.get("system_prompt", ""),
            }
            return {"success": True, "agent_id": aid, "role": p.get("role")}

        elif action == "send_message":
            msg = Message(role=p.get("role", "user"), content=p.get("content", ""),
                          sender=p.get("sender", ""), receiver=p.get("receiver", ""))
            self._messages.append(msg)

            # If sender is an agent, respond
            agent = self._agents.get(msg.sender) or self._agents.get(msg.receiver)
            if agent:
                system = agent.get("system_prompt", f"你是一个{agent['role']}。目标: {agent['goal']}")
                data = json.dumps({"model": agent["model"],
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": msg.content}],
                    "max_tokens": 1024}).encode()
                req = ur.Request(self._llm_url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
                try:
                    resp = ur.urlopen(req, timeout=30)
                    reply = json.loads(resp.read()).get("choices",[{}])[0].get("message",{}).get("content","")
                except Exception as e:
                    reply = f"<error: {e}>"
                self._messages.append(Message(role="assistant", content=reply,
                                              sender=agent["role"], receiver=msg.sender))
                return {"success": True, "reply": reply[:500]}
            return {"success": True, "message": "message queued"}

        elif action == "conversation":
            return {"success": True, "messages": [{"role": m.role, "content": m.content[:100],
                                                    "sender": m.sender} for m in self._messages[-20:]]}

        elif action == "list_agents":
            return {"success": True, "agents": list(self._agents.keys())}

        return {"success": False, "error": f"unknown action: {action}"}

    async def shutdown(self):
        self._agents.clear(); self._messages.clear()
        self.status = ModuleStatus.STOPPED

module_class = MultiAgentCrew
