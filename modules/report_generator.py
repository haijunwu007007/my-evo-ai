# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 报告生成器（A级）"""
__module_meta__ = {"id":"report-generator","name":"Report Generator","version":"V0.1","group":"data","grade":"A",
    "tags":["data","report","document"],"description":"报告生成器 - 真实HTML报告/JSON摘要/结构化输出"}

import json, logging, html, os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)

logger = logging.getLogger("evo.report-generator")

# ── 内嵌 CSS 样式（零外部依赖） ──────────────────────────────────────
_REPORT_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f5f7fa; color: #1a1a2e; line-height: 1.6; padding: 20px; }
.report-container { max-width: 960px; margin: 0 auto; background: #fff;
                    border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                    overflow: hidden; }
.report-header { background: linear-gradient(135deg, #667eea, #764ba2);
                 color: #fff; padding: 32px 40px; }
.report-header h1 { font-size: 28px; margin-bottom: 6px; }
.report-header .meta { font-size: 13px; opacity: 0.85; }
.report-body { padding: 32px 40px; }
.section { margin-bottom: 28px; }
.section h2 { font-size: 20px; color: #333; border-left: 4px solid #667eea;
              padding-left: 12px; margin-bottom: 14px; }
.section p { color: #555; margin-bottom: 8px; }
.section .metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                        gap: 14px; margin-top: 10px; }
.metric-card { background: #f8f9ff; border-radius: 8px; padding: 16px;
               border: 1px solid #e8ecf4; }
.metric-card .label { font-size: 12px; color: #888; text-transform: uppercase;
                      letter-spacing: 0.5px; }
.metric-card .value { font-size: 22px; font-weight: 700; color: #333; margin-top: 4px; }
table.data-table { width: 100%; border-collapse: collapse; margin-top: 10px;
                   font-size: 14px; }
table.data-table th { background: #667eea; color: #fff; padding: 10px 14px;
                      text-align: left; font-weight: 600; }
table.data-table td { padding: 8px 14px; border-bottom: 1px solid #eee; }
table.data-table tr:nth-child(even) { background: #f9fafc; }
.report-footer { text-align: center; padding: 20px; font-size: 12px; color: #aaa;
                 border-top: 1px solid #eee; }
"""


class ReportGenerator(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "report-generator"
    MODULE_NAME = "报告生成器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._generated = 0
        self._start = datetime.now()

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info("ReportGenerator initialized")

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True, module_id=self.MODULE_ID,
            checks={"generated": self._generated}
        )

    async def execute(self, action, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p):
        a = p.get("action", "status")
        if a == "status":
            return {"success": True, "generated": self._generated}
        if a == "generate_html_report":
            return self._action_generate_html_report(p)
        if a == "generate_summary":
            return self._action_generate_summary(p)
        if a == "to_html":
            return self._action_to_html(p)
        if a == "stats":
            return {
                "total_generated": self._generated,
                "uptime_seconds": round((datetime.now() - self._start).total_seconds(), 1)
            }
        return {"error": f"unknown:{a}"}

    # ── public API: generate_html_report ────────────────────────────────
    def generate_html_report(self, title: str,
                             sections: List[Dict[str, Any]]) -> str:
        """生成美观的 HTML 报告

        sections 每项格式：
            {"type": "text", "title": "...", "content": "..."}
            {"type": "metrics", "title": "...", "items": [{"label":"...","value":"..."}]}
            {"type": "table", "title": "...", "headers": [...], "rows": [[...], ...]}
            {"type": "code", "title": "...", "content": "..."}
        """
        safe_title = html.escape(title)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body_html = "".join(self._render_section(s) for s in sections)

        report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{safe_title}</title>
<style>{_REPORT_CSS}</style></head>
<body>
<div class="report-container">
  <div class="report-header">
    <h1>{safe_title}</h1>
    <div class="meta">Generated: {html.escape(now)} | AUTO-EVO-AI V0.1</div>
  </div>
  <div class="report-body">
    {body_html}
  </div>
  <div class="report-footer">AUTO-EVO-AI Report Generator &mdash; V0.1</div>
</div>
</body>
</html>"""
        self._generated += 1
        logger.info("generate_html_report: '%s' with %d sections", title, len(sections))
        return report

    def _render_section(self, s: Dict[str, Any]) -> str:
        stype = s.get("type", "text")
        title = html.escape(s.get("title", ""))
        html_parts = [f'<div class="section"><h2>{title}</h2>']

        if stype == "text":
            content = html.escape(s.get("content", ""))
            html_parts.append(f"<p>{content}</p>")

        elif stype == "metrics":
            items = s.get("items", [])
            html_parts.append('<div class="metric-grid">')
            for item in items:
                label = html.escape(str(item.get("label", "")))
                value = html.escape(str(item.get("value", "")))
                html_parts.append(
                    f'<div class="metric-card">'
                    f'<div class="label">{label}</div>'
                    f'<div class="value">{value}</div>'
                    f'</div>'
                )
            html_parts.append("</div>")

        elif stype == "table":
            headers = s.get("headers", [])
            rows = s.get("rows", [])
            html_parts.append('<table class="data-table"><thead><tr>')
            for h in headers:
                html_parts.append(f"<th>{html.escape(str(h))}</th>")
            html_parts.append("</tr></thead><tbody>")
            for row in rows:
                html_parts.append("<tr>")
                for cell in row:
                    html_parts.append(f"<td>{html.escape(str(cell))}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody></table>")

        elif stype == "code":
            content = html.escape(s.get("content", ""))
            html_parts.append(
                f'<pre style="background:#f4f4f8;padding:14px;border-radius:6px;'
                f'overflow-x:auto;font-size:13px;">{content}</pre>'
            )

        html_parts.append("</div>")
        return "".join(html_parts)

    # ── public API: generate_summary ────────────────────────────────────
    def generate_summary(self, data: Any,
                         fmt: str = "json") -> Union[str, Dict[str, Any]]:
        """生成摘要，支持 json / text 两种格式"""
        if fmt == "json":
            result = self._summary_to_json(data)
            self._generated += 1
            return result
        else:
            result = self._summary_to_text(data)
            self._generated += 1
            return result

    def _summary_to_json(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys()),
                "key_count": len(data),
                "sample": {k: data[k] for k in list(data.keys())[:5]}
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "sample": data[:5]
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:200]
            }

    def _summary_to_text(self, data: Any) -> str:
        if isinstance(data, dict):
            lines = [f"Dict ({len(data)} keys):"]
            for k, v in list(data.items())[:10]:
                lines.append(f"  {k}: {str(v)[:60]}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = [f"List ({len(data)} items):"]
            for i, item in enumerate(data[:10]):
                lines.append(f"  [{i}]: {str(item)[:80]}")
            return "\n".join(lines)
        else:
            return f"{type(data).__name__}: {str(data)[:200]}"

    # ── legacy: to_html (backward compat) ───────────────────────────────
    def _action_to_html(self, p):
        title = p.get("title", "Report")
        sections_data = p.get("sections", p.get("data", []))
        if isinstance(sections_data, list) and all(isinstance(s, str) for s in sections_data):
            sections = [{"type": "text", "title": "", "content": s} for s in sections_data]
        else:
            sections = sections_data if isinstance(sections_data, list) else []
        html = self.generate_html_report(title, sections)
        return {"success": True, "html": html, "format": "html"}

    def _action_generate_html_report(self, p):
        title = p.get("title", "Report")
        sections = p.get("sections", [])
        html = self.generate_html_report(title, sections)
        return {"success": True, "html": html, "format": "html", "sections": len(sections)}

    def _action_generate_summary(self, p):
        data = p.get("data", {})
        fmt = p.get("format", "json")
        result = self.generate_summary(data, fmt)
        return {"success": True, "result": result, "format": fmt}

    async def shutdown(self) -> None:
        self.status = ModuleStatus.STOPPED
        logger.info("ReportGenerator shut down (total generated: %d)", self._generated)


module_class = ReportGenerator
