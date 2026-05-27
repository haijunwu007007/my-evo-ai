"""AUTO-EVO-AI V0.1 — 多Agent协作框架"""
VERSION = "V0.1"
__module_meta__ = {"id": "crewai", "name": "CrewAI", "version": VERSION, "group": "ai"}

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class CrewAIResult(dict):
    def __init__(self, success, data=None, error=None):
        super().__init__(success=success, data=data or {}, error=error or "")

class AgentConfig:
    def __init__(self, role, goal, backstory="", llm="zhipu:glm-4-flash",
                 allow_delegation=False, max_iter=5):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm or "zhipu:glm-4-flash"
        self.allow_delegation = allow_delegation
        self.max_iter = max_iter

class TaskConfig:
    def __init__(self, description, agent_role=None, expected_output="",
                 async_execution=False, context=None):
        self.description = description
        self.agent_role = agent_role
        self.expected_output = expected_output
        self.async_execution = async_execution
        self.context = context or []

class CrewModule(EnterpriseModule):
    MODULE_ID = "crewai"; MODULE_NAME = "CrewAI"

    def __init__(self, config=None):
        super().__init__(config)
        self._crews: dict = {}
        self._agents: dict = {}
        self._tasks: list = []
        self._default_llm = self.config.get("default_llm", "zhipu:glm-4-flash")

    def initialize(self):
        self.status = ModuleStatus.INITIALIZING

    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value, healthy=True,
                            module_id=self.MODULE_ID)

    async def execute(self, action=None, params=None):
        import json as _json, urllib.request as _ur

        p = params or {}
        if action == "create_crew":
            name = p.get("name", "default")
            agents_raw = p.get("agents", [])
            tasks_raw = p.get("tasks", [])
            agents = {a["role"]: AgentConfig(**a) for a in agents_raw}
            tasks = [TaskConfig(**t) for t in tasks_raw]
            self._crews[name] = {"agents": agents, "tasks": tasks}
            for r, a in agents.items(): self._agents[r] = a
            return {"success": True, "crew": name,
                    "agents": len(agents), "tasks": len(tasks)}

        elif action == "run_crew":
            name = p.get("crew", "default")
            crew = self._crews.get(name)
            if not crew:
                return {"success": False, "error": f"crew {name} not found"}
            results = []
            for task in crew["tasks"]:
                agent = crew["agents"].get(task.agent_role)
                if not agent:
                    results.append({"task": task.description[:60],
                                    "error": f"no agent for role {task.agent_role}"})
                    continue
                prompt = f"""你是一个{agent.role}。目标: {agent.goal}
背景: {agent.backstory}
任务描述: {task.description}
请直接输出结果，不要额外解释。"""
                data = _json.dumps({"model": agent.llm,
                                    "messages": [{"role": "user", "content": prompt}],
                                    "max_tokens": 1024}).encode()
                req = _ur.Request("http://127.0.0.1:8765/api/llm/chat",
                                  data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
                try:
                    resp = _ur.urlopen(req, timeout=30)
                    result = _json.loads(resp.read())\
                        .get("choices", [{}])[0].get("message", {})\
                        .get("content", "")
                except Exception as e:
                    result = f"[LLM call failed: {e}]"
                results.append({"task": task.description[:60], "agent": agent.role,
                                "result": result[:500]})
            return {"success": True, "crew": name, "completed": len(results)}

        elif action == "list_crews":
            return {"success": True, "crews": {k: {
                "agents": len(v["agents"]), "tasks": len(v["tasks"])}
                for k, v in self._crews.items()}}

        return {"success": False, "error": f"unknown action: {action}"}

    async def shutdown(self):
        self._crews.clear()
        self.status = ModuleStatus.STOPPED

module_class = CrewModule
