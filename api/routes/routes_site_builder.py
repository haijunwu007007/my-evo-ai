"""
AUTO-EVO-AI V0.1 — 一键建站路由
描述→AI生成HTML→上线
"""
from fastapi import APIRouter
from pydantic import BaseModel
import json, time, os
from pathlib import Path

router = APIRouter(prefix="/api/v1/site-builder", tags=["site-builder"])
SITES_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "sites"
SITES_DIR.mkdir(parents=True, exist_ok=True)

class GenRequest(BaseModel):
    description: str
    template: str = "landing"

@router.post("/generate")
async def generate_site(req: GenRequest):
    try:
        from api.agent_llm import call_llm
        tpl_configs = {"landing": "现代风格落地页，有导航/英雄区/功能/定价/联系表单",
                       "blog": "博客风格，有文章列表/分类/标签/侧边栏",
                       "business": "企业官网风格，有公司介绍/服务/案例/联系我们",
                       "portfolio": "作品集风格，有个人介绍/作品网格/技能/联系"}
        tpl_desc = tpl_configs.get(req.template, "落地页")
        prompt = f"""根据以下描述生成一个完整的单页HTML网站：
描述：{req.description}
风格：{tpl_desc}
要求：
- 完整HTML文档（含<!DOCTYPE html>）
- 内联CSS（现代美观设计）
- 响应式布局
- 使用中文
- 专业配色
只返回HTML代码，不要其他文字。"""
        r, _ = call_llm([{"role":"user","content":prompt}], None, "")
        html = r or "<html><body><h1>生成失败</h1></body></html>"
        # 提取HTML
        if "```html" in html:
            html = html.split("```html")[1].split("```")[0]
        elif "```" in html:
            html = html.split("```")[1].split("```")[0]
        # 保存
        name = f"site_{int(time.time())}"
        fp = SITES_DIR / f"{name}.html"
        fp.write_text(html, encoding="utf-8")
        return {"success": True, "html": html[:500], "url": f"/output/sites/{name}.html", "file": name}
    except Exception as e:
        return {"success": False, "error": str(e)}
