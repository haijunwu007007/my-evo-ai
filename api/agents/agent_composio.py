"""
Composio 集成模块
提供200+工具统一集成：GitHub/Slack/Gmail/Jira等
依赖: pip install composio-langchain
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

# Composio 可选依赖
try:
    from composio import ComposioToolSet, Action, App
    from composio_langchain import ComposioToolSet as LangChainToolSet
    COMPOSIO_AVAILABLE = True
except ImportError:
    COMPOSIO_AVAILABLE = False
    logger.warning("composio not installed. Run: pip install composio-langchain")


class ComposioIntegration:
    """Composio 200+工具统一集成"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Composio API Key（可选，默认从环境变量读取）
        """
        self.api_key = api_key or self._get_api_key()
        self.client = None
        self.toolset = None

    def _get_api_key(self) -> Optional[str]:
        """从环境变量获取API Key"""
        import os
        return os.getenv("COMPOSIO_API_KEY")

    async def initialize(self) -> Dict[str, Any]:
        """初始化Composio客户端"""
        if not COMPOSIO_AVAILABLE:
            return {
                "success": False,
                "error": "composio not installed. Run: pip install composio-langchain"
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "COMPOSIO_API_KEY not set. Get your key from https://app.composio.dev"
            }

        try:
            # 创建客户端
            self.client = ComposioToolSet(api_key=self.api_key)
            self.toolset = LangChainToolSet(api_key=self.api_key)

            return {
                "success": True,
                "message": "Composio客户端初始化成功",
                "api_key_configured": True
            }

        except Exception as e:
            logger.error(f"Composio initialization failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_apps(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        列出所有可用的应用（工具）

        Args:
            category: 应用类别（可选）
                - "productivity": 生产力工具
                - "communication": 通信工具
                - "development": 开发工具
                - "crm": CRM工具
                - "finance": 金融工具
        """
        if not self.client:
            init_result = await self.initialize()
            if not init_result["success"]:
                return init_result

        try:
            # 获取所有应用
            apps = self.client.get_apps()

            # 过滤类别（如果指定）
            if category:
                # 这里需要根据Composio的实际API调整
                apps = [app for app in apps if category.lower() in app.get("categories", [])]

            app_list = []
            for app in apps[:50]:  # 限制返回数量
                app_list.append({
                    "name": app.get("name", ""),
                    "display_name": app.get("display_name", ""),
                    "description": app.get("description", ""),
                    "categories": app.get("categories", []),
                    "actions_count": len(app.get("actions", []))
                })

            return {
                "success": True,
                "apps": app_list,
                "total_count": len(apps),
                "returned_count": len(app_list)
            }

        except Exception as e:
            logger.error(f"List apps failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_actions(self, app_name: str) -> Dict[str, Any]:
        """
        列出指定应用的所有可用操作

        Args:
            app_name: 应用名称（如"github", "slack", "gmail"）
        """
        if not self.client:
            init_result = await self.initialize()
            if not init_result["success"]:
                return init_result

        try:
            actions = self.client.get_actions(app=App(app_name))

            action_list = []
            for action in actions:
                action_list.append({
                    "name": action.name,
                    "description": action.description,
                    "parameters": action.parameters if hasattr(action, 'parameters') else {}
                })

            return {
                "success": True,
                "app_name": app_name,
                "actions": action_list,
                "count": len(action_list)
            }

        except Exception as e:
            logger.error(f"List actions failed: {e}")
            return {"success": False, "error": str(e)}

    async def execute_action(
        self,
        app_name: str,
        action_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行指定应用的指定操作

        Args:
            app_name: 应用名称（如"github"）
            action_name: 操作名称（如"CREATE_ISSUE"）
            params: 操作参数
        """
        if not self.client:
            init_result = await self.initialize()
            if not init_result["success"]:
                return init_result

        try:
            # 执行操作
            result = self.client.execute_action(
                action=Action(action_name),
                app=App(app_name),
                params=params
            )

            return {
                "success": True,
                "app_name": app_name,
                "action_name": action_name,
                "result": result
            }

        except Exception as e:
            logger.error(f"Execute action failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_tools_for_llm(self, apps: List[str]) -> Dict[str, Any]:
        """
        获取指定应用的工具定义（用于LLM调用）

        Args:
            apps: 应用名称列表（如["github", "slack"]）
        """
        if not self.toolset:
            init_result = await self.initialize()
            if not init_result["success"]:
                return init_result

        try:
            # 获取工具定义
            tools = self.toolset.get_tools(apps=apps)

            tool_defs = []
            for tool in tools:
                tool_defs.append({
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": str(tool.args_schema) if hasattr(tool, 'args_schema') else ""
                })

            return {
                "success": True,
                "tools": tool_defs,
                "count": len(tool_defs),
                "apps": apps
            }

        except Exception as e:
            logger.error(f"Get tools failed: {e}")
            return {"success": False, "error": str(e)}


# 同步包装器
def init_composio(api_key: Optional[str] = None) -> Dict[str, Any]:
    """同步版本：初始化Composio"""
    integration = ComposioIntegration(api_key)
    return asyncio.run(integration.initialize())


def list_composio_apps(category: Optional[str] = None) -> Dict[str, Any]:
    """同步版本：列出应用"""
    integration = ComposioIntegration()
    return asyncio.run(integration.list_apps(category))


def execute_composio_action(app_name: str, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """同步版本：执行操作"""
    integration = ComposioIntegration()
    return asyncio.run(integration.execute_action(app_name, action_name, params))


# 工具函数：检查安装状态
def check_composio_status() -> Dict[str, Any]:
    """检查Composio安装状态"""
    status = {
        "available": COMPOSIO_AVAILABLE,
        "install_command": "pip install composio-langchain",
        "api_key_required": True,
        "api_key_url": "https://app.composio.dev",
        "capabilities": []
    }

    if COMPOSIO_AVAILABLE:
        status["capabilities"] = [
            "200+工具统一集成",
            "GitHub操作（Issue/PR/Star等）",
            "Slack消息发送",
            "Gmail邮件操作",
            "Google Drive文件管理",
            "Jira任务管理",
            "Salesforce CRM操作",
            "工具定义自动生成（供LLM调用）",
            "统一认证管理"
        ]

    return status


# 常用应用列表
POPULAR_APPS = [
    "github", "gitlab", "slack", "discord", "telegram",
    "gmail", "google_drive", "google_calendar", "google_sheets",
    "jira", "linear", "notion", "asana", "trello",
    "salesforce", "hubspot", "stripe", "quickbooks",
    "twitter", "linkedin", "facebook", "instagram",
    "youtube", "twitch", "spotify", "netflix",
    "aws", "azure", "gcp", "docker", "kubernetes",
    "mysql", "postgresql", "mongodb", "redis",
    "openai", "anthropic", "huggingface", "stability"
]


if __name__ == "__main__":
    # 测试
    logger.info("Composio Integration Module")
    logger.info("=" * 50)
    status = check_composio_status()
    logger.info(f"Available: {status['available']}")
    if not status['available']:
        logger.info(f"Install: {status['install_command']}")
        logger.info(f"API Key URL: {status['api_key_url']}")
    else:
        logger.info("Capabilities:")
        for cap in status['capabilities']:
            logger.info(f"  - {cap}")
        logger.info(f"\nPopular apps ({len(POPULAR_APPS)}):")
        for app in POPULAR_APPS[:10]:
            logger.info(f"  - {app}")
        logger.info(f"  ... and {len(POPULAR_APPS) - 10} more")
