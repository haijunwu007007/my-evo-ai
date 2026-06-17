"""Agent核心 — 自动决策引擎"""
import os, json, time
from typing import Optional

BASE = os.path.dirname(os.path.dirname(__file__))

class AgentCore:
    """自主Agent核心: 决策→规划→执行→学习"""

    def __init__(self):
        self.history = []
        self.memory_file = os.path.join(BASE, "data", "agent_memory.json")
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)

    def decide(self, goal: str, context: Optional[dict] = None) -> dict:
        """分析目标→决定执行策略"""
        goal_lower = goal.lower()

        # 多步骤检测
        multi_keywords = ["然后", "并且", "接着", "之后", "同时", "and", "then", "also", "并"]
        is_multi = any(kw in goal for kw in multi_keywords)

        # 工具匹配
        from api.tools.tool_router import route_and_execute
        result = route_and_execute(goal)

        # 记录
        entry = {
            "goal": goal,
            "type": result.get("type", "unknown"),
            "is_multi": is_multi,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "result": result.get("data", "")[:100],
        }
        self.history.append(entry)
        self._save_memory(entry)

        return result

    def _save_memory(self, entry: dict):
        """保存记忆"""
        try:
            mem = []
            if os.path.isfile(self.memory_file):
                with open(self.memory_file, "r") as f:
                    mem = json.load(f)
            mem.append(entry)
            if len(mem) > 100:
                mem = mem[-100:]
            with open(self.memory_file, "w") as f:
                json.dump(mem, f, ensure_ascii=False, indent=2)
        except: pass

    def get_stats(self) -> dict:
        """统计"""
        return {
            "total_tasks": len(self.history),
            "recent": self.history[-5:] if self.history else [],
        }

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = AgentCore()
    return _agent
