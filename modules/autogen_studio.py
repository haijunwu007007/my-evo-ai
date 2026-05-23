"""
AUTO-EVO-AI V0.1 — AutoGen Studio 多智能体编排模块
Grade: A (生产级) | Category: AI智能体
职责：管理AutoGen风格的多智能体对话编排、角色定义、消息路由、会话持久化
"""

__module_meta__ = {
    "id": "autogen-studio",
    "name": "Autogen Studio",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "operation", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["autogen", "manager", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — AutoGen Studio 多智能体编排模块 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import logging
import uuid
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger(__name__)

class AgentRole(Enum):
    ASSISTANT = "assistant"
    USER = "user"
    CRITIC = "critic"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    SUMMARIZER = "summarizer"
    COORDINATOR = "coordinator"

class ConversationStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class TerminationCondition(Enum):
    MAX_ROUNDS = "max_rounds"
    USER_APPROVAL = "user_approval"
    KEYWORD = "keyword"
    NO_PROGRESS = "no_progress"
    MANUAL = "manual"

@dataclass
class AgentDefinition:
    """智能体角色定义"""

    agent_id: str
    name: str
    role: AgentRole
    system_prompt: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class ChatMessage:
    """对话消息"""

    msg_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    conversation_id: str = ""
    sender_id: str = ""
    role: str = "assistant"
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0

@dataclass
class Conversation:
    """对话会话"""

    conv_id: str = field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:10]}")
    title: str = ""
    status: ConversationStatus = ConversationStatus.ACTIVE
    agents: List[str] = field(default_factory=list)
    messages: List[ChatMessage] = field(default_factory=list)
    max_rounds: int = 50
    current_round: int = 0
    termination: TerminationCondition = TerminationCondition.MAX_ROUNDS
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentGroup:
    """智能体组（多智能体协作模板）"""

    group_id: str = field(default_factory=lambda: f"grp_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    agent_ids: List[str] = field(default_factory=list)
    routing_strategy: str = "sequential"  # sequential, round_robin, router
    max_rounds: int = 20
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class SkillDefinition:
    """工具/技能定义"""

    skill_id: str = field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    handler: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class AutoGenStudioManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """AutoGen Studio 多智能体编排管理器"""

    def __init__(self):

        super().__init__()
        self.module_name = "autogen_studio"
        self.module_id = self.module_name
        self.module_version = "1.0.0"
        self.module_category = "AI智能体"
        self.module_description = "AutoGen风格的多智能体对话编排与角色管理"

        # 智能体注册表
        self._agents: Dict[str, AgentDefinition] = {}
        # 对话会话存储
        self._conversations: Dict[str, Conversation] = {}
        # 智能体组
        self._groups: Dict[str, AgentGroup] = {}
        # 工具/技能
        self._skills: Dict[str, SkillDefinition] = {}
        # 对话历史索引（用于搜索）
        self._message_index: List[Dict[str, str]] = []

        self._initialized = False

    def initialize(self) -> None:
        """初始化模块，预置默认智能体和技能"""
        if self._initialized:
            return

        _t0 = time.time()
        try:
            pass
            # 注册内置技能
            builtin_skills = [
                SkillDefinition(
                    skill_id="skill_search",
                    name="知识搜索",
                    description="搜索知识库获取相关信息",
                    handler="search_knowledge",
                    parameters={"query": {"type": "str", "required": True}, "top_k": {"type": "int", "default": 5}},
                ),
                SkillDefinition(
                    skill_id="skill_code",
                    name="代码执行",
                    description="执行Python代码片段",
                    handler="execute_code",
                    parameters={"code": {"type": "str", "required": True}, "timeout": {"type": "int", "default": 30}},
                ),
                SkillDefinition(
                    skill_id="skill_web",
                    name="网页浏览",
                    description="获取网页内容",
                    handler="fetch_web",
                    parameters={"url": {"type": "str", "required": True}},
                ),
                SkillDefinition(
                    skill_id="skill_file",
                    name="文件操作",
                    description="读写文件",
                    handler="file_operation",
                    parameters={
                        "path": {"type": "str", "required": True},
                        "action": {"type": "str", "enum": ["read", "write", "list"]},
                        "content": {"type": "str"},
                    },
                ),
            ]
            for s in builtin_skills:
                self._skills[s.skill_id] = s

            # 注册默认智能体
            default_agents = [
                AgentDefinition(
                    agent_id="assistant_default",
                    name="通用助手",
                    role=AgentRole.ASSISTANT,
                    system_prompt="你是一个专业的AI助手，擅长回答问题、分析数据和提供建议。",
                    tools=["skill_search"],
                ),
                AgentDefinition(
                    agent_id="coder_default",
                    name="代码专家",
                    role=AgentRole.CODER,
                    system_prompt="你是一个高级软件工程师，擅长编写高质量代码、架构设计和技术方案。",
                    model="gpt-4",
                    temperature=0.3,
                    tools=["skill_code", "skill_search"],
                ),
                AgentDefinition(
                    agent_id="critic_default",
                    name="评审专家",
                    role=AgentRole.CRITIC,
                    system_prompt="你是一个严格的技术评审专家，负责审查方案和代码质量，指出潜在问题。",
                    model="gpt-4",
                    temperature=0.4,
                ),
                AgentDefinition(
                    agent_id="planner_default",
                    name="规划师",
                    role=AgentRole.PLANNER,
                    system_prompt="你是一个任务规划专家，擅长将复杂任务分解为可执行的子任务步骤。",
                    model="gpt-4",
                    temperature=0.5,
                ),
                AgentDefinition(
                    agent_id="reviewer_default",
                    name="文档审查员",
                    role=AgentRole.REVIEWER,
                    system_prompt="你负责审查和总结讨论内容，确保信息准确完整。",
                    temperature=0.3,
                ),
            ]
            for a in default_agents:
                self._agents[a.agent_id] = a

            metrics_collector.gauge("autogen_studio_agents_total", len(self._agents))
            metrics_collector.gauge("autogen_studio_skills_total", len(self._skills))
        finally:
            elapsed = time.time() - _t0
            metrics_collector.observe("autogen_studio_initialize", elapsed)

        self._initialized = True
        logger.info(f"AutoGen Studio 初始化完成: {len(self._agents)} 智能体, {len(self._skills)} 技能")

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行模块操作"""
        _ = self.trace("execute")
        params = params or {}
        ops = {
            "register_agent": self._op_register_agent,
            "update_agent": self._op_update_agent,
            "list_agents": self._op_list_agents,
            "get_agent": self._op_get_agent,
            "delete_agent": self._op_delete_agent,
            "create_conversation": self._op_create_conversation,
            "send_message": self._op_send_message,
            "get_conversation": self._op_get_conversation,
            "list_conversations": self._op_list_conversations,
            "end_conversation": self._op_end_conversation,
            "create_group": self._op_create_group,
            "run_group_chat": self._op_run_group_chat,
            "list_groups": self._op_list_groups,
            "register_skill": self._op_register_skill,
            "list_skills": self._op_list_skills,
            "search_conversations": self._op_search_conversations,
            "get_stats": self._op_get_stats,
        }

        handler = ops.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}

        try:
            return handler(params)
        except Exception as e:
            logger.error(f"AutoGen Studio 操作失败 [{operation}]: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── 智能体管理 ──

    def _op_register_agent(self, p: Dict) -> Dict:
        agent_id = p.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
        if agent_id in self._agents:
            return {"success": False, "error": f"智能体 {agent_id} 已存在"}
        agent = AgentDefinition(
            agent_id=agent_id,
            name=p.get("name", "未命名智能体"),
            role=AgentRole(p.get("role", "assistant")),
            system_prompt=p.get("system_prompt", "你是一个AI助手。"),
            model=p.get("model", "gpt-4"),
            temperature=p.get("temperature", 0.7),
            max_tokens=p.get("max_tokens", 4096),
            tools=p.get("tools", []),
        )
        self._agents[agent_id] = agent
        metrics_collector.gauge("autogen_studio_agents_total", len(self._agents))
        logger.info(f"注册智能体: {agent_id} ({agent.name})")
        return {"success": True, "result": {"agent_id": agent_id, "name": agent.name, "role": agent.role.value}}

    def _op_update_agent(self, p: Dict) -> Dict:
        aid = p.get("agent_id")
        if not aid or aid not in self._agents:
            return {"success": False, "error": "智能体不存在"}
        a = self._agents[aid]
        for k in ("name", "system_prompt", "model", "temperature", "max_tokens", "tools"):
            if k in p:
                setattr(a, k, p[k])
        if "role" in p:
            a.role = AgentRole(p["role"])
        logger.info(f"更新智能体: {aid}")
        return {"success": True, "result": {"agent_id": aid, "name": a.name}}

    def _op_list_agents(self, p: Dict) -> Dict:
        role_filter = p.get("role")
        result = []
        for a in self._agents.values():
            if role_filter and a.role.value != role_filter:
                continue
            result.append(
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "role": a.role.value,
                    "model": a.model,
                    "tools": a.tools,
                    "created_at": a.created_at,
                }
            )
        return {"success": True, "result": result}

    def _op_get_agent(self, p: Dict) -> Dict:
        aid = p.get("agent_id")
        if not aid or aid not in self._agents:
            return {"success": False, "error": "智能体不存在"}
        a = self._agents[aid]
        return {
            "success": True,
            "result": {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role.value,
                "system_prompt": a.system_prompt,
                "model": a.model,
                "temperature": a.temperature,
                "max_tokens": a.max_tokens,
                "tools": a.tools,
                "created_at": a.created_at,
            },
        }

    def _op_delete_agent(self, p: Dict) -> Dict:
        aid = p.get("agent_id")
        if not aid or aid not in self._agents:
            return {"success": False, "error": "智能体不存在"}
        del self._agents[aid]
        metrics_collector.gauge("autogen_studio_agents_total", len(self._agents))
        return {"success": True, "result": {"deleted": aid}}

    # ── 对话管理 ──

    def _op_create_conversation(self, p: Dict) -> Dict:
        conv = Conversation(
            title=p.get("title", "新对话"),
            agents=p.get("agents", ["assistant_default"]),
            max_rounds=p.get("max_rounds", 50),
            termination=TerminationCondition(p.get("termination", "max_rounds")),
        )
        self._conversations[conv.conv_id] = conv
        # 添加系统消息
        sys_msg = ChatMessage(
            conversation_id=conv.conv_id,
            sender_id="system",
            role="system",
            content=f"对话创建: {conv.title}。参与智能体: {', '.join(conv.agents)}。最大轮次: {conv.max_rounds}。",
        )
        conv.messages.append(sys_msg)
        metrics_collector.record("autogen_studio_conversations_created")
        logger.info(f"创建对话: {conv.conv_id} ({conv.title})")
        return {"success": True, "result": {"conv_id": conv.conv_id, "title": conv.title, "agents": conv.agents}}

    def _op_send_message(self, p: Dict) -> Dict:
        conv_id = p.get("conversation_id")
        if not conv_id or conv_id not in self._conversations:
            return {"success": False, "error": "对话不存在"}
        conv = self._conversations[conv_id]
        if conv.status != ConversationStatus.ACTIVE:
            return {"success": False, "error": f"对话状态为 {conv.status.value}，无法发送消息"}

        sender = p.get("sender_id", conv.agents[0] if conv.agents else "user")
        content = p.get("content", "")
        if not content:
            return {"success": False, "error": "消息内容不能为空"}

        msg = ChatMessage(
            conversation_id=conv_id,
            sender_id=sender,
            role=p.get("role", "assistant" if sender != "user" else "user"),
            content=content,
            metadata=p.get("metadata", {}),
        )
        msg.token_count = len(content) // 2  # 近似token数
        conv.messages.append(msg)
        conv.current_round += 1
        conv.updated_at = datetime.utcnow().isoformat()

        # 索引消息
        self._message_index.append({"conv_id": conv_id, "msg_id": msg.msg_id, "content": content[:200]})

        # 检查终止条件
        terminated = False
        reason = ""
        if conv.current_round >= conv.max_rounds:
            terminated = True
            reason = "达到最大轮次"
        elif conv.termination == TerminationCondition.KEYWORD and p.get("termination_keyword") in content:
            terminated = True
            reason = f"触发终止关键词: {p.get('termination_keyword')}"

        if terminated:
            conv.status = ConversationStatus.COMPLETED
            logger.info(f"对话 {conv_id} 终止: {reason}")

        metrics_collector.record("autogen_studio_messages_sent")
        return {
            "success": True,
            "result": {
                "msg_id": msg.msg_id,
                "round": conv.current_round,
                "tokens": msg.token_count,
                "terminated": terminated,
                "reason": reason,
            },
        }

    def _op_get_conversation(self, p: Dict) -> Dict:
        cid = p.get("conversation_id")
        if not cid or cid not in self._conversations:
            return {"success": False, "error": "对话不存在"}
        c = self._conversations[cid]
        return {
            "success": True,
            "result": {
                "conv_id": c.conv_id,
                "title": c.title,
                "status": c.status.value,
                "agents": c.agents,
                "round": c.current_round,
                "max_rounds": c.max_rounds,
                "messages": [
                    {
                        "msg_id": m.msg_id,
                        "sender": m.sender_id,
                        "role": m.role,
                        "content": m.content[:200],
                        "tokens": m.token_count,
                    }
                    for m in c.messages[-20:]
                ],
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            },
        }

    def _op_list_conversations(self, p: Dict) -> Dict:
        status = p.get("status")
        limit = min(p.get("limit", 50), 200)
        result = []
        for c in sorted(self._conversations.values(), key=lambda x: x.updated_at, reverse=True):
            if status and c.status.value != status:
                continue
            result.append(
                {
                    "conv_id": c.conv_id,
                    "title": c.title,
                    "status": c.status.value,
                    "round": c.current_round,
                    "messages": len(c.messages),
                    "updated_at": c.updated_at,
                }
            )
            if len(result) >= limit:
                break
        return {"success": True, "result": result}

    def _op_end_conversation(self, p: Dict) -> Dict:
        cid = p.get("conversation_id")
        if not cid or cid not in self._conversations:
            return {"success": False, "error": "对话不存在"}
        c = self._conversations[cid]
        c.status = ConversationStatus(p.get("final_status", "completed"))
        c.updated_at = datetime.utcnow().isoformat()
        return {"success": True, "result": {"conv_id": cid, "status": c.status.value}}

    # ── 智能体组管理 ──

    def _op_create_group(self, p: Dict) -> Dict:
        gid = p.get("group_id", f"grp_{uuid.uuid4().hex[:8]}")
        group = AgentGroup(
            group_id=gid,
            name=p.get("name", "未命名组"),
            description=p.get("description", ""),
            agent_ids=p.get("agent_ids", []),
            routing_strategy=p.get("routing_strategy", "sequential"),
            max_rounds=p.get("max_rounds", 20),
        )
        # 验证智能体存在
        for aid in group.agent_ids:
            if aid not in self._agents:
                return {"success": False, "error": f"智能体 {aid} 不存在"}
        self._groups[gid] = group
        logger.info(f"创建智能体组: {gid} ({group.name}), 策略: {group.routing_strategy}")
        return {"success": True, "result": {"group_id": gid, "name": group.name, "agents": group.agent_ids}}

    def _op_run_group_chat(self, p: Dict) -> Dict:
        """模拟运行多智能体群聊"""
        self.audit("execute", f"action={action}")

        gid = p.get("group_id")
        if not gid or gid not in self._groups:
            return {"success": False, "error": "智能体组不存在"}
        group = self._groups[gid]
        initial_msg = p.get("message", "开始讨论")

        # 创建群聊对话
        conv = Conversation(
            title=f"群聊: {group.name}",
            agents=group.agent_ids,
            max_rounds=p.get("rounds", group.max_rounds),
        )
        self._conversations[conv.conv_id] = conv

        # 模拟轮转对话
        agents = group.agent_ids
        strategy = group.routing_strategy
        round_count = 0
        simulated_messages = []

        for rnd in range(min(conv.max_rounds, 5)):  # 限制模拟轮次
            if strategy == "round_robin":
                sender = agents[rnd % len(agents)]
            elif strategy == "sequential":
                sender = agents[0] if rnd == 0 else agents[min(rnd, len(agents) - 1)]
            else:
                sender = agents[rnd % len(agents)]

            agent = self._agents.get(sender)
            agent_name = agent.name if agent else sender
            msg_content = (
                f"[{agent_name}] 第{rnd + 1}轮讨论内容..." if rnd > 0 else f"[{agent_name}] 提出议题: {initial_msg}"
            )

            msg = ChatMessage(
                conversation_id=conv.conv_id,
                sender_id=sender,
                role=agent.role.value if agent else "assistant",
                content=msg_content,
            )
            conv.messages.append(msg)
            simulated_messages.append({"round": rnd + 1, "sender": agent_name, "content_preview": msg_content[:60]})
            round_count = rnd + 1

        conv.current_round = round_count
        conv.updated_at = datetime.utcnow().isoformat()

        metrics_collector.record("autogen_studio_group_chats")
        metrics_collector.histogram("autogen_studio_group_chat_rounds").observe(round_count)
        logger.info(f"群聊完成: {gid}, {round_count} 轮")
        return {
            "success": True,
            "result": {
                "conv_id": conv.conv_id,
                "group": group.name,
                "rounds": round_count,
                "messages": simulated_messages,
            },
        }

    def _op_list_groups(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": [
                {
                    "group_id": g.group_id,
                    "name": g.name,
                    "agents": g.agent_ids,
                    "strategy": g.routing_strategy,
                    "max_rounds": g.max_rounds,
                }
                for g in self._groups.values()
            ],
        }

    # ── 技能管理 ──

    def _op_register_skill(self, p: Dict) -> Dict:
        sid = p.get("skill_id", f"skill_{uuid.uuid4().hex[:8]}")
        if sid in self._skills:
            return {"success": False, "error": f"技能 {sid} 已存在"}
        skill = SkillDefinition(
            skill_id=sid,
            name=p.get("name", ""),
            description=p.get("description", ""),
            handler=p.get("handler", ""),
            parameters=p.get("parameters", {}),
            required_permissions=p.get("required_permissions", []),
        )
        self._skills[sid] = skill
        metrics_collector.gauge("autogen_studio_skills_total", len(self._skills))
        return {"success": True, "result": {"skill_id": sid, "name": skill.name}}

    def _op_list_skills(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "handler": s.handler,
                    "parameters": s.parameters,
                }
                for s in self._skills.values()
            ],
        }

    # ── 搜索与统计 ──

    def _op_search_conversations(self, p: Dict) -> Dict:
        query = p.get("query", "").lower()
        limit = min(p.get("limit", 20), 100)
        if not query:
            return {"success": True, "result": []}
        matches = [m for m in self._message_index if query in m["content"].lower()]
        return {"success": True, "result": matches[:limit], "total": len(matches)}

    def _op_get_stats(self, p: Dict) -> Dict:
        active = sum(1 for c in self._conversations.values() if c.status == ConversationStatus.ACTIVE)
        total_msgs = sum(len(c.messages) for c in self._conversations.values())
        total_tokens = sum(m.token_count for c in self._conversations.values() for m in c.messages)
        return {
            "success": True,
            "result": {
                "agents": len(self._agents),
                "skills": len(self._skills),
                "conversations": len(self._conversations),
                "active": active,
                "groups": len(self._groups),
                "total_messages": total_msgs,
                "total_tokens": total_tokens,
                "message_index_size": len(self._message_index),
            },
        }

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.setdefault("status", "healthy")
        result.update(
            {
                "agents": len(self._agents),
                "skills": len(self._skills),
                "conversations": len(self._conversations),
                "groups": len(self._groups),
                "message_index": len(self._message_index),
            }
        )
        return result

    def shutdown(self) -> None:
        metrics_collector.gauge("autogen_studio_agents_total", len(self._agents))
        logger.info("AutoGen Studio 关闭完成")
        super().shutdown()

module_class = AutoGenStudioManager
