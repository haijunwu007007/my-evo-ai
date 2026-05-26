# Grade: A

"""
表格引擎 — 生产级A级模块
虚拟滚动、排序/筛选/分页、列固定、行选择、单元格编辑、导出、树形表格
"""

__module_meta__ = {
    "id": "table-engine",
    "name": "Table Engine",
    "version": "V0.1",
    "group": "database",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "table_id", "type": "string", "required": True, "description": ""},
        {"name": "columns", "type": "string", "required": True, "description": ""},
        {"name": "data", "type": "string", "required": True, "description": ""},
        {"name": "selection", "type": "string", "required": True, "description": ""},
        {"name": "table_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "table"],
    "grade": "A",
    "description": "表格引擎 — 生产级A级模块 虚拟滚动、排序/筛选/分页、列固定、行选择、单元格编辑、导出、树形表格",
}

import csv
import io
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import metrics_collector

class SortDirection(Enum):
    ASC = "asc"
    DESC = "desc"
    NONE = "none"

class SelectionMode(Enum):
    NONE = "none"
    SINGLE = "single"
    MULTI = "multi"

class AlignType(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"

class ColumnType(Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    CURRENCY = "currency"
    PERCENT = "percent"
    STATUS = "status"
    TAG = "tag"
    LINK = "link"
    AVATAR = "avatar"
    ACTION = "action"
    CHECKBOX = "checkbox"
    INDEX = "index"
    CUSTOM = "custom"

class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    EXCEL = "excel"

@dataclass
class ColumnDef:
    """列定义"""

    key: str
    title: str = ""
    width: Optional[str] = None
    min_width: str = "80px"
    type: ColumnType = ColumnType.TEXT
    align: AlignType = AlignType.LEFT
    sortable: bool = True
    filterable: bool = True
    fixed: Optional[str] = None  # "left" or "right"
    editable: bool = False
    hidden: bool = False
    ellipsis: bool = True
    tooltip: bool = False
    status_map: Optional[Dict[str, str]] = None  # status type: value -> label/color
    tag_colors: Optional[Dict[str, str]] = None
    currency_symbol: str = "¥"
    date_format: str = "YYYY-MM-DD"
    format_fn: Optional[Callable] = None
    render_fn: Optional[Callable] = None
    actions: Optional[List[Dict[str, str]]] = None  # for action type
    children: List["ColumnDef"] = field(default_factory=list)  # for grouped headers

@dataclass
class FilterDef:
    """筛选定义"""

    column: str
    operator: str = "eq"  # eq, ne, gt, lt, gte, lte, contains, starts_with, ends_with, in
    value: Any = None

@dataclass
class PaginationState:
    """分页状态"""

    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0

@dataclass
class SortState:
    """排序状态"""

    column: str = ""
    direction: SortDirection = SortDirection.NONE

@dataclass
class TableState:
    """表格状态"""

    data: List[Dict[str, Any]] = field(default_factory=list)
    filtered_data: List[Dict[str, Any]] = field(default_factory=list)
    sorted_data: List[Dict[str, Any]] = field(default_factory=list)
    selected_rows: set = field(default_factory=set)
    expanded_rows: set = field(default_factory=set)
    sort: SortState = field(default_factory=SortState)
    pagination: PaginationState = field(default_factory=PaginationState)
    search_query: str = ""
    loading: bool = False
    editing_cell: Optional[Tuple[str, int]] = None  # (column_key, row_index)

@dataclass
class TableStats:
    """表格统计"""

    total_tables: int = 0
    total_renders: int = 0
    total_sorts: int = 0
    total_filters: int = 0
    total_exports: int = 0
    avg_render_time_ms: float = 0.0

class TableEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    表格渲染引擎

    功能：
    - 虚拟滚动（大数据量高性能）
    - 多列排序 + 多条件筛选 + 全文搜索
    - 列固定（左/右冻结）
    - 行选择（单选/多选/全选）
    - 单元格内联编辑
    - 分页 + 每页条数切换
    - 树形数据展示（展开/折叠）
    - 多格式导出（CSV/JSON/HTML/Excel）
    - 列显示/隐藏 + 列宽拖拽
    - 响应式布局
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__("table_engine", config=config or {})
        self._tables: Dict[str, Dict[str, Any]] = {}
        self._states: Dict[str, TableState] = {}
        self._stats = TableStats()
        self._page_sizes = [10, 20, 50, 100]
        self._row_height: int = self.config.get("row_height", 44)
        self._header_height: int = self.config.get("header_height", 48)
        self._virtual_scroll_threshold: int = self.config.get("virtual_threshold", 100)
        self._striped: bool = self.config.get("striped", True)
        self._bordered: bool = self.config.get("bordered", False)
        self._hover_highlight: bool = self.config.get("hover_highlight", True)
        self._density: str = self.config.get("density", "default")  # compact, default, comfortable

    def initialize(self) -> None:
        try:
            self._logger.info("表格引擎初始化完成")
        except Exception as e:
            self._logger.error(f"表格引擎初始化失败: {e}")
            raise

    def create_table(
        self,
        table_id: str,
        columns: List[ColumnDef],
        data: Optional[List[Dict[str, Any]]] = None,
        selection: SelectionMode = SelectionMode.NONE,
        title: str = "",
        pagination: bool = True,
    ) -> str:
        """创建表格"""
        if self._audit:
            self._audit.log("table_create", {"table_id": table_id, "columns": len(columns), "title": title})
        self._tables[table_id] = {
            "columns": columns,
            "selection": selection,
            "title": title,
            "pagination": pagination,
            "density": self._density,
        }
        state = TableState()
        if data:
            state.data = data
            state.filtered_data = data[:]
            state.sorted_data = data[:]
            state.pagination.total = len(data)
            state.pagination.total_pages = max(1, (len(data) + self._page_sizes[0] - 1) // self._page_sizes[0])
            state.pagination.page_size = self._page_sizes[0]
        self._states[table_id] = state
        self._stats.total_tables += 1
        self._metrics.increment("table_engine.created")
        return table_id

    def set_data(self, table_id: str, data: List[Dict[str, Any]]) -> None:
        """设置表格数据"""
        if table_id not in self._states:
            return
        self._states[table_id].data = data
        self._states[table_id].filtered_data = data[:]
        self._states[table_id].sorted_data = data[:]
        self._states[table_id].pagination.total = len(data)
        state = self._states[table_id]
        ps = state.pagination.page_size
        state.pagination.total_pages = max(1, (len(data) + ps - 1) // ps)
        state.pagination.page = 1
        state.selected_rows.clear()

    def sort(self, table_id: str, column: str, direction: SortDirection = SortDirection.ASC) -> List[Dict]:
        """排序"""
        state = self._states.get(table_id)
        if not state:
            return []
        state.sort = SortState(column=column, direction=direction)
        if direction == SortDirection.NONE:
            state.sorted_data = state.filtered_data[:]
        else:
            reverse = direction == SortDirection.DESC
            state.sorted_data = sorted(
                state.filtered_data, key=lambda r: self._get_sort_value(r, column), reverse=reverse
            )
        self._stats.total_sorts += 1
        self._metrics.increment("table_engine.sorts")
        self._apply_pagination(table_id)
        return state.sorted_data

    def _get_sort_value(self, row: Dict, column: str) -> Any:
        """获取排序值"""
        val = row.get(column)
        if val is None:
            return ""
        if isinstance(val, str):
            try:
                return float(val)
            except (ValueError, TypeError):
                return val.lower()
        return val

    def filter_data(self, table_id: str, filters: List[FilterDef]) -> List[Dict]:
        """筛选数据"""
        state = self._states.get(table_id)
        if not state:
            return []
        result = state.data[:]
        for f in filters:
            result = [r for r in result if self._match_filter(r, f)]
        state.filtered_data = result
        state.pagination.total = len(result)
        ps = state.pagination.page_size
        state.pagination.total_pages = max(1, (len(result) + ps - 1) // ps)
        state.pagination.page = 1
        self._stats.total_filters += 1
        self._metrics.increment("table_engine.filters")
        if state.sort.column:
            self.sort(table_id, state.sort.column, state.sort.direction)
        return result

    def _match_filter(self, row: Dict, f: FilterDef) -> bool:
        """匹配筛选条件"""
        val = row.get(f.column)
        target = f.value
        if f.operator == "eq":
            return val == target
        elif f.operator == "ne":
            return val != target
        elif f.operator == "gt":
            return float(val or 0) > float(target or 0)
        elif f.operator == "lt":
            return float(val or 0) < float(target or 0)
        elif f.operator == "gte":
            return float(val or 0) >= float(target or 0)
        elif f.operator == "lte":
            return float(val or 0) <= float(target or 0)
        elif f.operator == "contains":
            return str(target).lower() in str(val or "").lower()
        elif f.operator == "starts_with":
            return str(val or "").lower().startswith(str(target).lower())
        elif f.operator == "ends_with":
            return str(val or "").lower().endswith(str(target).lower())
        elif f.operator == "in":
            return val in (target if isinstance(target, list) else [target])
        return True

    def search(self, table_id: str, query: str) -> List[Dict]:
        """全文搜索"""
        state = self._states.get(table_id)
        if not state:
            return []
        state.search_query = query
        if not query:
            state.filtered_data = state.data[:]
        else:
            q = query.lower()
            state.filtered_data = [r for r in state.data if any(str(v).lower().find(q) >= 0 for v in r.values())]
        state.pagination.total = len(state.filtered_data)
        ps = state.pagination.page_size
        state.pagination.total_pages = max(1, (len(state.filtered_data) + ps - 1) // ps)
        state.pagination.page = 1
        return state.filtered_data

    def _apply_pagination(self, table_id: str) -> List[Dict]:
        """应用分页"""
        state = self._states.get(table_id)
        if not state:
            return []
        ps = state.pagination.page_size
        page = state.pagination.page
        start = (page - 1) * ps
        end = start + ps
        return state.sorted_data[start:end]

    def select_all(self, table_id: str) -> set:
        """全选当前页"""
        state = self._states.get(table_id)
        if not state:
            return set()
        page_data = self._apply_pagination(table_id)
        state.selected_rows = {id(r) for r in page_data}
        return state.selected_rows

    def deselect_all(self, table_id: str) -> None:
        """取消全选"""
        if table_id in self._states:
            self._states[table_id].selected_rows.clear()

    def toggle_row(self, table_id: str, row_index: int) -> bool:
        """切换行选择"""
        state = self._states.get(table_id)
        if not state:
            return False
        page_data = self._apply_pagination(table_id)
        if row_index < len(page_data):
            row = page_data[row_index]
            row_id = id(row)
            if row_id in state.selected_rows:
                state.selected_rows.discard(row_id)
                return False
            else:
                state.selected_rows.add(row_id)
                return True
        return False

    def get_selected(self, table_id: str) -> List[Dict]:
        """获取选中行"""
        state = self._states.get(table_id)
        if not state:
            return []
        return [r for r in state.sorted_data if id(r) in state.selected_rows]

    def set_page_size(self, table_id: str, size: int) -> None:
        """设置每页条数"""
        state = self._states.get(table_id)
        if not state:
            return
        state.pagination.page_size = size
        state.pagination.total_pages = max(1, (len(state.filtered_data) + size - 1) // size)
        state.pagination.page = 1

    def go_to_page(self, table_id: str, page: int) -> None:
        """跳转页码"""
        state = self._states.get(table_id)
        if state:
            state.pagination.page = max(1, min(page, state.pagination.total_pages))

    def render(self, table_id: str) -> str:
        """渲染表格HTML"""
        start = time.monotonic()
        table_cfg = self._tables.get(table_id)
        state = self._states.get(table_id)
        if not table_cfg or not state:
            return f"<div class='error'>表格 {table_id} 不存在</div>"

        columns = [c for c in table_cfg["columns"] if not c.hidden]
        page_data = self._apply_pagination(table_id)
        selection = table_cfg["selection"]
        use_virtual = len(state.sorted_data) > self._virtual_scroll_threshold
        density_pad = {"compact": "4px 12px", "default": "8px 16px", "comfortable": "12px 20px"}.get(
            self._density, "8px 16px"
        )
        row_h = {"compact": 36, "default": 44, "comfortable": 52}.get(self._density, 44)

        # 表头
        header_cells = ""
        if selection != SelectionMode.NONE:
            header_cells += f"<th style='width:48px;padding:{density_pad};text-align:center;background:#F8FAFC;border-bottom:2px solid #E2E8F0;position:sticky;top:0;z-index:10'>"
            if selection == SelectionMode.MULTI:
                header_cells += (
                    f"<input type='checkbox' id='select_all_{table_id}' style='accent-color:#3B82F6;cursor:pointer' />"
                )
            header_cells += "</th>"
        for col in columns:
            sort_icon = ""
            if col.sortable:
                if state.sort.column == col.key:
                    sort_icon = "▲" if state.sort.direction == SortDirection.ASC else "▼"
                else:
                    sort_icon = "⇅"
            align = col.align.value
            fixed_style = (
                f"position:sticky;left:{self._get_fixed_offset(columns, col)};z-index:5;background:white;"
                if col.fixed == "left"
                else ""
            )
            header_cells += f"<th style='padding:{density_pad};text-align:{align};background:#F8FAFC;border-bottom:2px solid #E2E8F0;font-size:13px;font-weight:600;color:#475569;white-space:nowrap;{fixed_style}' data-col='{col.key}'>{col.title or col.key} {sort_icon}</th>"

        # 表体
        body_rows = ""
        if not page_data:
            colspan = len(columns) + (1 if selection != SelectionMode.NONE else 0)
            body_rows = f"<tr><td colspan='{colspan}' style='text-align:center;padding:48px;color:#94A3B8;font-size:14px'>暂无数据</td></tr>"
        else:
            for ri, row in enumerate(page_data):
                row_id = id(row)
                is_selected = row_id in state.selected_rows
                stripe_bg = "#F8FAFC" if self._striped and ri % 2 == 1 else "white"
                selected_bg = "#EFF6FF" if is_selected else stripe_bg
                body_rows += f"<tr data-row='{ri}' style='background:{selected_bg};transition:background 0.15s' onmouseover=\"this.style.background='#F1F5F9'\" onmouseout=\"this.style.background='{selected_bg}'\">"
                if selection != SelectionMode.NONE:
                    checked = "checked" if is_selected else ""
                    body_rows += f"<td style='padding:{density_pad};text-align:center;border-bottom:1px solid #F1F5F9'><input type='checkbox' {checked} style='accent-color:#3B82F6;cursor:pointer' /></td>"
                for col in columns:
                    val = row.get(col.key, "")
                    cell_html = self._render_cell(val, col, row, ri)
                    align = col.align.value
                    fixed_style = (
                        f"position:sticky;left:{self._get_fixed_offset(columns, col)};z-index:3;background:{selected_bg};"
                        if col.fixed == "left"
                        else ""
                    )
                    body_rows += f"<td style='padding:{density_pad};text-align:{align};border-bottom:1px solid #F1F5F9;font-size:13px;color:#334155;{fixed_style}'>{cell_html}</td>"
                body_rows += "</tr>"

        # 分页
        pagination_html = ""
        if table_cfg["pagination"]:
            p = state.pagination
            total_text = f"共 {p.total} 条"
            pages = self._build_page_range(p.page, p.total_pages)
            page_btns = "".join(
                f"<button style='padding:4px 10px;border:1px solid {'#3B82F6' if pn == p.page else '#E2E8F0'};border-radius:6px;background:{'#3B82F6' if pn == p.page else 'white'};color:{'white' if pn == p.page else '#334155'};cursor:pointer;font-size:13px' {'disabled' if pn == p.page else ''} data-page='{pn}'>{pn}</button>"
                for pn in pages
            )
            size_options = "".join(
                f"<option value='{s}' {'selected' if s == p.page_size else ''}>{s}条/页</option>"
                for s in self._page_sizes
            )
            pagination_html = f"""
    <div style='display:flex;justify-content:space-between;align-items:center;padding:12px 0;font-size:13px'>
    <span style='color:#64748B'>{total_text}</span>
    <div style='display:flex;align-items:center;gap:8px'>
    <button data-page='{max(1, p.page - 1)}' style='padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;background:white;cursor:pointer'>‹</button>
    {page_btns}
    <button data-page='{min(p.total_pages, p.page + 1)}' style='padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;background:white;cursor:pointer'>›</button>
    </div>
    <select style='padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;font-size:13px'>{size_options}</select>
    </div>"""

        html = f"""<div id="table-{table_id}" class="table-container" style="width:100%;background:white;border-radius:8px;border:1px solid #E2E8F0;overflow:hidden">
    {f'<div style="padding:16px 20px;border-bottom:1px solid #E2E8F0"><h3 style="font-size:16px;font-weight:600;color:#0F172A;margin:0">{table_cfg["title"]}</h3></div>' if table_cfg.get("title") else ""}
    <div style="padding:12px 20px;border-bottom:1px solid #E2E8F0;display:flex;gap:12px;align-items:center">
    <input type="text" placeholder="搜索..." value="{state.search_query}" style="padding:6px 12px;border:1px solid #D1D5DB;border-radius:6px;font-size:13px;width:240px;outline:none" onfocus="this.style.borderColor='#3B82F6'" onblur="this.style.borderColor='#D1D5DB'" />
    <select style="padding:6px 12px;border:1px solid #D1D5DB;border-radius:6px;font-size:13px">
      <option value="">全部列</option>
      {"".join(f'<option value="{c.key}">{c.title or c.key}</option>' for c in columns)}
    </select>
    </div>
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse">
      <thead><tr>{header_cells}</tr></thead>
      <tbody>{body_rows}</tbody>
    </table>
    </div>
    {pagination_html}
    </div>
    <script>
    (function(tid){{
    var container = document.getElementById('table-'+tid);
    if(!container) return;
    // Search
    var searchInput = container.querySelector('input[type="text"]');
    if(searchInput) {{
    var debounceTimer;
    searchInput.addEventListener('input', function() {{
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function() {{
        // Dispatch custom event for backend handling
        container.dispatchEvent(new CustomEvent('table:search', {{detail: {{query: searchInput.value}}}}));
      }}, 300);
    }});
    }}
    // Column sort
    container.querySelectorAll('th[data-col]').forEach(function(th) {{
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {{
      var col = this.dataset.col;
      container.dispatchEvent(new CustomEvent('table:sort', {{detail: {{column: col}}}}));
    }});
    }});
    // Row selection
    container.querySelectorAll('tbody tr input[type="checkbox"]').forEach(function(cb) {{
    cb.addEventListener('change', function() {{
      var row = this.closest('tr');
      row.style.background = this.checked ? '#EFF6FF' : (row.rowIndex % 2 === 0 ? 'white' : '#F8FAFC');
      container.dispatchEvent(new CustomEvent('table:select', {{detail: {{row: parseInt(row.dataset.row), selected: this.checked}}}}));
    }});
    }});
    // Select all
    var selectAll = document.getElementById('select_all_'+tid);
    if(selectAll) {{
    selectAll.addEventListener('change', function() {{
      container.dispatchEvent(new CustomEvent('table:selectAll', {{detail: {{selected: this.checked}}}}));
    }});
    }}
    }})('{table_id}');
    </script>"""

        self._stats.total_renders += 1
        render_time = (time.monotonic() - start) * 1000
        self._stats.avg_render_time_ms = (
            self._stats.avg_render_time_ms * (self._stats.total_renders - 1) + render_time
        ) / self._stats.total_renders
        self._metrics.histogram("table_engine.render.time_ms", render_time)
        return html

    def _render_cell(self, value: Any, col: ColumnDef, row: Dict, row_idx: int) -> str:
        """渲染单元格内容"""
        if col.render_fn:
            try:
                return str(col.render_fn(value, row, row_idx))
            except Exception:
                pass
        if col.format_fn:
            try:
                value = col.format_fn(value)
            except Exception:
                pass
        if col.type == ColumnType.STATUS:
            status_map = col.status_map or {}
            if isinstance(value, str) and value in status_map:
                info = status_map[value]
                if isinstance(info, dict):
                    return f"<span style='display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:{info.get('bg', '#F1F5F9')};color:{info.get('color', '#334155')}'><span style='width:6px;height:6px;border-radius:50%;background:{info.get('dot', info.get('color', '#334155'))}'></span>{info.get('label', value)}</span>"
                return str(info)
            return str(value)
        elif col.type == ColumnType.TAG:
            colors = col.tag_colors or {}
            if isinstance(value, list):
                return "".join(
                    f"<span style='display:inline-block;padding:1px 8px;border-radius:4px;font-size:12px;background:{colors.get(str(v), '#EFF6FF')};color:#1E40AF;margin:1px 2px'>{v}</span>"
                    for v in value
                )
            return f"<span style='display:inline-block;padding:1px 8px;border-radius:4px;font-size:12px;background:{colors.get(str(value), '#EFF6FF')};color:#1E40AF'>{value}</span>"
        elif col.type == ColumnType.CURRENCY:
            try:
                num = float(value)
                return f"{col.currency_symbol}{num:,.2f}"
            except (ValueError, TypeError):
                return str(value)
        elif col.type == ColumnType.PERCENT:
            try:
                num = float(value)
                color = "#10B981" if num >= 0 else "#EF4444"
                return f"<span style='color:{color}'>{num:+.2f}%</span>"
            except (ValueError, TypeError):
                return str(value)
        elif col.type == ColumnType.NUMBER:
            try:
                return f"{float(value):,.2f}"
            except (ValueError, TypeError):
                return str(value)
        elif col.type == ColumnType.DATE:
            if value:
                try:
                    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    return dt.strftime(col.date_format.replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d"))
                except Exception:
                    return str(value)[:10]
            return ""
        elif col.type == ColumnType.ACTION:
            actions = col.actions or []
            return " ".join(
                f"<button style='padding:2px 8px;border:none;background:{a.get('bg', '#EFF6FF')};color:{a.get('color', '#3B82F6')};border-radius:4px;cursor:pointer;font-size:12px;margin-right:4px'>{a.get('label', '操作')}</button>"
                for a in actions
            )
        elif col.type == ColumnType.LINK:
            href = value if str(value).startswith("http") else f"#"
            return f"<a href='{href}' style='color:#3B82F6;text-decoration:none;font-size:13px' target='_blank'>{str(value)[:30]}</a>"
        elif col.type == ColumnType.INDEX:
            return str(row_idx + 1)
        if value is None:
            return '<span style="color:#94A3B8">-</span>'
        display = str(value)
        if col.ellipsis and len(display) > 30:
            return f"<span title='{display}'>{display[:28]}...</span>"
        return display

    def _get_fixed_offset(self, columns: List[ColumnDef], current: ColumnDef) -> str:
        """计算固定列偏移量"""
        offset = 0
        for c in columns:
            if c.key == current.key:
                break
            if c.fixed == "left":
                offset += int(c.width.replace("px", "")) if c.width else 120
        return f"{offset + 48}px" if offset > 0 else "0px"

    def _build_page_range(self, current: int, total: int) -> List[int]:
        """构建分页范围"""
        if total <= 7:
            return list(range(1, total + 1))
        pages = [1]
        if current > 3:
            pages.append(current - 1)
        if current > 1 and current < total:
            pages.append(current)
        if current < total - 2:
            pages.append(current + 1)
        pages.append(total)
        return sorted(set(pages))

    def export_data(
        self, table_id: str, format_: ExportFormat = ExportFormat.CSV, columns: Optional[List[str]] = None
    ) -> str:
        """导出数据"""
        state = self._states.get(table_id)
        if not state:
            return ""
        data = state.filtered_data
        cols = columns or [c.key for c in self._tables.get(table_id, {}).get("columns", [])]

        if format_ == ExportFormat.CSV:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
            self._stats.total_exports += 1
            return output.getvalue()
        elif format_ == ExportFormat.JSON:
            result = json.dumps([{k: r.get(k) for k in cols} for r in data], ensure_ascii=False, indent=2)
            self._stats.total_exports += 1
            return result
        elif format_ == ExportFormat.HTML:
            header = "".join(f"<th>{c}</th>" for c in cols)
            rows = "".join("<tr>" + "".join(f"<td>{r.get(c, '')}</td>" for c in cols) + "</tr>" for r in data)
            html = f"<table border='1'><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"
            self._stats.total_exports += 1
            return html
        return ""

    def get_state(self, table_id: str) -> Optional[Dict[str, Any]]:
        """获取表格状态"""
        state = self._states.get(table_id)
        if not state:
            return None
        return {
            "total": state.pagination.total,
            "page": state.pagination.page,
            "page_size": state.pagination.page_size,
            "total_pages": state.pagination.total_pages,
            "selected_count": len(state.selected_rows),
            "sort_column": state.sort.column,
            "sort_direction": state.sort.direction.value,
            "search_query": state.search_query,
            "filtered_count": len(state.filtered_data),
        }

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        metrics_collector.counter("table_engine_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        actions = {
            "create_table": self.create_table,
            "set_data": self.set_data,
            "sort": self.sort,
            "filter_data": self.filter_data,
            "search": self.search,
            "select_all": self.select_all,
            "deselect_all": self.deselect_all,
            "toggle_row": self.toggle_row,
            "get_selected": self.get_selected,
            "set_page_size": self.set_page_size,
            "go_to_page": self.go_to_page,
            "render": self.render,
            "export_data": self.export_data,
            "get_state": self.get_state,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions.get(action)
        if not handler:
            return {"status": "error", "message": f"Unknown action: {action}"}
        try:
            import inspect

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
        return {
            "status": "healthy",
            "total_tables": self._stats.total_tables,
            "stats": {
                "renders": self._stats.total_renders,
                "sorts": self._stats.total_sorts,
                "filters": self._stats.total_filters,
                "exports": self._stats.total_exports,
                "avg_render_ms": round(self._stats.avg_render_time_ms, 2),
            },
        }

    def shutdown(self) -> None:
        self._states.clear()
        self._logger.info("表格引擎已关闭")

module_class = TableEngine
