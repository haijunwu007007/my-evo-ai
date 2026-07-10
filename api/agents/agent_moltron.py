"""
Moltron 集成模块
通过Skills.md自动进化能力树
参考: https://github.com/moltron/moltron
"""

import os
import re
import logging
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MoltronIntegration:
    """
    Moltron Skills自动进化集成
    
    能力：
    1. 读取Skills.md文件
    2. 解析技能树
    3. 自动学习新技能
    4. 更新技能树
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    async def parse_skills_md(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        解析Skills.md文件

        Args:
            file_path: Skills.md文件路径（可选，默认搜索常见位置）

        Returns:
            {
                "success": bool,
                "skills": [
                    {
                        "name": str,
                        "description": str,
                        "category": str,
                        "dependencies": list,
                        "mastered": bool
                    }
                ],
                "categories": list
            }
        """
        # 搜索Skills.md文件
        if not file_path:
            possible_paths = [
                self.skills_dir / "Skills.md",
                Path("Skills.md"),
                Path("skills.md"),
                Path("SKILLS.md")
            ]
            for path in possible_paths:
                if path.exists():
                    file_path = str(path)
                    break

        if not file_path:
            return {
                "success": False,
                "error": "Skills.md not found. Create one at skills/Skills.md"
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            skills = []
            categories = set()

            # 解析Markdown格式
            # 格式示例：
            # ## 类别1
            # - [x] 技能1: 描述
            # - [ ] 技能2: 描述

            current_category = "Uncategorized"

            for line in content.split("\n"):
                # 检测类别标题
                category_match = re.match(r"^##+\s+(.+)$", line)
                if category_match:
                    current_category = category_match.group(1).strip()
                    categories.add(current_category)
                    continue

                # 检测技能项
                skill_match = re.match(r"^\s*-\s+\[(.)\]\s+(.+?):\s*(.+)$", line)
                if skill_match:
                    mastered_marker = skill_match.group(1)
                    skill_name = skill_match.group(2).strip()
                    skill_desc = skill_match.group(3).strip()

                    skills.append({
                        "name": skill_name,
                        "description": skill_desc,
                        "category": current_category,
                        "mastered": mastered_marker.lower() == "x",
                        "dependencies": []
                    })

            return {
                "success": True,
                "skills": skills,
                "categories": list(categories),
                "total_skills": len(skills),
                "mastered_count": sum(1 for s in skills if s["mastered"]),
                "file_path": file_path
            }

        except Exception as e:
            logger.error(f"Parse Skills.md failed: {e}")
            return {"success": False, "error": str(e)}

    async def learn_skill(
        self,
        skill_name: str,
        skill_description: str,
        category: str = "Auto-learned"
    ) -> Dict[str, Any]:
        """
        学习新技能（添加到Skills.md）

        Args:
            skill_name: 技能名称
            skill_description: 技能描述
            category: 技能类别
        """
        try:
            skills_md_path = self.skills_dir / "Skills.md"

            # 如果文件不存在，创建初始结构
            if not skills_md_path.exists():
                content = f"""# Skills

## {category}

"""
                skills_md_path.write_text(content, encoding="utf-8")

            # 读取现有内容
            with open(skills_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查技能是否已存在
            if skill_name in content:
                return {
                    "success": False,
                    "error": f"Skill '{skill_name}' already exists"
                }

            # 添加新技能
            new_skill_line = f"- [ ] {skill_name}: {skill_description}\n"

            # 检查类别是否存在
            category_header = f"## {category}"
            if category_header in content:
                # 在类别下添加技能
                content = content.replace(
                    category_header,
                    category_header + "\n" + new_skill_line.strip()
                )
            else:
                # 创建新类别并添加技能
                content += f"\n## {category}\n\n{new_skill_line}"

            # 写回文件
            with open(skills_md_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Skill '{skill_name}' added to {skills_md_path}",
                "skill_name": skill_name,
                "category": category
            }

        except Exception as e:
            logger.error(f"Learn skill failed: {e}")
            return {"success": False, "error": str(e)}

    async def master_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        标记技能为已掌握

        Args:
            skill_name: 技能名称
        """
        try:
            skills_md_path = self.skills_dir / "Skills.md"
            if not skills_md_path.exists():
                return {"success": False, "error": "Skills.md not found"}

            with open(skills_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找并替换技能行
            pattern = rf"(\s*-\s+\[)\s*(\]\s+{re.escape(skill_name)}:)"
            replacement = r"\1x\2"

            new_content = re.sub(pattern, replacement, content)

            if new_content == content:
                return {
                    "success": False,
                    "error": f"Skill '{skill_name}' not found in Skills.md"
                }

            # 写回文件
            with open(skills_md_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "message": f"Skill '{skill_name}' marked as mastered"
            }

        except Exception as e:
            logger.error(f"Master skill failed: {e}")
            return {"success": False, "error": str(e)}

    async def suggest_new_skills(self, context: str = "") -> Dict[str, Any]:
        """
        建议学习新技能

        Args:
            context: 上下文（可选，用于更精准的建议）
        """
        # 这里可以调用LLM生成建议
        # 简化版本：返回预定义建议
        suggestions = [
            {
                "name": "Browser Automation",
                "description": "使用Browser-Use自动化浏览器操作",
                "category": "Automation"
            },
            {
                "name": "Research Report Generation",
                "description": "使用GPT-Researcher生成研究报告",
                "category": "Research"
            },
            {
                "name": "Full-stack Project Generation",
                "description": "使用OpenHands生成全栈项目",
                "category": "Development"
            },
            {
                "name": "Memory Management",
                "description": "使用Letta管理长期记忆",
                "category": "AI"
            },
            {
                "name": "Tool Integration",
                "description": "使用Composio集成200+工具",
                "category": "Integration"
            }
        ]

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "context": context
        }

    async def generate_learning_plan(self, target_skills: List[str]) -> Dict[str, Any]:
        """
        生成学习计划

        Args:
            target_skills: 目标技能列表
        """
        plan = {
            "target_skills": target_skills,
            "steps": [],
            "estimated_time": "N/A"
        }

        for i, skill in enumerate(target_skills):
            plan["steps"].append({
                "step": i + 1,
                "skill": skill,
                "action": f"学习并实践 {skill}",
                "resources": ["文档", "示例代码", "实践项目"]
            })

        return {
            "success": True,
            "learning_plan": plan,
            "total_steps": len(plan["steps"])
        }


# 同步包装器
def parse_skills_md(file_path: Optional[str] = None) -> Dict[str, Any]:
    """同步版本：解析Skills.md"""
    integration = MoltronIntegration()
    return asyncio.run(integration.parse_skills_md(file_path))


def learn_skill(skill_name: str, skill_description: str, category: str = "Auto-learned") -> Dict[str, Any]:
    """同步版本：学习新技能"""
    integration = MoltronIntegration()
    return asyncio.run(integration.learn_skill(skill_name, skill_description, category))


def master_skill(skill_name: str) -> Dict[str, Any]:
    """同步版本：标记技能为已掌握"""
    integration = MoltronIntegration()
    return asyncio.run(integration.master_skill(skill_name))


def suggest_new_skills(context: str = "") -> Dict[str, Any]:
    """同步版本：建议新技能"""
    integration = MoltronIntegration()
    return asyncio.run(integration.suggest_new_skills(context))


if __name__ == "__main__":
    # 测试
    logger.info("Moltron Skills Auto-Evolution Integration Module")
    logger.info("=" * 50)

    logger.info("\n1. 解析Skills.md...")
    result = parse_skills_md()
    if result["success"]:
        logger.info(f"   找到 {result['total_skills']} 个技能")
        logger.info(f"   已掌握: {result['mastered_count']}")
        logger.info(f"   类别: {', '.join(result['categories'])}")
    else:
        logger.info(f"   失败: {result.get('error', 'Unknown error')}")

    logger.info("\n2. 建议新技能...")
    suggestions = suggest_new_skills()
    if suggestions["success"]:
        logger.info(f"   建议学习 {suggestions['count']} 个新技能:")
        for sugg in suggestions["suggestions"]:
            logger.info(f"   - {sugg['name']}: {sugg['description']}")
