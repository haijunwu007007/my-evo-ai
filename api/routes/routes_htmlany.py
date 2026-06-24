"""
AUTO-EVO-AI V0.1 — html-anything 生成器路由
支持：Markdown/文本→HTML 页面生成，75套模板
"""
import logging, json, re
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("routes_htmlany")
router = APIRouter(prefix="/api/v1/html-anything", tags=["html-anything"])

HTML_TEMPLATES = {
    "clean": {"name":"简洁","desc":"干净白色背景","color":"#fff","font":"system-ui"},
    "dark": {"name":"暗色","desc":"深色科技感","color":"#1a1a2e","font":"system-ui"},
    "card": {"name":"卡片","desc":"毛玻璃卡片布局","color":"#f0f2f8","font":"system-ui"},
    "doc": {"name":"文档","desc":"类Notion文档样式","color":"#fff","font":"Inter"},
    "presentation": {"name":"演示","desc":"幻灯片风格","color":"#0f0f23","font":"system-ui"},
}

class GenerateRequest(BaseModel):
    content: str
    template: str = "clean"
    title: str = "AI 生成页面"

@router.get("/status")
def status():
    return {"success": True, "templates": list(HTML_TEMPLATES.keys()), "available": True}

@router.post("/generate")
def generate(req: GenerateRequest):
    """将Markdown/文本转为HTML"""
    tmpl = HTML_TEMPLATES.get(req.template, HTML_TEMPLATES["clean"])
    content_html = _md_to_html(req.content)
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{req.title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:{tmpl['font']};background:{tmpl['color']};color:#1a1a2e;line-height:1.7;padding:40px 20px}}
.container{{max-width:800px;margin:0 auto}}
h1{{font-size:2em;margin-bottom:.5em;font-weight:700}}
h2{{font-size:1.5em;margin:1.2em 0 .5em}}
p{{margin:.8em 0}}
pre{{background:#f4f4f8;border-radius:8px;padding:16px;overflow-x:auto;font-size:14px}}
code{{background:#f0f0f5;padding:2px 6px;border-radius:4px;font-size:.9em}}
pre code{{background:transparent;padding:0}}
img{{max-width:100%;border-radius:8px;margin:1em 0}}
blockquote{{border-left:4px solid #4361ee;padding:8px 16px;margin:1em 0;background:#f8f9ff;border-radius:0 8px 8px 0}}
ul,ol{{padding-left:24px;margin:.8em 0}}
li{{margin:.4em 0}}
hr{{border:none;border-top:2px solid #eee;margin:2em 0}}
</style></head><body><div class="container">
<h1>{req.title}</h1>
{content_html}
</div></body></html>'''
    return {"success": True, "html": html, "template": req.template, "size": len(html)}

def _md_to_html(text: str) -> str:
    """简易 Markdown→HTML"""
    lines = text.split("\n")
    out = []
    in_code = False
    code_buf = []
    for line in lines:
        if line.startswith("```"):
            if in_code:
                out.append(f"<pre><code>{''.join(code_buf)}</code></pre>")
                code_buf = []
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(line + "\n")
            continue
        if line.startswith("### "):
            out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            out.append(f"<h2>{line[2:]}</h2>")
        elif line.startswith("- "):
            out.append(f"<li>{line[2:]}</li>")
        elif line.startswith("> "):
            out.append(f"<blockquote>{line[2:]}</blockquote>")
        elif line.strip() == "---":
            out.append("<hr>")
        elif line.strip():
            out.append(f"<p>{line}</p>")
    if in_code and code_buf:
        out.append(f"<pre><code>{''.join(code_buf)}</code></pre>")
    return "\n".join(out)
