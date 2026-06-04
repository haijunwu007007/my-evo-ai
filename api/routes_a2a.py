"""
AUTO-EVO-AI V0.1 — A2A (Agent-to-Agent) 通信协议 (ContextForge风格)
Agent 之间直接发送消息、协作完成任务、共享上下文
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, uuid, asyncio
from pathlib import Path

logger = get_logger("evo.api.a2a")
router = APIRouter()

# Agent 注册表
_AGENTS: dict = {}  # {agent_id: {"name":..., "capabilities": [...], "status": "idle"|"busy"}}
_AGENT_ROOMS: dict = {}  # {room_id: {"agents": [...], "messages": [...], "task": ...}}

@router.post("/api/v1/a2a/register")
async def register_agent(name: str, capabilities: str = ""):
    """注册一个 Agent 到 A2A 网络"""
    agent_id = name.lower().replace(" ", "-")
    caps = [c.strip() for c in capabilities.split(",") if c.strip()] if capabilities else ["general"]
    _AGENTS[agent_id] = {
        "name": name,
        "capabilities": caps,
        "status": "idle",
        "registered_at": time.time()
    }
    logger.info(f"[A2A] Agent 注册: {name} ({agent_id}) [{', '.join(caps)}]")
    return {"success": True, "agent_id": agent_id, "agent": _AGENTS[agent_id]}


@router.get("/api/v1/a2a/agents")
async def list_agents():
    return {"success": True, "agents": _AGENTS, "total": len(_AGENTS)}


class A2AMessage(BaseModel):
    sender: str
    recipient: str
    content: str
    task: Optional[str] = ""


@router.post("/api/v1/a2a/send")
async def send_message(msg: A2AMessage):
    """Agent A 向 Agent B 发送消息"""
    if msg.sender not in _AGENTS:
        return {"success": False, "detail": f"发送者 {msg.sender} 未注册"}
    if msg.recipient not in _AGENTS:
        return {"success": False, "detail": f"接收者 {msg.recipient} 未注册"}
    
    message_id = str(uuid.uuid4())[:8]
    
    # 如果接收 Agent 正 idle，自动标记 busy
    _AGENTS[msg.recipient]["status"] = "busy"
    
    logger.info(f"[A2A] {msg.sender} → {msg.recipient}: {msg.content[:50]}")
    
    return {
        "success": True,
        "message_id": message_id,
        "from": msg.sender,
        "to": msg.recipient,
        "content": f"消息已投递: {msg.content}"
    }


@router.post("/api/v1/a2a/create-room")
async def create_room(agents: str = "", task: str = ""):
    """创建 Agent 协作房间"""
    room_id = f"room-{uuid.uuid4()[:8]}"
    agent_list = [a.strip() for a in agents.split(",") if a.strip()] if agents else []
    
    # 验证 agent 存在
    valid_agents = [a for a in agent_list if a in _AGENTS]
    if not valid_agents and agent_list:
        valid_agents = agent_list  # 允许注册不存在的 agent（自动注册）
        for a in agent_list:
            if a not in _AGENTS:
                _AGENTS[a] = {"name": a, "capabilities": ["auto"], "status": "idle", "registered_at": time.time()}
    
    # 如果没指定 agent，注册默认团队
    if not valid_agents:
        defaults = {
            "planner": ["规划", "分拆任务"],
            "coder": ["代码生成", "实现"],
            "reviewer": ["代码审查", "质量检查"],
            "operator": ["执行", "部署"],
            "analyst": ["分析", "建议"]
        }
        for a_name, a_caps in defaults.items():
            _AGENTS[a_name] = {"name": a_name, "capabilities": a_caps, "status": "idle", "registered_at": time.time()}
            valid_agents.append(a_name)
    
    _AGENT_ROOMS[room_id] = {
        "agents": valid_agents,
        "messages": [],
        "task": task or "未定义任务",
        "created_at": time.time(),
        "status": "active"
    }
    
    # 标记所有 agent busy
    for a in valid_agents:
        if a in _AGENTS:
            _AGENTS[a]["status"] = "busy"
    
    logger.info(f"[A2A] 房间创建: {room_id} ({len(valid_agents)} agents) task={task[:50]}")
    
    return {
        "success": True,
        "room_id": room_id,
        "agents": valid_agents,
        "task": task or "未定义任务"
    }


@router.post("/api/v1/a2a/room/{room_id}/chat")
async def room_chat(room_id: str, message: str = "", sender: str = ""):
    """在房间里发送消息并获取回复"""
    if room_id not in _AGENT_ROOMS:
        raise HTTPException(status_code=404, detail=f"房间 {room_id} 不存在")
    
    room = _AGENT_ROOMS[room_id]
    agents = room["agents"]
    sender = sender or agents[0]
    
    if sender not in _AGENTS:
        _AGENTS[sender] = {"name": sender, "capabilities": ["user"], "status": "active", "registered_at": time.time()}
    
    # 记录消息
    room["messages"].append({"from": sender, "content": message, "time": time.time()})
    
    # 每个 agent 回复
    responses = []
    for agent in agents:
        if agent == sender:
            continue
        agent_caps = _AGENTS.get(agent, {}).get("capabilities", ["general"])
        response = f"[{agent}] 收到来自 {sender} 的消息。当前任务: {room['task'][:30]}... 我的能力: {', '.join(str(c) for c in agent_caps)}"
        room["messages"].append({"from": agent, "content": response, "time": time.time()})
        responses.append({"agent": agent, "response": response})
    
    return {
        "success": True,
        "room_id": room_id,
        "sender": sender,
        "responses": responses,
        "task": room["task"]
    }


@router.get("/api/v1/a2a/rooms")
async def list_rooms():
    rooms_info = []
    for rid, room in _AGENT_ROOMS.items():
        rooms_info.append({
            "room_id": rid,
            "task": room["task"],
            "agents": room["agents"],
            "message_count": len(room["messages"]),
            "status": room.get("status", "active")
        })
    return {"success": True, "rooms": rooms_info, "total": len(rooms_info)}


@router.get("/api/v1/a2a/room/{room_id}")
async def get_room(room_id: str):
    if room_id not in _AGENT_ROOMS:
        raise HTTPException(status_code=404, detail=f"房间 {room_id} 不存在")
    return {"success": True, "room": _AGENT_ROOMS[room_id]}


def init_default_agents():
    """初始化默认 A2A Agent 团队"""
    default_team = {
        "planner": {"capabilities": ["任务规划", "架构设计", "分拆执行步骤"], "status": "idle"},
        "coder": {"capabilities": ["代码编写", "Python/JS/SQL", "API 开发"], "status": "idle"},
        "reviewer": {"capabilities": ["代码审查", "质量检查", "安全审计"], "status": "idle"},
        "operator": {"capabilities": ["执行命令", "部署", "运维操作"], "status": "idle"},
        "analyst": {"capabilities": ["数据分析", "趋势分析", "建议生成"], "status": "idle"},
        "researcher": {"capabilities": ["信息搜索", "知识查询", "技术调研"], "status": "idle"}
    }
    for a_name, a_info in default_team.items():
        _AGENTS[a_name] = {
            "name": a_name,
            "capabilities": a_info["capabilities"],
            "status": a_info["status"],
            "registered_at": time.time()
        }
    logger.info(f"[A2A] 默认 {len(default_team)} 个 Agent 已注册")

init_default_agents()
