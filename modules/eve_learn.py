from __future__ import annotations

"""

AUTO-EVO-AI V0.1 — EVE Agent 架构学习模块

参考：Vercel Eve (vercel/eve) — filesystem-first durable Agent 框架

Grade: A | Category: 学习中心 | Mode: 学习/实验

"""



import os, json, time, uuid, asyncio, logging

from pathlib import Path

from datetime import datetime

from typing import Any



logger = logging.getLogger("eve_learn")



__module_meta__ = {

    "id": "eve-learn",

    "name": "EVE Agent 架构",

    "version": "V0.1",

    "group": "learning",

    "description": "Vercel Eve 框架学习：filesystem-first 持久化 Agent、沙箱执行、审批流程",

}



# ─── EVE 概念：Filesystem-First Agent ───



class EveAgent:

    """基于 EVE 架构的 Agent — 状态持久化到文件系统"""

    def __init__(self, name: str, workspace: str = ""):

        self.name = name

        self.agent_id = uuid.uuid4().hex[:12]

        self.workspace = Path(workspace) / f"agent_{self.agent_id}" if workspace else Path(f"/tmp/eve_agents/{self.agent_id}")

        self.workspace.mkdir(parents=True, exist_ok=True)

        self.state_file = self.workspace / "state.json"

        self.output_dir = self.workspace / "outputs"

        self.output_dir.mkdir(exist_ok=True)

        self._load_state()



    def _load_state(self):

        if self.state_file.exists():

            with open(self.state_file) as f:

                self.state = json.load(f)

        else:

            self.state = {"created": datetime.now().isoformat(), "steps": [], "status": "idle", "artifacts": []}

            self._save_state()



    def _save_state(self):

        with open(self.state_file, "w") as f:

            json.dump(self.state, f, indent=2, ensure_ascii=False)



    async def step(self, action: str, params: dict = None) -> dict:

        """执行一个 Agent 步骤（EVE 持久化风格）"""

        step_id = uuid.uuid4().hex[:8]

        start = time.time()

        self.state["status"] = "running"

        self._save_state()

        try:

            result = {"step_id": step_id, "action": action, "params": params or {},

                      "status": "completed", "started": datetime.now().isoformat(),

                      "duration": round(time.time() - start, 3)}

            # 模拟执行

            await asyncio.sleep(0.05)

            result["output"] = f"[{self.name}] 执行 {action} 完成"

            self.state["steps"].append(result)

            self.state["artifacts"].append({"step": step_id, "file": f"output_{step_id}.md",

                                            "path": str(self.output_dir / f"output_{step_id}.md")})

            # 写入产出

            (self.output_dir / f"output_{step_id}.md").write_text(f"# {action} 结果\n\n{json.dumps(params, indent=2)}")

            self.state["status"] = "idle"

            self._save_state()

            return {"success": True, **result}

        except Exception as e:

            self.state["status"] = "failed"

            self.state["last_error"] = str(e)

            self._save_state()

            return {"success": False, "error": str(e)}



    async def run_plan(self, plan: list[dict]) -> list[dict]:

        """执行多步骤计划（EVE 的 durable 模式）"""

        results = []

        for step in plan:

            r = await self.step(step.get("action", "unknown"), step.get("params"))

            results.append(r)

            if not r["success"]:

                break

        return results



    def get_trace(self) -> list[dict]:

        """获取全链路追踪（类似 EVE 的 inspect 命令）"""

        return [{"step_id": s["step_id"], "action": s["action"], "status": s["status"],

                 "duration": s.get("duration", 0), "started": s.get("started", "")}

                for s in self.state["steps"]]



    def get_status(self) -> dict:

        return {"agent_id": self.agent_id, "name": self.name, "status": self.state["status"],

                "steps": len(self.state["steps"]), "artifacts": len(self.state["artifacts"]),

                "workspace": str(self.workspace)}



    def cleanup(self):

        import shutil

        shutil.rmtree(str(self.workspace), ignore_errors=True)



# ─── EVE 沙箱学习 ───



class EveSandbox:

    """EVE 风格沙箱 — 安全执行用户代码"""

    def __init__(self):

        self.allowed_modules = {"json", "math", "datetime", "random", "collections", "itertools", "typing"}



    def check_code(self, code: str) -> dict:

        """检查代码安全（类似 EVE sandbox）"""

        issues = []

        for line in code.split("\n"):

            stripped = line.strip()

            if stripped.startswith("import ") or stripped.startswith("from "):

                mod = stripped.split()[1].split(".")[0]

                if mod not in self.allowed_modules:

                    issues.append(f"禁止模块: {mod}")

            if "__import__" in stripped or "exec(" in stripped or "eval(" in stripped:

                issues.append(f"危险调用: {stripped[:30]}")

            if "os." in stripped or "subprocess" in stripped or "shutil" in stripped:

                issues.append(f"系统调用: {stripped[:30]}")

        return {"safe": len(issues) == 0, "issues": issues, "total_lines": len(code.split("\n"))}





# ─── EVE 审批流程学习 ───



class EveApproval:

    """EVE 风格 Human-in-the-loop 审批"""

    def __init__(self):

        self.pending = []



    def create_request(self, agent: str, action: str, reason: str) -> str:

        req_id = uuid.uuid4().hex[:10]

        self.pending.append({"id": req_id, "agent": agent, "action": action, "reason": reason,

                             "status": "pending", "created": datetime.now().isoformat()})

        return req_id



    def approve(self, req_id: str, note: str = "") -> dict:

        for r in self.pending:

            if r["id"] == req_id:

                r["status"] = "approved"

                r["note"] = note

                r["resolved"] = datetime.now().isoformat()

                return {"success": True, "request": r}

        return {"success": False, "error": "未找到审批请求"}



    def reject(self, req_id: str, reason: str = "") -> dict:

        for r in self.pending:

            if r["id"] == req_id:

                r["status"] = "rejected"

                r["rejection"] = reason

                r["resolved"] = datetime.now().isoformat()

                return {"success": True, "request": r}

        return {"success": False, "error": "未找到审批请求"}



    def list_pending(self) -> list[dict]:

        return [r for r in self.pending if r["status"] == "pending"]





# ─── 学习 API ───



_agents: dict[str, EveAgent] = {}

_sandbox = EveSandbox()

_approval = EveApproval()



def get_eve_concept(concept: str = "overview") -> dict:

    """获取 EVE 框架概念解释"""

    concepts = {

        "overview": {

            "title": "EVE — Filesystem-First Durable Agents",

            "author": "Vercel",

            "release": "2026-06-17",

            "description": "EVE 是 Vercel 推出的开源 Agent 框架，核心创新在于将 Agent 状态持久化到文件系统而非内存。"

                          "每个 Agent 对应一个目录，包含 state.json、outputs/、approvals/ 等文件。"

                          "这使得 Agent 任务可以跨进程恢复，支持数小时/数天的长跑任务。",

            "key_features": [

                "Filesystem-First: 所有状态存为文件，重启不丢失",

                "Durable Execution: 任务可中断后从断点恢复",

                "Sandbox: 安全执行用户代码",

                "Human-in-the-Loop: 内置审批流程",

                "Eval: 内置评估系统"

            ]

        },

        "filesystem_agent": {

            "title": "Filesystem-First Agent",

            "detail": "每个 Agent 是一个目录：agent_xxx/ |-- state.json (当前状态) |-- outputs/ (产出物) |-- plans/ (执行计划) |-- trace/ (追踪日志)。"

                      "优势：任意时间可查看 Agent 状态、进程崩溃不丢数据、可与 Git 版本控制集成。"

        },

        "durable_execution": {

            "title": "Durable Execution（持久化执行）",

            "detail": "Agent 的每个步骤都写入文件系统。如果进程在步骤 N 崩溃，重启后从步骤 N 恢复继续执行。"

                      "关键实现：每个 step 生成唯一 ID，结果立即持久化。"

        },

        "approval": {

            "title": "Human-in-the-Loop 审批",

            "detail": "Agent 在执行关键操作前（如发送邮件、修改数据库）可以请求人工审批。"

                      "审批请求写入文件，等待人工批准/拒绝后继续。适用于生产环境的安全控制。"

        },

        "sandbox": {

            "title": "沙箱执行",

            "detail": "EVE 提供了安全的代码执行沙箱，限制访问系统资源、网络和敏感 API。"

                      "支持白名单模块策略，防止 Agent 执行危险操作。"

        }

    }

    if concept in concepts:

        return {"success": True, "data": concepts[concept]}

    return {"success": False, "error": f"未知概念: {concept}"}





def create_agent(name: str) -> dict:

    aid = uuid.uuid4().hex[:12]

    agent = EveAgent(name, f"/tmp/eve_agents")

    _agents[agent.agent_id] = agent

    return {"success": True, "agent_id": agent.agent_id, "name": name,

            "workspace": str(agent.workspace), "message": f"Agent '{name}' 已创建（EVE 风格）"}





def list_agents() -> list[dict]:

    return [a.get_status() for a in _agents.values()]





def delete_agent(agent_id: str) -> dict:

    if agent_id in _agents:

        _agents[agent_id].cleanup()

        del _agents[agent_id]

        return {"success": True, "message": "Agent 已删除"}

    return {"success": False, "error": "未找到"}





def execute_step(agent_id: str, action: str, params: dict = None) -> dict:

    if agent_id not in _agents:

        return {"success": False, "error": "未找到 Agent"}

    import asyncio

    return asyncio.run(_agents[agent_id].step(action, params))





def sandbox_check(code: str) -> dict:

    return _sandbox.check_code(code)





def approval_create(agent: str, action: str, reason: str) -> dict:

    rid = _approval.create_request(agent, action, reason)

    return {"success": True, "request_id": rid, "message": "审批请求已创建"}





def approval_respond(req_id: str, approve: bool, note: str = "") -> dict:

    if approve:

        return _approval.approve(req_id, note)

    return _approval.reject(req_id, note)





module_class = type("EveLearnModule", (), {

    "get_agent": lambda self, aid: _agents.get(aid),

    "get_concept": staticmethod(get_eve_concept),

    "create_agent": staticmethod(create_agent),

    "list_agents": staticmethod(list_agents),

    "delete_agent": staticmethod(delete_agent),

    "execute_step": staticmethod(execute_step),

    "sandbox_check": staticmethod(sandbox_check),

    "approval_create": staticmethod(approval_create),

    "approval_respond": staticmethod(approval_respond),

    "get_version": lambda self: "V0.1",

    "get_info": lambda self: {"success": True, "module": "EVE Learn", "version": "V0.1", "status": "active"},

    "get_status": lambda self: {"success": True, "module": "EVE Learn", "agents": len(_agents), "pending_approvals": len(_approval.pending)},

})

