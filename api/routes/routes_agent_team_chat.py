"""AI同事间讨论 — Agent互相辩论协作（借鉴 Moxt）
多个Agent围绕一个话题展开讨论/辩论，每个Agent从自身角色出发发表意见。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
from api.agent_llm import call_llm
import json, time, uuid

logger = get_logger("evo.api.agent_team_chat")
router = APIRouter()

# 预置角色定义（与 teammates.html 一致）
TEAMMATE_ROLES = {
    "growth": {"name":"📈 增长官","prompt":"你是一个增长专家，专注于数据分析、用户增长和商业化。请从增长角度分析并提供可执行的建议。"},
    "critic": {"name":"🔍 批评家","prompt":"你是一个严格的批评家，专门找出计划中的风险、漏洞和盲点。请用挑剔的眼光审视。"},
    "creative": {"name":"🎨 创意官","prompt":"你是一个天马行空的创意官，负责突破常规思维。请给出最有创意的想法。"},
    "analyst": {"name":"📊 分析师","prompt":"你是一个冷静的数据分析师，基于事实和数据得出结论。请给出客观分析。"},
    "executor": {"name":"⚡ 执行经理","prompt":"你是一个执行力极强的项目经理，关注落地路径和时间节点。请给出可执行的步骤。"},
}

class TeamChatRequest(BaseModel):
    topic: str
    agents: list[str]  # 参与讨论的Agent ID列表
    rounds: int = 2    # 讨论轮数

@router.post("/api/v1/agent-team/discuss")
async def agent_team_discuss(req: TeamChatRequest):
    if not req.agents or len(req.agents) < 2:
        raise HTTPException(400, "至少需要2个Agent参与讨论")
    discussion = []
    for round_num in range(1, req.rounds + 1):
        for agent_id in req.agents:
            role = TEAMMATE_ROLES.get(agent_id, {"name": agent_id, "prompt": "请从你的专业角度分析。"})
            history = "\n".join([f"{d['agent']}: {d['content'][:200]}" for d in discussion[-6:]])
            prompt = f"""{role['prompt']}

讨论主题: {req.topic}

已有讨论:
{history or '（暂无讨论，你是第一个发言的）'}

请从你的角色出发，给出你的观点。保持简洁，200字以内。"""
            try:
                content, _ = call_llm([{"role": "user", "content": prompt}], timeout=20)
                if not content or len(content) < 5:
                    content = f"(Agent {role['name']} 暂无回应)"
            except Exception as e:
                content = f"(Agent {role['name']} 响应异常: {e})"
            discussion.append({"agent": role["name"], "agent_id": agent_id, "content": content[:500], "round": round_num})
    return {"success": True, "topic": req.topic, "rounds": req.rounds, "discussion": discussion}
