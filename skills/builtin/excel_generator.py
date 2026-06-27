"""Excel 生成技能 — openpyxl"""
from pathlib import Path

skill_def = {
    "name": "excel-generator", "version": "1.0.0",
    "description": "Excel 表格生成",
    "author": "AUTO-EVO-AI", "category": "文件生成", "icon": "📗",
    "tags": ["Excel", "表格", "数据"],
    "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "headers": {"type": "array"}, "data": {"type": "array"}}},
    "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}}
}

OUT = Path(__file__).resolve().parent.parent.parent / "output" / "excel"
OUT.mkdir(parents=True, exist_ok=True)

def execute(params, context=None):
    title = params.get("title", "表格")
    headers = params.get("headers", [])
    data = params.get("data", [])
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = title[:31]
        if headers:
            ws.append(headers)
        for row in data:
            ws.append(row if isinstance(row, (list, tuple)) else [row])
        fp = str(OUT / f"{title.replace(' ', '_')[:20]}.xlsx")
        wb.save(fp)
        return {"file_path": fp}
    except ImportError:
        return {"file_path": "", "error": "openpyxl 未安装"}
    except Exception as e:
        return {"file_path": "", "error": f"Excel 生成失败：{e}"}
