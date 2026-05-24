"""
AUTO-EVO-AI V0.1 — 每日自我进化报告生成器
上市公司级: 趋势分析→统计画像→LLM辅助解读→进化报告
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("evo.evolution")

INISIGHTS_DIR = os.path.join(os.path.dirname(__file__), "..", ".evo_data", "insights")
os.makedirs(INISIGHTS_DIR, exist_ok=True)


class EvolutionReporter:
    """趋势分析与自我进化报告生成"""

    def __init__(self):
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True
        logger.info("[EvolutionReporter] 初始化完成")

    def analyze_trend_data(self, repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析趋势数据，生成统计画像"""
        if not repos:
            return {"success": True, "summary": "暂无趋势数据", "report": {}}

        total = len(repos)
        langs: Dict[str, int] = {}
        stars = []
        descriptions = []

        for r in repos:
            lang = r.get("language", "Unknown") or "Unknown"
            langs[lang] = langs.get(lang, 0) + 1
            s = r.get("stars", 0)
            if isinstance(s, (int, float)):
                stars.append(s)
            desc = (r.get("description") or "").strip()
            if desc:
                descriptions.append(desc)

        top_langs = sorted(langs.items(), key=lambda x: -x[1])[:5]
        avg_stars = sum(stars) / len(stars) if stars else 0
        max_star = max(stars) if stars else 0

        return {
            "success": True,
            "summary": f"共{total}个趋势项目，{len(langs)}种语言，均⭐{avg_stars:.0f}，最高⭐{max_star}",
            "report": {
                "total": total,
                "languages": top_langs,
                "avg_stars": round(avg_stars, 1),
                "max_stars": max_star,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def generate_evolution_report(self, analysis: Dict[str, Any]) -> str:
        """根据分析生成进化报告文本"""
        r = analysis.get("report", {})
        langs_str = ", ".join([f"{lang}({cnt}个)" for lang, cnt in r.get("languages", [])])
        lines = [
            f"# 每日自我进化报告",
            f"",
            f"**日期**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"**摘要**: {analysis.get('summary', 'N/A')}",
            f"",
            f"## 统计概览",
            f"- 趋势项目总数: {r.get('total', 0)}",
            f"- 语言分布: {langs_str or '无'}",
            f"- 平均星标: {r.get('avg_stars', 0)}",
            f"- 最高星标: {r.get('max_stars', 0)}",
            f"",
            f"## 进化建议",
        ]
        # 规则引擎给出简单建议
        top_langs = r.get("languages", [])
        if top_langs:
            hottest = top_langs[0][0]
            lines.append(f"- 热门语言 **{hottest}** 趋势上升，建议关注相关模块更新")
        if r.get("max_stars", 0) > 1000:
            lines.append(f"- 出现高星标项目(⭐{r.get('max_stars')})，建议深入分析其技术栈")
        lines.append(f"- 每日9:00自动扫描，持续跟踪技术趋势")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"*AUTO-EVO-AI V0.1 · 自我进化报告*")

        return "\n".join(lines)

    def save_report(self, report_text: str) -> Dict[str, Any]:
        """保存报告到文件"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = os.path.join(INISIGHTS_DIR, f"evolution_{date_str}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info("[EvolutionReporter] 报告已保存: %s", path)
        return {"success": True, "path": path, "size": len(report_text)}

    def get_recent_reports(self, limit: int = 7) -> List[Dict[str, Any]]:
        """获取近期报告列表"""
        if not os.path.exists(INISIGHTS_DIR):
            return []
        files = sorted(
            [f for f in os.listdir(INISIGHTS_DIR) if f.startswith("evolution_") and f.endswith(".md")],
            reverse=True,
        )[:limit]
        result = []
        for fname in files:
            path = os.path.join(INISIGHTS_DIR, fname)
            result.append({
                "date": fname.replace("evolution_", "").replace(".md", ""),
                "path": path,
                "size": os.path.getsize(path),
            })
        return result


# 模块标准接口
module_class = EvolutionReporter
