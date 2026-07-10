"""
Letta (formerly MemGPT) 集成模块
提供操作系统级记忆能力：无限上下文、虚拟内存管理
依赖: pip install letta
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Letta 可选依赖
try:
    import letta
    from letta import create_client, get_config
    LETTA_AVAILABLE = True
except ImportError:
    LETTA_AVAILABLE = False
    logger.warning("letta not installed. Run: pip install letta")


class LettaMemoryIntegration:
    """Letta 操作系统级记忆集成"""

    def __init__(self, agent_name: str = "auto_evo_agent"):
        """
        Args:
            agent_name: Agent名称（用于记忆隔离）
        """
        self.agent_name = agent_name
        self.client = None
        self.agent_id = None

    async def initialize(self) -> Dict[str, Any]:
        """初始化Letta客户端和Agent"""
        if not LETTA_AVAILABLE:
            return {
                "success": False,
                "error": "letta not installed. Run: pip install letta"
            }

        try:
            # 创建客户端
            self.client = create_client()

            # 检查或创建Agent
            agents = self.client.list_agents()
            agent = next((a for a in agents if a.name == self.agent_name), None)

            if not agent:
                # 创建新Agent
                agent = self.client.create_agent(
                    name=self.agent_name,
                    memory_blocks=[
                        {"label": "human", "value": "用户与Auto-EVO-AI系统的交互历史"},
                        {"label": "persona", "value": "Auto-EVO-AI是一个自动化AI系统，能够完成各种任务"}
                    ]
                )

            self.agent_id = agent.id

            return {
                "success": True,
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "message": "Letta记忆系统初始化成功"
            }

        except Exception as e:
            logger.error(f"Letta initialization failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_message(self, message: str) -> Dict[str, Any]:
        """
        发送消息并获取响应（自动管理记忆）

        Args:
            message: 用户消息
        """
        if not self.client or not self.agent_id:
            init_result = await self.initialize()
            if not init_result["success"]:
                return init_result

        try:
            # 发送消息
            response = self.client.send_message(
                agent_id=self.agent_id,
                message=message
            )

            return {
                "success": True,
                "response": response.messages[-1]["content"] if response.messages else "",
                "memory_used": True
            }

        except Exception as e:
            logger.error(f"Letta send message failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_memory(self) -> Dict[str, Any]:
        """获取当前Agent的记忆状态"""
        if not self.client or not self.agent_id:
            return {"success": False, "error": "Agent not initialized"}

        try:
            agent = self.client.get_agent(self.agent_id)
            memory = agent.memory

            return {
                "success": True,
                "human_memory": memory.get("human", ""),
                "persona_memory": memory.get("persona", ""),
                "memory_blocks": list(memory.keys())
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_memory(self, block_label: str, value: str) -> Dict[str, Any]:
        """
        更新记忆块

        Args:
            block_label: 记忆块标签（如"human", "persona"）
            value: 新的记忆内容
        """
        if not self.client or not self.agent_id:
            return {"success": False, "error": "Agent not initialized"}

        try:
            self.client.update_agent_memory(
                agent_id=self.agent_id,
                memory_block=block_label,
                value=value
            )

            return {
                "success": True,
                "message": f"Memory block '{block_label}' updated"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_memories(self) -> Dict[str, Any]:
        """列出所有Agent的记忆"""
        if not LETTA_AVAILABLE:
            return {"success": False, "error": "letta not installed"}

        try:
            self.client = self.client or create_client()
            agents = self.client.list_agents()

            memories = []
            for agent in agents:
                memories.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "created_at": str(agent.created_at) if hasattr(agent, 'created_at') else ""
                })

            return {
                "success": True,
                "agents": memories,
                "count": len(memories)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# 同步包装器
def init_letta(agent_name: str = "auto_evo_agent") -> Dict[str, Any]:
    """同步版本：初始化Letta"""
    integration = LettaMemoryIntegration(agent_name)
    return asyncio.run(integration.initialize())


def send_message_to_letta(message: str, agent_name: str = "auto_evo_agent") -> Dict[str, Any]:
    """同步版本：发送消息"""
    integration = LettaMemoryIntegration(agent_name)
    return asyncio.run(integration.send_message(message))


def get_letta_memory(agent_name: str = "auto_evo_agent") -> Dict[str, Any]:
    """同步版本：获取记忆"""
    integration = LettaMemoryIntegration(agent_name)
    return asyncio.run(integration.get_memory())


# 工具函数：检查安装状态
def check_letta_status() -> Dict[str, Any]:
    """检查Letta安装状态"""
    status = {
        "available": LETTA_AVAILABLE,
        "install_command": "pip install letta",
        "python_version_ok": True,
        "capabilities": []
    }

    if LETTA_AVAILABLE:
        status["capabilities"] = [
            "操作系统级记忆管理",
            "虚拟上下文管理（突破上下文窗口限制）",
            "无限记忆（快慢内存+分页机制）",
            "记忆块管理（human/persona等）",
            "多Agent记忆隔离",
            "持久化记忆存储"
        ]

    return status


if __name__ == "__main__":
    # 测试
    logger.info("Letta (MemGPT) Integration Module")
    logger.info("=" * 50)
    status = check_letta_status()
    logger.info(f"Available: {status['available']}")
    if not status['available']:
        logger.info(f"Install: {status['install_command']}")
    else:
        logger.info("Capabilities:")
        for cap in status['capabilities']:
            logger.info(f"  - {cap}")
