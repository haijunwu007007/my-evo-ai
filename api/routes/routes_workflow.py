"""AUTO-EVO-AI V0.1 — 全自动工作流路由（n8n模板集成版）"""
import logging, json, httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("workflow")
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

try:
    from modules.workflow_engine import WorkflowEngine
    _engine = WorkflowEngine()
except Exception as e:
    _engine = None
    logger.warning(f"工作流引擎加载失败: {e}")

# ── n8n 模板市场 ──────────────────────────
N8N_API = "https://api.n8n.io/api"

@router.get("/templates/search")
async def search_templates(q: str = "", category: str = "", limit: int = 20):
    """从 n8n 官方模板库搜索工作流模板"""
    url = f"{N8N_API}/templates/search"
    params = {"limit": limit}
    if q: params["search"] = q
    if category: params["category"] = category
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                templates = data.get("workflows", data.get("data", [])) if isinstance(data, dict) else data
                return {"success": True, "templates": templates[:limit], "total": len(templates), "source": "n8n"}
            return {"success": False, "error": f"n8n API 返回 {r.status_code}"}
    except Exception as e:
        # 兜底：返回内置模板列表
        return await _builtin_templates(q, limit)

@router.get("/templates/categories")
async def list_categories():
    """获取 n8n 模板分类"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{N8N_API}/templates/categories")
            return {"success": True, "categories": r.json() if r.status_code == 200 else _DEFAULT_CATS}
    except Exception:
        return {"success": True, "categories": _DEFAULT_CATS}

@router.get("/templates/{template_id}")
async def get_template(template_id: int):
    """获取单个 n8n 模板详情"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{N8N_API}/templates/{template_id}")
            if r.status_code == 200:
                return {"success": True, "template": r.json()}
    except Exception:
        pass
    # 本地兜底
    for t in _BUILTIN_TEMPLATES:
        if t.get("id") == template_id:
            return {"success": True, "template": t}
    raise HTTPException(404, "模板未找到")

@router.post("/templates/install")
async def install_template(template_id: int = 0, workflow_json: str = ""):
    """安装工作流模板到本地引擎"""
    workflow_data = None
    if workflow_json:
        try:
            workflow_data = json.loads(workflow_json)
        except json.JSONDecodeError:
            return {"success": False, "error": "无效的 workflow JSON"}
    elif template_id:
        # 尝试从 n8n 获取
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{N8N_API}/templates/{template_id}")
                if r.status_code == 200:
                    workflow_data = r.json()
        except Exception:
            for t in _BUILTIN_TEMPLATES:
                if t.get("id") == template_id:
                    workflow_data = t
                    break
    if not workflow_data:
        return {"success": False, "error": "无法获取模板数据"}
    if _engine:
        try:
            result = _engine.create_workflow(
                f"wf_{template_id}" if template_id else f"wf_imported_{abs(hash(workflow_json)) % 10000}",
                workflow_data.get("name", "导入的工作流"),
                workflow_data.get("trigger", "manual"),
                workflow_data.get("steps", workflow_data.get("nodes", [])),
                workflow_data.get("description", "")
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": f"安装失败: {e}"}
    return {"success": False, "error": "工作流引擎未加载"}

_DEFAULT_CATS = [
    {"id": "communication", "name": "通信", "icon": "💬"},
    {"id": "data", "name": "数据", "icon": "📊"},
    {"id": "development", "name": "开发", "icon": "💻"},
    {"id": "marketing", "name": "营销", "icon": "📢"},
    {"id": "productivity", "name": "生产力", "icon": "⚡"},
    {"id": "sales", "name": "销售", "icon": "💰"},
    {"id": "ai", "name": "AI", "icon": "🤖"},
]

# ── 内置 30 个精选模板（n8n 风格）──
_BUILTIN_TEMPLATES = [
    {"id": 1, "name": "每日GitHub热门搜索", "category": "development",
     "description": "每天定时搜索 GitHub Trending 并推送总结到钉钉/Slack",
     "trigger": "schedule", "trigger_config": "0 9 * * *",
     "steps": [{"type": "github_trending", "params": {"language": "python", "limit": 10}},
               {"type": "llm_summarize", "params": {"lang": "zh-CN"}},
               {"type": "notify", "params": {"channel": "dingtalk"}}]},
    {"id": 2, "name": "自动生成日报", "category": "productivity",
     "description": "每天下班前自动汇总当天工作并生成日报文档",
     "trigger": "schedule", "trigger_config": "0 18 * * 1-5",
     "steps": [{"type": "collect_events", "params": {"source": "analytics", "period": "day"}},
               {"type": "llm_summarize", "params": {"lang": "zh-CN", "format": "report"}},
               {"type": "document_generate", "params": {"format": "md"}}]},
    {"id": 3, "name": "AI代码审查", "category": "development",
     "description": "Git Push 后自动审查代码变更",
     "trigger": "webhook", "trigger_config": "/webhook/github",
     "steps": [{"type": "code_review", "params": {"target": "commit"}},
               {"type": "llm_summarize", "params": {"lang": "zh-CN"}},
               {"type": "notify", "params": {"channel": "dingtalk"}}]},
    {"id": 4, "name": "每周行业动态报告", "category": "ai",
     "description": "每周一自动搜索行业动态并生成综合报告",
     "trigger": "schedule", "trigger_config": "0 9 * * 1",
     "steps": [{"type": "web_search", "params": {"query": "AI 最新动态", "count": 15}},
               {"type": "web_crawl", "params": {"depth": 1}},
               {"type": "llm_summarize", "params": {"format": "report", "lang": "zh-CN"}},
               {"type": "document_generate", "params": {"format": "docx"}}]},
    {"id": 5, "name": "自动备份到GitHub", "category": "development",
     "description": "每天定时自动备份项目代码到 GitHub",
     "trigger": "schedule", "trigger_config": "0 2 * * *",
     "steps": [{"type": "git_commit", "params": {"message": "auto backup"}},
               {"type": "git_push", "params": {"remote": "origin"}}]},
    {"id": 6, "name": "语音备忘录转文字", "category": "productivity",
     "description": "上传语音文件自动转文字并保存到笔记",
     "trigger": "webhook", "trigger_config": "/webhook/audio",
     "steps": [{"type": "speech_recognize", "params": {}},
               {"type": "llm_summarize", "params": {"lang": "zh-CN"}},
               {"type": "memory_save", "params": {"action": "save"}}]},
    {"id": 7, "name": "自动生成周报", "category": "productivity",
     "description": "每周五下午自动汇总生成周报PPT",
     "trigger": "schedule", "trigger_config": "0 16 * * 5",
     "steps": [{"type": "collect_events", "params": {"source": "analytics", "period": "week"}},
               {"type": "llm_summarize", "params": {"format": "ppt", "lang": "zh-CN"}},
               {"type": "ppt_generate", "params": {}}]},
    {"id": 8, "name": "网站变更监控", "category": "data",
     "description": "定时检查指定网页是否有更新，有变化时推送通知",
     "trigger": "schedule", "trigger_config": "0 */6 * * *",
     "steps": [{"type": "web_crawl", "params": {"url": ""}},
               {"type": "diff_compare", "params": {}},
               {"type": "notify", "params": {"channel": "email"}}]},
    {"id": 9, "name": "自动数据报表", "category": "data",
     "description": "每天自动从数据库生成销售/运营报表",
     "trigger": "schedule", "trigger_config": "0 8 * * *",
     "steps": [{"type": "db_query", "params": {"type": "sql"}},
               {"type": "chart_generate", "params": {}},
               {"type": "document_generate", "params": {"format": "pdf"}}]},
    {"id": 10, "name": "多语言自动翻译", "category": "ai",
     "description": "提交文档自动翻译成多国语言",
     "trigger": "webhook", "trigger_config": "/webhook/translate",
     "steps": [{"type": "document_read", "params": {}},
               {"type": "llm_translate", "params": {"target_langs": ["en", "ja", "ko"]}},
               {"type": "document_generate", "params": {"format": "docx"}}]},
    {"id": 11, "name": "社交媒体自动发布", "category": "marketing",
     "description": "生成内容后自动发布到多个社交平台",
     "trigger": "webhook", "trigger_config": "/webhook/social",
     "steps": [{"type": "llm_generate", "params": {"task": "social_media_post"}},
               {"type": "notify", "params": {"channel": "wechat"}},
               {"type": "notify", "params": {"channel": "telegram"}}]},
    {"id": 12, "name": "AI客服自动回复", "category": "ai",
     "description": "自动接收并回复用户咨询，复杂问题转人工",
     "trigger": "webhook", "trigger_config": "/webhook/chat",
     "steps": [{"type": "smart_chat", "params": {"mode": "auto"}},
               {"type": "llm_judge", "params": {"threshold": 0.8}},
               {"type": "notify", "params": {"channel": "dingtalk", "level": "urgent"}}]},
    {"id": 13, "name": "代码自动部署", "category": "development",
     "description": "代码合并到主分支后自动构建并部署",
     "trigger": "webhook", "trigger_config": "/webhook/github/pr",
     "steps": [{"type": "git_clone", "params": {}},
               {"type": "docker_build", "params": {}},
               {"type": "docker_deploy", "params": {"service": "app"}}]},
    {"id": 14, "name": "账单自动对账", "category": "data",
     "description": "每月自动核对账单和流水",
     "trigger": "schedule", "trigger_config": "0 9 1 * *",
     "steps": [{"type": "db_query", "params": {"type": "finance"}},
               {"type": "llm_analyze", "params": {"task": "reconciliation"}},
               {"type": "document_generate", "params": {"format": "xlsx"}}]},
    {"id": 15, "name": "竞争对手监控", "category": "marketing",
     "description": "监控竞争对手网站和社交媒体动态",
     "trigger": "schedule", "trigger_config": "0 */4 * * *",
     "steps": [{"type": "web_search", "params": {"count": 10}},
               {"type": "web_crawl", "params": {"depth": 1}},
               {"type": "llm_analyze", "params": {"task": "competitive_analysis"}},
               {"type": "notify", "params": {"channel": "email"}}]}]

async def _builtin_templates(q: str = "", limit: int = 20):
    """返回内置模板（n8n 不可用时的兜底）"""
    templates = _BUILTIN_TEMPLATES
    if q:
        ql = q.lower()
        templates = [t for t in templates if ql in t["name"].lower() or ql in t["description"].lower()]
    return {"success": True, "templates": templates[:limit], "total": len(templates), "source": "builtin"}
