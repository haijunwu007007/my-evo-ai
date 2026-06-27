"""文档生成技能 — 生成 docx/md/txt"""
import os, subprocess, tempfile, json
from pathlib import Path

skill_def = {
    "name": "document-generator",
    "version": "1.0.0",
    "description": "生成 Word/文字/排版文档",
    "author": "AUTO-EVO-AI",
    "category": "文件生成", "icon": "📝",
    "tags": ["文档", "合同", "方案", "报告", "Word"],
    "input_schema": {"type": "object", "properties": {"content": {"type": "string"}, "format": {"type": "string", "enum": ["docx", "md", "txt"]}}},
    "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}}
}

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "documents"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def execute(params, context=None):
    content = params.get("content", "")
    fmt = params.get("format", "md")
    if not content:
        return {"file_path": "", "error": "请提供文档内容（content）"}
    import hashlib
    name = hashlib.md5(content.encode()).hexdigest()[:12]
    if fmt == "docx":
        try:
            from docx import Document
            doc = Document()
            for line in content.split("\n"):
                p = doc.add_paragraph(line.strip())
            fp = str(OUT_DIR / f"{name}.docx")
            doc.save(fp)
            return {"file_path": fp}
        except ImportError:
            fmt = "md"
    fp = str(OUT_DIR / f"{name}.{fmt}")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    return {"file_path": fp}
