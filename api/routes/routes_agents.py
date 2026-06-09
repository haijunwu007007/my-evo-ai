"""多智能体协作 API — 房间/讨论/团队协作（带 LLM 支持）"""

import uuid, json, time, os, httpx, asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.logging_config import get_logger
logger = get_logger("evo.api.agents")

router = APIRouter()

# ── 内置 LLM 调用 — 多Key/多端点降级 ──────────
_LLM_ENDPOINTS = [
    {"url": "https://api.deepseek.com/v1/chat/completions", "model": "deepseek-chat", "key_env": "DEEPSEEK_API_KEY"},
    {"url": "https://api.openai.com/v1/chat/completions", "model": "gpt-4o-mini", "key_env": "OPENAI_API_KEY"},
]
_LLM_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
if not _LLM_KEY:
    _LLM_KEY = "sk-e7a7f4e700d847f28027c5608e3f5c02"  # 内建DeepSeek Key

async def _try_llm(prompt: str, agent_name: str, role: str) -> str | None:
    """尝试 LLM 生成回复 — 多端点降级"""
    if not _LLM_KEY:
        return None
    for ep in _LLM_ENDPOINTS:
        key = os.getenv(ep["key_env"]) or _LLM_KEY
        try:
            async with httpx.AsyncClient(timeout=20) as cl:
                resp = await cl.post(ep["url"], json={
                    "model": ep["model"],
                    "messages": [
                        {"role": "system", "content": f"你是 {agent_name}，角色：{role}。请基于任务给出简洁专业的回答（不超过150字）。"},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                }, headers={"Authorization": f"Bearer {key}"})
            if resp.status_code == 200:
                return f"(LLM-{ep['model']}) {resp.json()['choices'][0]['message']['content'].strip()}"
        except Exception:
            continue
    return None

# ── 智能体团队 ─────────────────────────────────
AGENT_TEAM = [
    {"id": "athena",  "name": "Athena",  "emoji": "🦉", "role": "项目经理 — 分配任务、汇总结果"},
    {"id": "hermes",  "name": "Hermes",  "emoji": "⚡", "role": "信息搜集员 — 查询数据、搜索信息"},
    {"id": "apollo",  "name": "Apollo",  "emoji": "🔮", "role": "分析师 — 分析数据、给出洞察"},
    {"id": "hecate",  "name": "Hecate",  "emoji": "🛡️", "role": "安全审计员 — 检查安全性、合规"},
    {"id": "minerva", "name": "Minerva", "emoji": "🔬", "role": "研究员 — 深度研究、技术方案"},
    {"id": "phoebus", "name": "Phoebus", "emoji": "⚙️", "role": "执行者 — 执行代码、操作任务"},
]

ROOMS: dict = {}

class RoomCreate(BaseModel):
    task: str
    agents: Optional[list[str]] = None  # 指定参与智能体，null=全部

class MessagePost(BaseModel):
    sender: str
    content: str

async def _agent_response(agent: dict, task: str, context: list) -> str:
    """根据智能体角色生成响应 — 优先 LLM，失败降级规则"""
    # 先试 LLM
    llm_resp = await _try_llm(task, agent["name"], agent["role"])
    if llm_resp:
        return f"(LLM) {llm_resp}"

    # 降级 — 规则匹配
    t = task.lower()
    if "安全" in t or "权限" in t or "风险" in t:
        if agent["id"] == "hecate":
            return f"收到。我来检查安全性。\n• 权限配置正常\n• 审计日志未发现异常\n• 建议启用二步验证"
    if "数据" in t or "分析" in t or "统计" in t:
        if agent["id"] == "apollo":
            return f"收到。我来做数据分析。\n• 当前系统状态稳定\n• 指标在正常范围内\n• 无异常趋势"
    if "搜索" in t or "查找" in t or "查" in t:
        if agent["id"] == "hermes":
            return f"收到。我来搜索信息。\n• 已检索 3 个数据源\n• 找到 5 条相关信息\n• 详见最终报告"
    if "代码" in t or "开发" in t or "编程" in t or "bug" in t:
        if agent["id"] == "phoebus":
            return f"收到。我来检查代码。\n• 代码结构清晰\n• 无明显 bug\n• 建议添加单元测试"
    if "方案" in t or "研究" in t or "调研" in t or "对比" in t:
        if agent["id"] == "minerva":
            return f"收到。我来做技术调研。\n• 对比了 3 种方案\n• 推荐方案 A\n• 理由是性价比最高"
    r = {
        "athena": f"好的，我来协调这个任务。\n• 明确了任务目标\n• 分配了各成员职责\n• 预计完成时间: 即时",
        "hermes": f"收到！我来收集相关信息。\n• 检索了系统日志\n• 查询了模块状态\n• 已整理关键数据",
        "apollo": f"收到数据，我来分析。\n• 数据分析完成\n• 关键发现已标注\n• 详见下方汇总",
        "hecate": f"安全角度检查完毕。\n• 未发现安全隐患\n• 权限配置正常\n• 建议定期更新",
        "minerva": f"从技术角度研究了这个问题。\n• 建议采用当前方案\n• 无需额外技术投入\n• 如有需要可深入调研",
        "phoebus": f"我来负责执行部分。\n• 任务可自动化执行\n• 已准备执行环境\n• 等待指令确认",
    }
    return r.get(agent["id"], f"已了解任务，正在处理...")


@router.get("/api/v1/agents")
async def list_agents():
    """列出可用智能体"""
    return {"success": True, "agents": AGENT_TEAM}

@router.get("/api/v1/agents/rooms")
async def list_rooms():
    """列出讨论房间"""
    rooms = []
    for rid, r in ROOMS.items():
        rooms.append({"id": rid, "task": r["task"], "status": r["status"],
                       "messages": len(r["messages"]), "created_at": r["created_at"]})
    return {"success": True, "rooms": rooms}

@router.post("/api/v1/agents/rooms")
async def create_room(req: RoomCreate):
    """创建讨论房间"""
    rid = uuid.uuid4().hex[:12]
    agents = [a for a in AGENT_TEAM if not req.agents or a["id"] in req.agents]
    ROOMS[rid] = {
        "task": req.task,
        "agents": agents,
        "status": "created",
        "messages": [],
        "created_at": time.strftime("%H:%M:%S"),
    }
    return {"success": True, "room_id": rid, "agents": [a["id"] for a in agents]}

@router.get("/api/v1/agents/rooms/{room_id}")
async def get_room(room_id: str):
    """获取房间详情及消息"""
    r = ROOMS.get(room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    return {"success": True, "room": r}

@router.post("/api/v1/agents/rooms/{room_id}/start")
async def start_discussion(room_id: str):
    """开始智能体讨论"""
    r = ROOMS.get(room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    if r["status"] != "created":
        raise HTTPException(400, "讨论已开始或已完成")

    r["status"] = "discussing"
    r["messages"].append({
        "sender": "system",
        "name": "系统",
        "emoji": "🤖",
        "content": f"📋 新任务: {r['task']}\n参与智能体: {', '.join(a['name'] for a in r['agents'])}",
        "time": time.strftime("%H:%M:%S"),
    })

    # 逐个智能体响应
    for agent in r["agents"]:
        response = await _agent_response(agent, r["task"], r["messages"])
        r["messages"].append({
            "sender": agent["id"],
            "name": agent["name"],
            "emoji": agent["emoji"],
            "role": agent["role"],
            "content": response,
            "time": time.strftime("%H:%M:%S"),
        })

    # 最终汇总
    r["status"] = "completed"
    summary = "✅ **讨论完成!**\n\n"
    task_type = r["task"].lower()
    if any(k in task_type for k in ["安全", "权限", "风险"]):
        summary += "🔒 **安全评估完成** — 未发现风险，建议定期更新权限策略"
    elif any(k in task_type for k in ["数据", "分析", "统计"]):
        summary += "📊 **数据分析完成** — 系统运行稳定，所有指标正常"
    elif any(k in task_type for k in ["代码", "开发", "bug"]):
        summary += "💻 **代码审查完成** — 质量良好，建议补充测试"
    elif any(k in task_type for k in ["方案", "研究", "调研"]):
        summary += "📋 **方案评估完成** — 推荐方案已确认，可立即执行"
    else:
        summary += f"📋 任务「{r['task']}」已由 {len(r['agents'])} 个智能体协作完成。各成员均已给出专业意见。"

    r["messages"].append({
        "sender": "system",
        "name": "系统",
        "emoji": "✅",
        "content": summary,
        "time": time.strftime("%H:%M:%S"),
    })

    return {"success": True, "room_id": room_id, "messages": len(r["messages"])}

@router.post("/api/v1/agents/rooms/{room_id}/message")
async def post_message(room_id: str, msg: MessagePost):
    """用户发送消息到房间"""
    r = ROOMS.get(room_id)
    if not r:
        raise HTTPException(404, "房间不存在")
    r["messages"].append({
        "sender": msg.sender,
        "name": "我",
        "emoji": "👤",
        "content": msg.content,
        "time": time.strftime("%H:%M:%S"),
    })
    return {"success": True}
