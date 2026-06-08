"""
OpenHands 集成模块
提供全栈项目生成能力：前端+后端+数据库+测试
依赖: pip install openhands
"""

import asyncio
import logging
import subprocess
import tempfile
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# OpenHands 可选依赖
try:
    import openhands
    from openhands.core.config import AppConfig
    from openhands.core.main import run_agent_until_done
    OPENHANDS_AVAILABLE = True
except ImportError:
    OPENHANDS_AVAILABLE = False
    logger.warning("openhands not installed. Run: pip install openhands")


class OpenHandsIntegration:
    """OpenHands 全栈项目生成集成"""

    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Args:
            workspace_dir: 工作目录（用于保存生成的项目）
        """
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="openhands_")
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)

    async def generate_project(
        self,
        description: str,
        project_type: str = "fullstack",
        language: str = "python",
        framework: str = "fastapi"
    ) -> Dict[str, Any]:
        """
        生成完整项目

        Args:
            description: 项目描述，如"一个待办事项管理Web应用"
            project_type: 项目类型 ("fullstack" | "frontend" | "backend" | "api" | "cli")
            language: 主要编程语言 ("python" | "javascript" | "typescript" | "java" | "go")
            framework: 框架 ("fastapi" | "flask" | "django" | "express" | "react" | "vue")

        Returns:
            {
                "success": bool,
                "project_path": str,  # 项目保存路径
                "files_generated": list,  # 生成的文件列表
                "summary": str,  # 项目摘要
            }
        """
        if not OPENHANDS_AVAILABLE:
            return {
                "success": False,
                "error": "openhands not installed. Run: pip install openhands"
            }

        try:
            # 构造任务提示
            task = f"""
            创建一个{project_type}项目：
            描述：{description}
            语言：{language}
            框架：{framework}
            
            要求：
            1. 生成完整的项目结构
            2. 包含前端（如适用）、后端API、数据库模型
            3. 包含单元测试
            4. 包含README.md和部署说明
            5. 代码要生产级质量
            
            将项目保存到：{self.workspace_dir}
            """

            # 运行OpenHands Agent
            config = AppConfig(workspace_base=self.workspace_dir)
            
            # 异步运行Agent
            result = await run_agent_until_done(
                task=task,
                config=config
            )

            # 获取生成的文件列表
            generated_files = []
            for root, dirs, files in os.walk(self.workspace_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.workspace_dir)
                    generated_files.append(rel_path)

            return {
                "success": True,
                "project_path": self.workspace_dir,
                "files_generated": generated_files,
                "file_count": len(generated_files),
                "description": description,
                "project_type": project_type
            }

        except Exception as e:
            logger.error(f"OpenHands project generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_api(
        self,
        api_description: str,
        endpoints: List[str]
    ) -> Dict[str, Any]:
        """
        生成API项目

        Args:
            api_description: API描述
            endpoints: 端点列表，如["/users GET", "/users POST", "/users/{id} PUT"]
        """
        endpoints_str = "\n".join([f"- {ep}" for ep in endpoints])
        description = f"""
        {api_description}
        
        需要实现的端点：
        {endpoints_str}
        """
        return await self.generate_project(
            description=description,
            project_type="api",
            language="python",
            framework="fastapi"
        )

    async def generate_frontend(
        self,
        description: str,
        framework: str = "react"
    ) -> Dict[str, Any]:
        """
        生成前端项目

        Args:
            description: 前端描述
            framework: 前端框架 ("react" | "vue" | "angular" | "svelte")
        """
        return await self.generate_project(
            description=description,
            project_type="frontend",
            language="javascript" if framework in ["react", "vue"] else "typescript",
            framework=framework
        )

    def list_generated_projects(self) -> List[str]:
        """列出所有生成的项目"""
        projects = []
        if os.path.exists(self.workspace_dir):
            for item in os.listdir(self.workspace_dir):
                item_path = os.path.join(self.workspace_dir, item)
                if os.path.isdir(item_path):
                    projects.append(item)
        return projects


# 同步包装器
def generate_project(
    description: str,
    project_type: str = "fullstack",
    language: str = "python"
) -> Dict[str, Any]:
    """同步版本：生成项目"""
    integration = OpenHandsIntegration()
    return asyncio.run(integration.generate_project(description, project_type, language))


def generate_api(api_description: str, endpoints: List[str]) -> Dict[str, Any]:
    """同步版本：生成API"""
    integration = OpenHandsIntegration()
    return asyncio.run(integration.generate_api(api_description, endpoints))


# 工具函数：检查安装状态
def check_openhands_status() -> Dict[str, Any]:
    """检查OpenHands安装状态"""
    status = {
        "available": OPENHANDS_AVAILABLE,
        "install_command": "pip install openhands",
        "python_version_required": "3.12+",
        "capabilities": []
    }

    if OPENHANDS_AVAILABLE:
        status["capabilities"] = [
            "全栈项目生成（前端+后端+数据库）",
            "API服务生成（FastAPI/Flask/Express）",
            "前端应用生成（React/Vue/Angular）",
            "自动化测试生成",
            "代码审查和优化",
            "数据库模型生成",
            "部署脚本生成"
        ]

    return status


if __name__ == "__main__":
    # 测试
    print("OpenHands Integration Module")
    print("=" * 50)
    status = check_openhands_status()
    print(f"Available: {status['available']}")
    if not status['available']:
        print(f"Install: {status['install_command']}")
        print(f"Python version required: {status['python_version_required']}")
    else:
        print("Capabilities:")
        for cap in status['capabilities']:
            print(f"  - {cap}")
