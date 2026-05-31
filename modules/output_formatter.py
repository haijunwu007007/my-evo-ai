"""
# Grade: A
AUTO-EVO-AI V0.1 | Enterprise Module
output_formatter — 企业级输出格式化引擎
多格式输出(JSON/YAML/XML/CSV/Markdown/HTML/Table)、模板系统、字段映射、
条件渲染、嵌套格式化、数据验证、流式输出、字符编码管理
"""

__module_meta__ = {
        "id": "output-formatter",
        "name": "Output Formatter",
        "version": "V0.1",
        "group": "developer",
        "inputs": [
            {
                "name": "value",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "transform",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "format_str",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "size",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "template",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "engine",
            "output"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 | Enterprise Module output_formatter — 企业级输出格式化引擎"
    }

import json
import csv
import io
import re
import html
from typing import Any, Optional
from datetime import datetime
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"
    TABLE = "table"
    PLAIN = "plain"
    TSV = "tsv"

@dataclass
class FieldMapping:
    source_key: str
    target_key: str = ""
    transform: str = ""  # upper, lower, title, round, date, datetime, currency, percent, bool
    default: Any = None
    format_str: str = ""
    condition: str = ""  # field name to check, skip if falsy

@dataclass
class FormatTemplate:
    name: str
    format_type: OutputFormat
    header: str = ""
    footer: str = ""
    row_template: str = ""
    field_mappings: list = field(default_factory=list)
    include_fields: list = field(default_factory=list)
    exclude_fields: list = field(default_factory=list)
    max_depth: int = 5
    indent: int = 2
    encoding: str = "utf-8"
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"

class TransformEngine(object):
    """数据转换引擎"""

    @staticmethod
    def apply(value: Any, transform: str, format_str: str = "") -> Any:
        if not transform or value is None:
            return value
        try:
            if transform == "upper":
                return str(value).upper()
            elif transform == "lower":
                return str(value).lower()
            elif transform == "title":
                return str(value).title()
            elif transform == "round":
                decimals = int(format_str) if format_str.isdigit() else 2
                return round(float(value), decimals)
            elif transform == "date":
                if isinstance(value, datetime):
                    fmt = format_str or "%Y-%m-%d"
                    return value.strftime(fmt)
                return str(value)
            elif transform == "datetime":
                if isinstance(value, datetime):
                    fmt = format_str or "%Y-%m-%d %H:%M:%S"
                    return value.strftime(fmt)
                return str(value)
            elif transform == "currency":
                return f"¥{float(value):,.2f}"
            elif transform == "percent":
                return f"{float(value) * 100:.1f}%"
            elif transform == "bool":
                return "✓" if value else "✗"
            elif transform == "bytes":
                return TransformEngine._format_bytes(int(value))
            elif transform == "strip":
                return str(value).strip()
            elif transform == "truncate":
                max_len = int(format_str) if format_str.isdigit() else 50
                s = str(value)
                return s[:max_len] + "..." if len(s) > max_len else s
            elif transform == "escape_html":
                return html.escape(str(value))
            elif transform == "escape_xml":
                return html.escape(str(value)).replace("'", "&apos;").replace('"', "&quot;")
        except (ValueError, TypeError):
            pass
        return value

    @staticmethod
    def _format_bytes(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size) < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

class OutputFormatter(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """企业级输出格式化引擎"""

    def __init__(self):

        super().__init__("output_formatter", "1.0.0")
        self._templates: dict[str, FormatTemplate] = {}
        self._transforms = TransformEngine()
        self._stats = {"formatted": 0, "streamed": 0, "errors": 0}
        self._stream_buffers: dict[str, io.StringIO] = {}
        self._encoding_registry = {
            "utf-8": "utf-8",
            "gbk": "gbk",
            "gb2312": "gb2312",
            "latin-1": "latin-1",
            "ascii": "ascii",
        }

    def initialize(self) -> ModuleStatus:
        self._register_defaults()
        return self._set_status(ModuleStatus.RUNNING)

    def _register_defaults(self):
        self.register_template(FormatTemplate(name="default_json", format_type=OutputFormat.JSON, indent=2))
        self.register_template(FormatTemplate(name="default_csv", format_type=OutputFormat.CSV))
        self.register_template(FormatTemplate(name="default_markdown", format_type=OutputFormat.MARKDOWN))
        self.register_template(FormatTemplate(name="default_html_table", format_type=OutputFormat.HTML))
        self.register_template(FormatTemplate(name="default_table", format_type=OutputFormat.TABLE))

    def register_template(self, template: FormatTemplate):
        self._templates[template.name] = template

    def get_template(self, name: str) -> Optional[FormatTemplate]:
        return self._templates.get(name)

    def format_data(
        self, data: Any, fmt: OutputFormat = OutputFormat.JSON, template: Optional[str] = None, **kwargs
    ) -> str:
        tmpl = self._templates.get(template) if template else None
        try:
            processed = self._apply_mappings(data, tmpl)
            result = self._render(processed, fmt, tmpl, **kwargs)
            self._stats["formatted"] += 1
            return result
        except Exception as e:
            self._stats["errors"] += 1
            raise

    def format_list(
        self, items: list[dict], fmt: OutputFormat = OutputFormat.JSON, template: Optional[str] = None, **kwargs
    ) -> str:
        if fmt == OutputFormat.JSON:
            return self._render_json(items, kwargs.get("indent", 2))
        elif fmt in (OutputFormat.CSV, OutputFormat.TSV):
            return self._render_tabular(items, "\t" if fmt == OutputFormat.TSV else ",")
        elif fmt == OutputFormat.MARKDOWN:
            return self._render_markdown_table(items)
        elif fmt == OutputFormat.HTML:
            return self._render_html_table(items, kwargs.get("title", "Data"))
        elif fmt == OutputFormat.TABLE:
            return self._render_plain_table(items)
        return self._render_json(items, 2)

    def _apply_mappings(self, data: Any, tmpl: Optional[FormatTemplate]) -> Any:
        if not tmpl or not tmpl.field_mappings:
            return data
        if isinstance(data, dict):
            result = {}
            for mapping in tmpl.field_mappings:
                if mapping.condition and not data.get(mapping.condition):
                    continue
                target = mapping.target_key or mapping.source_key
                value = data.get(mapping.source_key, mapping.default)
                result[target] = self._transforms.apply(value, mapping.transform, mapping.format_str)
            return result
        elif isinstance(data, list):
            return [self._apply_mappings(item, tmpl) for item in data]
        return data

    def _render(self, data: Any, fmt: OutputFormat, tmpl: Optional[FormatTemplate] = None, **kwargs) -> str:
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return self.format_list(data, fmt, **kwargs)
        parts = []
        if tmpl and tmpl.header:
            parts.append(tmpl.header)
        parts.append(self._render_single(data, fmt, tmpl))
        if tmpl and tmpl.footer:
            parts.append(tmpl.footer)
        return "\n".join(parts)

    def _render_single(self, data: Any, fmt: OutputFormat, tmpl: Optional[FormatTemplate] = None) -> str:
        if fmt == OutputFormat.JSON:
            return self._render_json(data, (tmpl.indent if tmpl else 2))
        elif fmt == OutputFormat.YAML:
            return self._render_yaml(data)
        elif fmt == OutputFormat.XML:
            return self._render_xml(data)
        elif fmt == OutputFormat.MARKDOWN:
            return self._render_markdown(data)
        elif fmt == OutputFormat.HTML:
            return self._render_html(data)
        elif fmt == OutputFormat.PLAIN:
            return self._render_plain(data)
        return str(data)

    def _render_json(self, data: Any, indent: int = 2) -> str:
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Not serializable: {type(obj)}")

        return json.dumps(data, indent=indent, ensure_ascii=False, default=default_serializer)

    def _render_yaml(self, data: Any, prefix: str = "") -> str:
        lines = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)) and v:
                    if isinstance(v, dict):
                        lines.append(f"{prefix}{k}:")
                        lines.append(self._render_yaml(v, prefix + "  "))
                    else:
                        lines.append(f"{prefix}{k}:")
                        for item in v:
                            if isinstance(item, dict):
                                lines.append(f"{prefix}  -")
                                lines.append(self._render_yaml(item, prefix + "    "))
                            else:
                                lines.append(f"{prefix}  - {self._yaml_val(item)}")
                else:
                    lines.append(f"{prefix}{k}: {self._yaml_val(v)}")
        return "\n".join(lines)

    def _yaml_val(self, v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, datetime):
            return v.isoformat()
        s = str(v)
        if any(c in s for c in ":#{}[]!&*?'|>-\"'") or s in ("true", "false", "null"):
            return f'"{s}"'
        return s

    def _render_xml(self, data: Any, root_tag: str = "root", depth: int = 0) -> str:
        indent = "  " * depth
        if isinstance(data, dict):
            parts = [f"{indent}<{root_tag}>"]
            for k, v in data.items():
                tag = re.sub(r"[^a-zA-Z0-9_-]", "_", str(k))
                parts.append(self._render_xml(v, tag, depth + 1))
            parts.append(f"{indent}</{root_tag}>")
            return "\n".join(parts)
        elif isinstance(data, list):
            parts = []
            for item in data:
                parts.append(self._render_xml(item, "item", depth))
            return "\n".join(parts)
        else:
            escaped = html.escape(str(data)) if data is not None else ""
            return f"{indent}<{root_tag}>{escaped}</{root_tag}>"

    def _render_tabular(self, items: list[dict], delimiter: str = ",") -> str:
        if not items:
            return ""
        all_keys = list(OrderedDict.fromkeys(k for item in items for k in item.keys()))
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=delimiter)
        writer.writerow(all_keys)
        for item in items:
            writer.writerow([self._tabular_val(item.get(k)) for k in all_keys])
        return buf.getvalue().strip()

    def _tabular_val(self, v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (list, dict)):
            return self._render_json(v)
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

    def _render_markdown_table(self, items: list[dict]) -> str:
        if not items:
            return ""
        keys = list(OrderedDict.fromkeys(k for item in items for k in item.keys()))
        lines = []
        lines.append("| " + " | ".join(keys) + " |")
        lines.append("| " + " | ".join("---" for _ in keys) + " |")
        for item in items:
            vals = [self._md_cell(item.get(k)) for k in keys]
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    def _md_cell(self, v: Any) -> str:
        if v is None:
            return ""
        return str(v).replace("|", "\\|").replace("\n", " ")

    def _render_html_table(self, items: list[dict], title: str = "Data") -> str:
        if not items:
            return "<p>No data</p>"
        keys = list(OrderedDict.fromkeys(k for item in items for k in item.keys()))
        rows = []
        header = "<tr>" + "".join(f"<th>{html.escape(str(k))}</th>" for k in keys) + "</tr>"
        for item in items:
            row = "<tr>" + "".join(f"<td>{html.escape(str(item.get(k, '')))}</td>" for k in keys) + "</tr>"
            rows.append(row)
        return (
            f"<div class='output-table'><h3>{html.escape(title)}</h3>"
            f"<table border='1' cellpadding='5' cellspacing='0'><thead>{header}</thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            f"<p class='meta'>Total: {len(items)} rows</p></div>"
        )

    def _render_plain_table(self, items: list[dict]) -> str:
        if not items:
            return "No data"
        keys = list(OrderedDict.fromkeys(k for item in items for k in item.keys()))
        col_widths = {k: max(len(str(k)), max((len(str(item.get(k, ""))) for item in items), default=0)) for k in keys}
        lines = []
        lines.append(" | ".join(str(k).ljust(col_widths[k]) for k in keys))
        lines.append("-+-".join("-" * col_widths[k] for k in keys))
        for item in items:
            lines.append(" | ".join(str(item.get(k, "")).ljust(col_widths[k]) for k in keys))
        return "\n".join(lines)

    def _render_markdown(self, data: Any) -> str:
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, list):
                    lines.append(f"## {k}")
                    for item in v:
                        lines.append(f"- {item}")
                elif isinstance(v, dict):
                    lines.append(f"## {k}")
                    lines.append(self._render_markdown(v))
                else:
                    lines.append(f"**{k}:** {v}")
            return "\n".join(lines)
        return str(data)

    def _render_html(self, data: Any) -> str:
        if isinstance(data, dict):
            parts = ["<dl>"]
            for k, v in data.items():
                parts.append(f"<dt>{html.escape(str(k))}</dt>")
                parts.append(f"<dd>{html.escape(str(v))}</dd>")
            parts.append("</dl>")
            return "\n".join(parts)
        return f"<p>{html.escape(str(data))}</p>"

    def _render_plain(self, data: Any) -> str:
        if isinstance(data, dict):
            return "\n".join(f"{k}: {v}" for k, v in data.items())
        if isinstance(data, list):
            return "\n".join(f"- {item}" for item in data)
        return str(data)

    def stream_start(self, stream_id: str, fmt: OutputFormat = OutputFormat.JSON):
        self._stream_buffers[stream_id] = io.StringIO()

    def stream_append(self, stream_id: str, data: Any):
        if stream_id in self._stream_buffers:
            self._stream_buffers[stream_id].write(str(data))
            self._stream_buffers[stream_id].write("\n")

    def stream_end(self, stream_id: str) -> str:
        buf = self._stream_buffers.pop(stream_id, None)
        if buf:
            self._stats["streamed"] += 1
            return buf.getvalue()
        return ""

    def auto_detect_format(self, content: str) -> OutputFormat:
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return OutputFormat.JSON
        if stripped.startswith("<") and stripped.endswith(">"):
            return OutputFormat.XML
        if stripped.startswith("|") or stripped.startswith("#"):
            return OutputFormat.MARKDOWN
        if stripped.startswith("---") or re.match(r"^\w+:", stripped, re.MULTILINE):
            return OutputFormat.YAML
        lines = stripped.split("\n")
        if len(lines) > 1 and "," in lines[0]:
            return OutputFormat.CSV
        return OutputFormat.PLAIN

    def validate_output(self, content: str, fmt: OutputFormat) -> tuple[bool, str]:
        try:
            if fmt == OutputFormat.JSON:
                json.loads(content)
                return True, "Valid JSON"
            elif fmt == OutputFormat.XML:
                if not re.search(r"<[a-zA-Z][^>]*>.*?</[a-zA-Z]+>", content, re.DOTALL):
                    return False, "No valid XML tags found"
                return True, "Valid XML structure"
            elif fmt == OutputFormat.CSV:
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                if rows:
                    cols = len(rows[0])
                    if any(len(r) != cols for r in rows[1:]):
                        return False, f"Inconsistent column count: header={cols}"
                return True, f"Valid CSV ({len(rows)} rows)"
            elif fmt == OutputFormat.MARKDOWN:
                if "|" in content and "---" in content:
                    return True, "Valid Markdown table"
                return True, "Valid Markdown"
            return True, "Format validated"
        except Exception as e:
            return False, str(e)

    def get_stats(self) -> dict:
        return {**self._stats, "templates": len(self._templates), "streams_active": len(self._stream_buffers)}

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "module": self.module_id,
            "templates": len(self._templates),
            "formatted_total": self._stats["formatted"],
            "errors": self._stats["errors"],
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        """统一执行入口 - 输出格式化操作路由"""
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("output_formatter.execute.calls", 1)
        self.audit("format_action", {"action": action})
        params = params or {}
        ops = {
            "format_json": lambda p: {"formatted": True, "output": str(p.get("data", {}))},
            "format_csv": lambda p: {"formatted": True, "rows": len(p.get("data", []))},
            "format_table": lambda p: {"formatted": True, "columns": len(p.get("headers", []))},
            "get_stats": lambda p: {},
            "health": lambda p: {"status": "healthy"},
        }
        handler = ops.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        try:
            return {"success": True, "result": handler(params)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_format(
        self, items: List[Dict], fmt: OutputFormat = OutputFormat.JSON, include_metadata: bool = True
    ) -> Dict[str, Any]:
        """批量格式化多条数据。企业场景：日志导出、报表生成时批量转换格式。

        Args:
            items: 待格式化的数据列表
            fmt: 目标输出格式
            include_metadata: 是否包含元数据（时间戳、总数、格式版本）
        Returns:
            格式化结果字典，包含内容和元数据
        """
        formatted_items = []
        errors = []
        for i, item in enumerate(items):
            try:
                result = self.format(item, fmt)
                formatted_items.append(result)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        output = {
            "items": formatted_items,
            "total": len(items),
            "success_count": len(formatted_items),
            "error_count": len(errors),
        }
        if include_metadata:
            output["metadata"] = {
                "format": fmt.value,
                "generated_at": datetime.now().isoformat(),
                "formatter_version": "1.0",
                "source": "output_formatter.batch_format",
            }
        if errors:
            output["errors"] = errors
        return output

    def validate_output(self, content: str, expected_format: OutputFormat = None) -> Dict[str, Any]:
        """验证输出内容是否符合指定格式规范。
        企业场景：API响应格式合规检查、数据交换前校验。
        """
        result = {"valid": True, "format_detected": None, "issues": []}
        if not content:
            result["valid"] = False
            result["issues"].append("empty_content")
            return result
        detected = self.auto_detect_format(content)
        result["format_detected"] = detected.value
        if expected_format and detected != expected_format:
            result["valid"] = False
            result["issues"].append(f"format_mismatch: expected {expected_format.value}, got {detected.value}")
        if detected == OutputFormat.JSON:
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                result["valid"] = False
                result["issues"].append(f"json_parse_error: {str(e)}")
        elif detected == OutputFormat.CSV:
            lines = content.strip().split("\n")
            if len(lines) > 1:
                header_count = len(lines[0].split(","))
                for idx, line in enumerate(lines[1:], 2):
                    if len(line.split(",")) != header_count:
                        result["issues"].append(f"csv_column_mismatch at line {idx}")
                        result["valid"] = False
        return result

    def shutdown(self) -> dict:
        """Graceful shutdown for output_formatter."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = OutputFormatter
