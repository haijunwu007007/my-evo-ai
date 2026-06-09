"""智能体 — 图状工作流（LangGraph式多分支决策）"""
import json, time, re, asyncio, threading, queue
from pathlib import Path
from api.agent_llm import call_llm
from api.agent_tools import exec_tool

class WorkflowNode:
    def __init__(self, name, action, deps=None, condition=None):
        self.name = name
        self.action = action  # "llm" / "tool" / "condition"
        self.deps = deps or []  # 依赖的节点名
        self.condition = condition  # 条件函数
        self.result = None
        self.status = "pending"  # pending/running/done/failed

class AgentWorkflow:
    def __init__(self, BASE, OUT, TOOLS_DIR, MEM_DB):
        self.BASE = BASE
        self.OUT = OUT
        self.TOOLS_DIR = TOOLS_DIR
        self.MEM_DB = MEM_DB
        self._GENERATED_TOOLS = {}
        self._LAST = {}

    def _exec_tool(self, name, args):
        return exec_tool(name, args, self.BASE, self.OUT, self._LAST, self._GENERATED_TOOLS)

    def run_parallel(self, tasks, msg, key=""):
        """并发执行多个Agent任务"""
        results = {}
        def _run_one(role, prompt):
            msgs = [{"role":"system","content":f"你是{role}。{msg[:50]}"},{"role":"user","content":prompt}]
            r, _ = call_llm(msgs, None, key)
            return role, r or ""
        threads = []
        for role, prompt in tasks:
            t = threading.Thread(target=lambda rp=(role, prompt): results.update({rp[0]: _run_one(rp[0], rp[1])}))
            t.start()
            threads.append(t)
        for t in threads: t.join()
        return results

    def create_plan(self, msg, key=""):
        """LangGraph式：分析→计划→执行→审查"""
        start = time.time()
        plan_prompt = f"任务: {msg[:100]}\n分析需求并制定3步以内执行计划。格式: 步骤1|步骤2|步骤3"
        msgs = [{"role":"system","content":"你是任务规划师"},{"role":"user","content":plan_prompt}]
        plan_r, _ = call_llm(msgs, None, key)
        steps = [s.strip() for s in (plan_r or "").split("|") if s.strip()][:3]
        if not steps: steps = [f"开发{msg[:20]}"]

        # 并发执行（除最后一步审查外）
        exec_tasks = [(f"开发者{i+1}", f"执行: {step}") for i, step in enumerate(steps)]
        results = self.run_parallel(exec_tasks, msg, key)

        # 审查
        all_outputs = "\n".join([f"{role}: {res[:200]}" for role, res in results.values()])
        review_prompt = f"审查以下执行结果是否满足需求：{msg[:50]}\n{all_outputs[:500]}\n回复: 通过/不通过+原因"
        review_msgs = [{"role":"system","content":"代码审查专家"},{"role":"user","content":review_prompt}]
        review_r, _ = call_llm(review_msgs, None, key)

        # 审查不通过→迭代修复
        iteration = 0
        while review_r and "不通过" in review_r[:15] and iteration < 3:
            iteration += 1
            fix_prompt = f"【第{iteration}轮修复】问题: {review_r[:200]}\n请修复并重新生成完整代码"
            fix_msgs = [{"role":"system","content":"代码修复专家"},{"role":"user","content":fix_prompt}]
            fix_r, _ = call_llm(fix_msgs, None, key)
            if fix_r:
                all_outputs = fix_r[:500]
                review_msgs[-1]["content"] = f"审查修复结果是否满足需求：{msg[:50]}\n{fix_r[:500]}"
                review_r, _ = call_llm(review_msgs, None, key)
            else:
                break

        dur = time.time() - start
        return {
            "result": all_outputs[:2000],
            "steps": len(steps),
            "iterations": iteration,
            "duration": f"{dur:.0f}s",
            "mode": "workflow"
        }
