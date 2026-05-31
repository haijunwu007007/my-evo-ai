"""
AUTO-EVO-AI V0.1 — 文档自动化
Grade: A (生产级) | Category: 编排调度
职责：自动化文档生成、模板管理、版本控制、多格式导出
"""

__module_meta__ = {
        "id": "doc-automation",
        "name": "Doc Automation",
        "version": "V0.1",
        "group": "documents",
        "inputs": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value_3",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "adapter",
            "doc"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 文档自动化 Grade: A (生产级) | Category: 编排调度"
    }

import re
import asyncio
import time
import uuid
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

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
logger = logging.getLogger("doc_automation")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class DocFormat(Enum):
    """文档格式"""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"

class DocStatus(Enum):
    """文档状态"""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

@dataclass
class DocumentTemplate:
    """文档模板"""

    template_id: str
    name: str
    description: str
    category: str
    format: DocFormat
    content_template: str
    variables: List[str] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    styles: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0

@dataclass
class Document:
    """文档实例"""

    doc_id: str
    title: str
    template_id: Optional[str]
    format: DocFormat
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: DocStatus = DocStatus.DRAFT
    version: int = 1
    versions: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    word_count: int = 0

@dataclass
class GenerationResult:
    """生成结果"""

    success: bool
    doc_id: str
    format: DocFormat
    output_path: Optional[str] = None
    content_length: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None

class DocumentFormatter(object):
    """文档格式分析器 — 检测文档格式、转换格式、验证结构完整性"""

    SUPPORTED_FORMATS = {
        "pdf": "Portable Document Format",
        "docx": "Word Document",
        "xlsx": "Excel Spreadsheet",
        "csv": "Comma-Separated Values",
        "html": "HyperText Markup",
        "markdown": "Markdown",
        "json": "JSON Document",
        "xml": "XML Document",
        "txt": "Plain Text",
    }

    def __init__(self):
        self._format_signatures: Dict[str, Dict[str, Any]] = {
            "pdf": {"magic": b"%PDF", "extension": ".pdf", "binary": True},
            "docx": {"magic": b"PK\x03\x04", "extension": ".docx", "binary": True},
            "xlsx": {"magic": b"PK\x03\x04", "extension": ".xlsx", "binary": True},
            "html": {"magic": b"<!DOCTYPE", "extension": ".html", "binary": False},
            "json": {"magic": b"{", "extension": ".json", "binary": False},
            "xml": {"magic": b"<?xml", "extension": ".xml", "binary": False},
            "csv": {"extension": ".csv", "binary": False},
            "markdown": {"extension": ".md", "binary": False},
            "txt": {"extension": ".txt", "binary": False},
        }

    def detect_format(self, content: bytes, filename: str = "") -> Dict[str, Any]:
        """根据文件头魔数和扩展名检测文档格式"""
        filename_lower = filename.lower()
        detected = []
        for fmt, sig in self._format_signatures.items():
            score = 0
            if sig.get("magic") and content[: len(sig["magic"])] == sig["magic"]:
                score += 80
            ext = sig.get("extension", "")
            if ext and filename_lower.endswith(ext):
                score += 20
            if filename_lower.endswith(ext) and sig.get("magic") and content[: len(sig["magic"])] == sig["magic"]:
                score = 100
            if score > 0:
                detected.append(
                    {"format": fmt, "confidence": score, "description": self.SUPPORTED_FORMATS.get(fmt, "Unknown")}
                )
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "detected_formats": detected,
            "best_match": detected[0] if detected else {"format": "unknown", "confidence": 0},
            "file_size": len(content),
        }

    def convert_plan(self, source_format: str, target_format: str) -> Dict[str, Any]:
        """生成格式转换计划，评估转换复杂度和兼容性"""
        conversions = {
            ("csv", "json"): {"complexity": "low", "steps": ["parse_csv", "map_headers", "emit_json"]},
            ("json", "csv"): {"complexity": "low", "steps": ["parse_json", "flatten", "emit_csv"]},
            ("markdown", "html"): {"complexity": "low", "steps": ["parse_md", "convert_syntax", "emit_html"]},
            ("html", "markdown"): {"complexity": "medium", "steps": ["strip_tags", "extract_text", "format_md"]},
            ("json", "xml"): {"complexity": "medium", "steps": ["parse_json", "build_tree", "emit_xml"]},
            ("xml", "json"): {"complexity": "medium", "steps": ["parse_xml", "extract_data", "emit_json"]},
            ("csv", "xlsx"): {"complexity": "medium", "steps": ["parse_csv", "build_sheet", "write_xlsx"]},
            ("txt", "json"): {"complexity": "high", "steps": ["tokenize", "structure", "emit_json"]},
        }
        key = (source_format.lower(), target_format.lower())
        if key in conversions:
            plan = conversions[key]
            plan["source"] = source_format
            plan["target"] = target_format
            plan["feasible"] = True
            return plan
        return {
            "source": source_format,
            "target": target_format,
            "feasible": False,
            "error": f"No conversion path from {source_format} to {target_format}",
            "suggestion": "Consider converting via an intermediate format (e.g., JSON)",
        }

    def validate_structure(self, content: str, format_type: str = "json") -> Dict[str, Any]:
        """验证文档结构完整性和格式正确性"""
        errors = []
        warnings = []
        stats = {"lines": content.count("\n"), "chars": len(content), "size_kb": round(len(content) / 1024, 2)}
        if format_type == "json":
            try:
                import json

                data = json.loads(content)
                stats["keys_top"] = list(data.keys())[:5] if isinstance(data, dict) else f"array[{len(data)}]"
            except json.JSONDecodeError as e:
                errors.append(f"JSON parse error at line {e.lineno}: {e.msg}")
        elif format_type == "csv":
            lines = [l for l in content.strip().split("\n") if l.strip()]
            if lines:
                header_count = len(lines[0].split(","))
                for i, line in enumerate(lines[1:], 2):
                    col_count = len(line.split(","))
                    if col_count != header_count:
                        warnings.append(f"Row {i}: {col_count} columns (expected {header_count})")
                stats["rows"] = len(lines) - 1
                stats["columns"] = header_count
        elif format_type == "markdown":
            headers = [l for l in content.split("\n") if l.strip().startswith("#")]
            stats["headers"] = len(headers)
            if not headers:
                warnings.append("No headers found in markdown document")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "stats": stats}

class DocAutomation(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """文档自动化引擎"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._documents: Dict[str, Document] = {}
        self._templates: Dict[str, DocumentTemplate] = {}
        self._output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_docs")
        self._max_documents = 10000

    def initialize(self) -> None:
        os.makedirs(self._output_dir, exist_ok=True)
        self._register_builtin_templates()
        self.audit("initialized", "文档自动化模块初始化完成")
        logger.info(f"文档自动化初始化完成，{len(self._templates)} 个模板，输出目录: {self._output_dir}")

    def _register_builtin_templates(self) -> None:
        """注册内置文档模板"""
        templates = [
            DocumentTemplate(
                "tmpl_api_doc",
                "API文档",
                "标准化API接口文档",
                "technical",
                DocFormat.MARKDOWN,
                "# {title}\n\n## 概述\n{description}\n\n## 接口列表\n{api_list}\n\n## 参数说明\n{params}\n\n## 示例\n{examples}\n\n## 错误码\n{error_codes}",
                variables=["title", "description", "api_list", "params", "examples", "error_codes"],
                sections=[
                    {"name": "概述", "required": True},
                    {"name": "接口列表", "required": True},
                    {"name": "参数说明", "required": True},
                    {"name": "示例", "required": False},
                    {"name": "错误码", "required": True},
                ],
            ),
            DocumentTemplate(
                "tmlp_report",
                "分析报告",
                "数据分析报告模板",
                "business",
                DocFormat.HTML,
                "<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{summary}</p><h2>数据概览</h2>{data_overview}<h2>趋势分析</h2>{trends}<h2>结论建议</h2>{conclusions}</body></html>",
                variables=["title", "summary", "data_overview", "trends", "conclusions"],
                sections=[
                    {"name": "数据概览", "required": True},
                    {"name": "趋势分析", "required": True},
                    {"name": "结论建议", "required": True},
                ],
            ),
            DocumentTemplate(
                "tmpl_sprint_review",
                "迭代评审",
                "Sprint迭代评审文档",
                "agile",
                DocFormat.MARKDOWN,
                "# {sprint_name} 迭代评审\n\n## 迭代目标\n{goals}\n\n## 完成情况\n{completed}\n\n## 指标数据\n{metrics}\n\n## 风险与问题\n{risks}\n\n## 下迭代计划\n{next_sprint}",
                variables=["sprint_name", "goals", "completed", "metrics", "risks", "next_sprint"],
            ),
            DocumentTemplate(
                "tmpl_change_log",
                "变更日志",
                "系统变更日志模板",
                "release",
                DocFormat.MARKDOWN,
                "# 变更日志 v{version}\n\n## 发布日期: {date}\n\n## 新功能\n{features}\n\n## 修复\n{fixes}\n\n## 破坏性变更\n{breaking}\n\n## 贡献者\n{contributors}",
                variables=["version", "date", "features", "fixes", "breaking", "contributors"],
            ),
            DocumentTemplate(
                "tmlp_architecture",
                "架构文档",
                "系统架构设计文档",
                "technical",
                DocFormat.MARKDOWN,
                "# {title}\n\n## 架构概述\n{overview}\n\n## 系统组件\n{components}\n\n## 数据流\n{data_flow}\n\n## 部署方案\n{deployment}\n\n## 性能指标\n{performance}",
                variables=["title", "overview", "components", "data_flow", "deployment", "performance"],
            ),
        ]
        for t in templates:
            self._templates[t.template_id] = t

    @trace_operation("create_document")
    def create_document(
        self,
        title: str,
        content: str,
        format: DocFormat = DocFormat.MARKDOWN,
        template_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建文档"""
        try:
            if len(self._documents) >= self._max_documents:
                raise RuntimeError(f"文档数量已达上限 {self._max_documents}")

            doc_id = f"doc_{uuid.uuid4().hex[:10]}"
            doc = Document(
                doc_id=doc_id,
                title=title,
                template_id=template_id,
                format=format,
                content=content,
                metadata=metadata or {},
                tags=tags or [],
            )
            doc.word_count = len(content.split())
            doc.size_bytes = len(content.encode("utf-8"))
            self._documents[doc_id] = doc

            metrics_collector.gauge("doc_automation_total_docs", len(self._documents))
            self.stats["documents_created"] += 1
            return {
                "doc_id": doc_id,
                "title": title,
                "words": doc.word_count,
                "size_bytes": doc.size_bytes,
                "status": doc.status.value,
            }

        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            self.stats["errors"] += 1
            raise

    @trace_operation("generate_from_template")
    def generate_from_template(
        self,
        template_id: str,
        variables: Dict[str, str],
        title: Optional[str] = None,
        format: Optional[DocFormat] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """从模板生成文档"""
        if template_id not in self._templates:
            raise ValueError(f"模板 {template_id} 不存在")
        template = self._templates[template_id]
        template.usage_count += 1

        content = template.content_template
        missing_vars = []
        for var in template.variables:
            placeholder = f"{{{var}}}"
            if var in variables:
                content = content.replace(placeholder, variables[var])
            else:
                content = content.replace(placeholder, f"[待填写: {var}]")
                missing_vars.append(var)

        doc_title = title or template.name
        doc_format = format or template.format

        return self.create_document(
            title=doc_title,
            content=content,
            format=doc_format,
            template_id=template_id,
            tags=tags or [template.category],
            metadata={"template_id": template_id, "missing_variables": missing_vars},
        )

    @trace_operation("export_document")
    def export_document(
        self, doc_id: str, target_format: DocFormat, output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """导出文档为指定格式"""
        try:
            if doc_id not in self._documents:
                raise ValueError(f"文档 {doc_id} 不存在")

            doc = self._documents[doc_id]
            start = time.time()

            export_content = self._convert_format(doc.content, doc.format, target_format)

            if not output_path:
                ext = target_format.value
                output_path = os.path.join(self._output_dir, f"{doc.title}_{doc_id[:8]}.{ext}")

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(export_content)

            duration = (time.time() - start) * 1000
            self.stats["exports_total"] += 1

            audit_logger.log(
                action="export_document", resource=doc_id, details=f"导出为 {target_format.value} -> {output_path}"
            )
            return {
                "doc_id": doc_id,
                "format": target_format.value,
                "path": output_path,
                "size_bytes": len(export_content.encode("utf-8")),
                "duration_ms": round(duration, 2),
            }

        except Exception as e:
            logger.error(f"导出失败 {doc_id}: {e}")
            self.stats["errors"] += 1
            raise

    def _convert_format(self, content: str, source: DocFormat, target: DocFormat) -> str:
        """格式转换"""
        if source == target:
            return content

        converters = {
            (DocFormat.MARKDOWN, DocFormat.HTML): self._md_to_html,
            (DocFormat.MARKDOWN, DocFormat.TXT): self._md_to_txt,
            (DocFormat.MARKDOWN, DocFormat.JSON): self._md_to_json,
            (DocFormat.HTML, DocFormat.TXT): self._html_to_txt,
            (DocFormat.HTML, DocFormat.MARKDOWN): self._html_to_md,
            (DocFormat.JSON, DocFormat.HTML): self._json_to_html,
        }

        converter = converters.get((source, target))
        if converter:
            return converter(content)

        return content

    def _md_to_html(self, md: str) -> str:
        """Markdown -> HTML"""
        import re

        lines = md.split("\n")
        html_lines = []
        in_list = False
        in_code = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    html_lines.append("</code></pre>")
                    in_code = False
                else:
                    lang = stripped[3:].strip()
                    html_lines.append(f'<pre><code class="{lang}">')
                    in_code = True
                continue
            if in_code:
                html_lines.append(stripped)
                continue

            if stripped.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{stripped[2:]}</li>")
            elif re.match(r"^\d+\.\s", stripped):
                if not in_list:
                    html_lines.append("<ol>")
                    in_list = True
                text = re.sub(r"^\d+\.\s", "", stripped)
                html_lines.append(f"<li>{text}</li>")
            elif stripped == "":
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<p>{stripped}</p>")

        if in_list:
            html_lines.append("</ul>")

        body = "\n".join(html_lines)
        return f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>Document</title></head>\n<body>\n{body}\n</body></html>'

    def _md_to_txt(self, md: str) -> str:
        import re

        txt = re.sub(r"^#{1,6}\s+", "", md, flags=re.MULTILINE)
        txt = re.sub(r"\*\*(.+?)\*\*", r"\1", txt)
        txt = re.sub(r"\*(.+?)\*", r"\1", txt)
        txt = re.sub(r"`(.+?)`", r"\1", txt)
        txt = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", txt)
        return txt

    def _md_to_json(self, md: str) -> str:
        sections = {}
        current_section = "body"
        current_lines = []
        for line in md.split("\n"):
            if line.startswith("# "):
                if current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = line[2:].strip()
                current_lines = []
            elif line.startswith("## "):
                if current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            sections[current_section] = "\n".join(current_lines).strip()
        return json.dumps(sections, ensure_ascii=False, indent=2)

    def _html_to_txt(self, html: str) -> str:
        import re

        txt = re.sub(r"<[^>]+>", "", html)
        txt = re.sub(r"&nbsp;", " ", txt)
        txt = re.sub(r"&amp;", "&", txt)
        txt = re.sub(r"&lt;", "<", txt)
        txt = re.sub(r"&gt;", ">", txt)
        return txt.strip()

    def _html_to_md(self, html: str) -> str:
        import re

        md = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", html, flags=re.DOTALL)
        md = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", md, flags=re.DOTALL)
        md = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", md, flags=re.DOTALL)
        md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1", md, flags=re.DOTALL)
        md = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n", md, flags=re.DOTALL)
        md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
        md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)
        md = re.sub(r"<[^>]+>", "", md)
        return md.strip()

    def _json_to_html(self, json_str: str) -> str:
        try:
            data = json.loads(json_str)
            items = []
            if isinstance(data, dict):
                for k, v in data.items():
                    items.append(f"<dt><strong>{k}</strong></dt><dd>{v}</dd>")
                body = f"<dl>{''.join(items)}</dl>"
            else:
                body = f"<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"
            return f'<html><head><meta charset="utf-8"></head><body>{body}</body></html>'
        except json.JSONDecodeError:
            return f"<html><body><pre>{json_str}</pre></body></html>"

    @trace_operation("update_document")
    def update_document(
        self, doc_id: str, content: Optional[str] = None, title: Optional[str] = None, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """更新文档（自动版本控制）"""
        if doc_id not in self._documents:
            raise ValueError(f"文档 {doc_id} 不存在")

        doc = self._documents[doc_id]
        # 保存旧版本
        doc.versions.append(
            {"version": doc.version, "content": doc.content, "title": doc.title, "updated_at": doc.updated_at}
        )
        doc.version += 1

        if content is not None:
            doc.content = content
            doc.word_count = len(content.split())
            doc.size_bytes = len(content.encode("utf-8"))
        if title is not None:
            doc.title = title
        if metadata is not None:
            doc.metadata.update(metadata)

        doc.updated_at = time.time()
        self.stats["documents_updated"] += 1
        return {
            "doc_id": doc_id,
            "version": doc.version,
            "words": doc.word_count,
            "history_versions": len(doc.versions),
        }

    @trace_operation("batch_generate")
    def batch_generate(
        self, template_id: str, batch_variables: List[Dict[str, str]], format: Optional[DocFormat] = None
    ) -> List[Dict]:
        """批量生成文档"""
        results = []
        for i, variables in enumerate(batch_variables):
            try:
                result = self.generate_from_template(
                    template_id=template_id, variables=variables, title=variables.get("title"), format=format
                )
                results.append({"index": i, "success": True, **result})
            except Exception as e:
                results.append({"index": i, "success": False, "error": str(e)})
        return results

    def list_documents(self, tag: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """列出文档"""
        docs = list(self._documents.values())
        if tag:
            docs = [d for d in docs if tag in d.tags]
        if status:
            docs = [d for d in docs if d.status.value == status]
        docs.sort(key=lambda d: d.updated_at, reverse=True)
        return [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "format": d.format.value,
                "status": d.status.value,
                "version": d.version,
                "words": d.word_count,
                "tags": d.tags,
                "updated_at": datetime.fromtimestamp(d.updated_at).isoformat(),
            }
            for d in docs[:limit]
        ]

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """获取文档详情"""
        if doc_id not in self._documents:
            raise ValueError(f"文档 {doc_id} 不存在")
        doc = self._documents[doc_id]
        return {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "format": doc.format.value,
            "status": doc.status.value,
            "version": doc.version,
            "content": doc.content,
            "metadata": doc.metadata,
            "tags": doc.tags,
            "word_count": doc.word_count,
            "size_bytes": doc.size_bytes,
            "versions": len(doc.versions),
            "created_at": datetime.fromtimestamp(doc.created_at).isoformat(),
            "updated_at": datetime.fromtimestamp(doc.updated_at).isoformat(),
        }

    def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self._documents:
            raise ValueError(f"文档 {doc_id} 不存在")
        del self._documents[doc_id]
        self.stats["documents_deleted"] += 1
        return True

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        params = params or {}
        actions = {
            "create_document": self.create_document,
            "generate_from_template": self.generate_from_template,
            "export_document": self.export_document,
            "update_document": self.update_document,
            "batch_generate": self.batch_generate,
            "list_documents": self.list_documents,
            "get_document": self.get_document,
            "delete_document": self.delete_document,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "total_documents": len(self._documents),
                "templates": len(self._templates),
                "output_dir": self._output_dir,
                "total_exports": self.stats.get("exports_total", 0),
                "storage_usage_mb": round(sum(d.size_bytes for d in self._documents.values()) / 1048576, 2),
            }
        )
        return base

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown", resource="doc_automation", details=f"关闭，共 {len(self._documents)} 个文档"
        )

module_class = DocAutomation
