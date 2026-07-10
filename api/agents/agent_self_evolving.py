"""
Self-Evolving Agent 集成模块
提供Agent自主进化能力：读源码→分析→改进→测试→提交
参考: https://github.com/self-evolving/starter
"""

import os
import ast
import logging
import subprocess
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SelfEvolvingIntegration:
    """
    Self-Evolving Agent 自主进化集成
    
    能力：
    1. 读取系统源码
    2. 分析潜在改进点
    3. 自动生成改进代码
    4. 运行测试验证
    5. 提交改进（可选）
    """

    def __init__(self, repo_path: str = "."):
        """
        Args:
            repo_path: 代码仓库路径
        """
        self.repo_path = Path(repo_path)
        self.evolution_history = []

    async def analyze_codebase(self) -> Dict[str, Any]:
        """
        分析代码库，找出潜在改进点
        
        Returns:
            {
                "success": bool,
                "issues": [
                    {
                        "file": str,
                        "line": int,
                        "type": str,  # "bug" | "optimization" | "refactor" | "feature"
                        "description": str,
                        "suggestion": str
                    }
                ],
                "summary": str
            }
        """
        issues = []
        files_analyzed = 0

        try:
            # 遍历Python文件
            for py_file in self.repo_path.rglob("*.py"):
                if any(part in str(py_file) for part in ["__pycache__", ".venv", "node_modules", ".git"]):
                    continue

                files_analyzed += 1
                file_issues = await self._analyze_file(py_file)
                issues.extend(file_issues)

            # 生成摘要
            summary = f"分析了 {files_analyzed} 个文件，发现 {len(issues)} 个潜在改进点。\n"
            issue_types = {}
            for issue in issues:
                issue_type = issue["type"]
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            for issue_type, count in issue_types.items():
                summary += f"- {issue_type}: {count} 个\n"

            return {
                "success": True,
                "issues": issues[:20],  # 限制返回数量
                "total_issues": len(issues),
                "files_analyzed": files_analyzed,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Codebase analysis failed: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """分析单个文件"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)

            # 检查常见问题
            issues.extend(self._check_common_issues(file_path, content, tree))
            issues.extend(self._check_complexity(file_path, tree))
            issues.extend(self._check_docstrings(file_path, tree))

        except SyntaxError as e:
            issues.append({
                "file": str(file_path),
                "line": e.lineno or 0,
                "type": "bug",
                "description": f"语法错误: {e.msg}",
                "suggestion": "修复语法错误"
            })
        except Exception as e:
            pass  # 跳过无法分析的文件

        return issues

    def _check_common_issues(self, file_path: Path, content: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """检查常见问题"""
        issues = []

        # 检查bare except
        if "except:" in content or "except Exception:" in content:
            # 简化检查
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "except Exception:" in line and i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if next_line in ["pass", "return", "continue"]:
                        issues.append({
                            "file": str(file_path),
                            "line": i + 1,
                            "type": "optimization",
                            "description": "空的except块",
                            "suggestion": "添加适当的错误处理或日志记录"
                        })

        # 检查TODO/FIXME注释
        for i, line in enumerate(content.split("\n")):
            if "TODO" in line or "FIXME" in line:
                issues.append({
                    "file": str(file_path),
                    "line": i + 1,
                    "type": "feature",
                    "description": f"待实现功能: {line.strip()}",
                    "suggestion": "实现此功能或移除注释"
                })

        return issues

    def _check_complexity(self, file_path: Path, tree: ast.AST) -> List[Dict[str, Any]]:
        """检查代码复杂度"""
        issues = []

        # 检查函数长度
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > 50:
                    issues.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "refactor",
                        "description": f"函数 {node.name} 过长 ({func_lines} 行)",
                        "suggestion": "将函数拆分为多个小函数"
                    })

        return issues

    def _check_docstrings(self, file_path: Path, tree: ast.AST) -> List[Dict[str, Any]]:
        """检查文档字符串"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "optimization",
                        "description": f"{'函数' if isinstance(node, ast.FunctionDef) else '类'} {node.name} 缺少文档字符串",
                        "suggestion": "添加文档字符串"
                    })

        return issues

    async def propose_improvement(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        为指定问题提出改进方案

        Args:
            issue: 问题分析结果的单个issue
        """
        try:
            file_path = Path(issue["file"])
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 这里可以调用LLM生成改进代码
            # 简化版本：返回问题描述和建议
            improvement = {
                "issue": issue,
                "proposed_code": f"# 建议改进 {issue['file']} 第 {issue['line']} 行\n# {issue['suggestion']}",
                "confidence": 0.8
            }

            return {
                "success": True,
                "improvement": improvement
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def apply_improvement(
        self,
        issue: Dict[str, Any],
        improvement: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        应用改进

        Args:
            issue: 问题
            improvement: 改进方案
            dry_run: 是否仅模拟（不实际修改文件）
        """
        try:
            if dry_run:
                return {
                    "success": True,
                    "message": "Dry run - no changes made",
                    "proposed_code": improvement.get("proposed_code", ""),
                    "file": issue["file"]
                }

            # 实际修改文件（需要谨慎）
            # 这里只是示例，实际需要更复杂的逻辑
            return {
                "success": True,
                "message": "Improvement applied (simulated)",
                "file": issue["file"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_tests(self) -> Dict[str, Any]:
        """运行测试验证改进"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[-2000:],  # 限制输出长度
                "stderr": result.stderr[-1000:] if result.stderr else ""
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Tests timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def commit_improvement(self, message: str) -> Dict[str, Any]:
        """提交改进到Git"""
        try:
            # 检查是否有改动
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if not status_result.stdout.strip():
                return {"success": False, "error": "No changes to commit"}

            # 添加所有改动
            subprocess.run(["git", "add", "."], cwd=self.repo_path)

            # 提交
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if commit_result.returncode == 0:
                return {
                    "success": True,
                    "message": "Committed successfully",
                    "commit_output": commit_result.stdout
                }
            else:
                return {"success": False, "error": commit_result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_evolution_history(self) -> List[Dict[str, Any]]:
        """获取进化历史"""
        return self.evolution_history


# 同步包装器
def analyze_codebase(repo_path: str = ".") -> Dict[str, Any]:
    """同步版本：分析代码库"""
    integration = SelfEvolvingIntegration(repo_path)
    return asyncio.run(integration.analyze_codebase())


def run_tests(repo_path: str = ".") -> Dict[str, Any]:
    """同步版本：运行测试"""
    integration = SelfEvolvingIntegration(repo_path)
    return asyncio.run(integration.run_tests())


def commit_improvement(message: str, repo_path: str = ".") -> Dict[str, Any]:
    """同步版本：提交改进"""
    integration = SelfEvolvingIntegration(repo_path)
    return asyncio.run(integration.commit_improvement(message))


if __name__ == "__main__":
    # 测试
    logger.info("Self-Evolving Agent Integration Module")
    logger.info("=" * 50)
    
    logger.info("\n1. 分析代码库...")
    result = analyze_codebase(".")
    if result["success"]:
        logger.info(f"   分析了 {result['files_analyzed']} 个文件")
        logger.info(f"   发现 {result['total_issues']} 个潜在改进点")
        logger.info(f"\n{result['summary']}")
    else:
        logger.info(f"   失败: {result.get('error', 'Unknown error')}")
