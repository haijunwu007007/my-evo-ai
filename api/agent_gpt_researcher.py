"""
GPT-Researcher 集成模块
提供自主研究能力：自动搜索→抓取→生成带引用的研究报告
依赖: pip install gpt-researcher
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# GPT-Researcher 可选依赖
try:
    from gpt_researcher import GPTResearcher
    GPT_RESEARCHER_AVAILABLE = True
except ImportError:
    GPT_RESEARCHER_AVAILABLE = False
    logger.warning("gpt-researcher not installed. Run: pip install gpt-researcher")


class GPTResearcherIntegration:
    """GPT-Researcher 自主研究集成"""

    def __init__(self, report_type: str = "research_report"):
        """
        Args:
            report_type: 报告类型
                - "research_report": 综合研究报告
                - "detailed_report": 详细报告
                - "outline_report": 大纲报告
                - "custom_report": 自定义报告
        """
        self.report_type = report_type

    async def research(
        self,
        query: str,
        source: str = "web",
        report_format: str = "markdown",
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        执行自主研究

        Args:
            query: 研究问题，如"ChatGPT最新动态分析"
            source: 数据源 ("web" | "local" | "hybrid")
            report_format: 报告格式 ("markdown" | "json" | "html")
            max_iterations: 最大迭代次数

        Returns:
            {
                "success": bool,
                "report": str,  # 研究报告内容
                "sources": list,  # 引用的来源
                "cost": float,    # 预估成本
                "research_time": float  # 研究耗时
            }
        """
        if not GPT_RESEARCHER_AVAILABLE:
            return {
                "success": False,
                "error": "gpt-researcher not installed. Run: pip install gpt-researcher"
            }

        try:
            import time
            start_time = time.time()

            # 创建研究员实例
            researcher = GPTResearcher(
                query=query,
                report_type=self.report_type,
                source=source,
                report_format=report_format,
                max_iterations=max_iterations
            )

            # 执行研究
            await researcher.conduct_research()

            # 获取报告
            report = await researcher.get_research_report()
            sources = researcher.get_research_sources() if hasattr(researcher, 'get_research_sources') else []

            research_time = time.time() - start_time

            return {
                "success": True,
                "report": report,
                "sources": sources,
                "research_time": round(research_time, 2),
                "query": query,
                "report_type": self.report_type
            }

        except Exception as e:
            logger.error(f"GPT-Researcher research failed: {e}")
            return {"success": False, "error": str(e)}

    async def quick_research(self, query: str) -> Dict[str, Any]:
        """
        快速研究（使用默认参数）
        """
        return await self.research(query, source="web", report_format="markdown")

    async def compare_topics(self, topics: List[str]) -> Dict[str, Any]:
        """
        对比多个主题

        Args:
            topics: 主题列表，如["ChatGPT", "Claude", "Gemini"]
        """
        results = {}
        for topic in topics:
            result = await self.research(f"对比分析：{topic}")
            results[topic] = result

        return {
            "success": True,
            "comparison": results,
            "topics": topics
        }


# 同步包装器
def do_research(query: str, report_type: str = "research_report") -> Dict[str, Any]:
    """同步版本：执行研究"""
    integration = GPTResearcherIntegration(report_type=report_type)
    return asyncio.run(integration.research(query))


def quick_research(query: str) -> Dict[str, Any]:
    """同步版本：快速研究"""
    integration = GPTResearcherIntegration()
    return asyncio.run(integration.quick_research(query))


# 工具函数：检查安装状态
def check_gpt_researcher_status() -> Dict[str, Any]:
    """检查GPT-Researcher安装状态"""
    status = {
        "available": GPT_RESEARCHER_AVAILABLE,
        "install_command": "pip install gpt-researcher",
        "python_version_ok": True,
        "capabilities": []
    }

    if GPT_RESEARCHER_AVAILABLE:
        status["capabilities"] = [
            "自主网络研究",
            "生成带引用的研究报告",
            "多源数据整合（web + local）",
            "支持多种报告格式（Markdown/JSON/HTML）",
            "主题对比分析",
            "实时信息抓取"
        ]

    return status


if __name__ == "__main__":
    # 测试
    print("GPT-Researcher Integration Module")
    print("=" * 50)
    status = check_gpt_researcher_status()
    print(f"Available: {status['available']}")
    if not status['available']:
        print(f"Install: {status['install_command']}")
    else:
        print("Capabilities:")
        for cap in status['capabilities']:
            print(f"  - {cap}")
