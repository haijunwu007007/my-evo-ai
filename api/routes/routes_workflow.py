from core.logging_config import get_logger
logger = get_logger("evo.routes_workflow")
"""AUTO-EVO-AI V0.1 — 全自动工作流路由（中文版n8n模板集成）"""
import logging, json, httpx, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("workflow")
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

# ── 中文工作流模板库（小白也能用）──
_CN_TEMPLATES = [
    {"id":"daily_report","name":"每日工作日报","desc":"每天自动收集工作记录，生成日报并发送到邮箱/钉钉","tags":["日报","邮件","通知","钉钉","每天"],"type":"auto"},
    {"id":"gather_trending","name":"GitHub热门收集","desc":"每天自动收集GitHub热门项目，推送到钉钉/Slack群","tags":["GitHub","热门","每日","通知","钉钉"],"type":"auto"},
    {"id":"backup_files","name":"文件自动备份","desc":"定时备份本地文件夹到云存储（OSS/S3）","tags":["备份","云存储","OSS","S3","定时"],"type":"auto"},
    {"id":"rss_monitor","name":"RSS订阅监控","desc":"监控RSS源更新，有新文章自动推送到Slack/钉钉","tags":["RSS","监控","通知","订阅"],"type":"auto"},
    {"id":"email_summary","name":"邮件摘要","desc":"每天定时汇总收件箱邮件，生成摘要报告","tags":["邮件","摘要","日报","IMAP"],"type":"auto"},
    {"id":"website_monitor","name":"网站变更监控","desc":"定时检查网站是否变更，有变化立即通知","tags":["网站","监控","变更","通知"],"type":"auto"},
    {"id":"excel_report","name":"Excel自动报表","desc":"从数据库查询数据，自动生成Excel报表发送到邮箱","tags":["Excel","报表","数据库","邮件"],"type":"auto"},
    {"id":"webhook_trigger","name":"Webhook自动处理","desc":"接收Webhook请求，自动处理并转发到其他系统","tags":["Webhook","转发","自动化"],"type":"auto"},
    {"id":"schedule_meeting","name":"会议提醒","desc":"定时发送会议提醒到群聊/邮箱","tags":["会议","提醒","通知","定时"],"type":"auto"},
    {"id":"github_pr_reminder","name":"PR待审核提醒","desc":"每天检查GitHub仓库的待审核PR，发送提醒","tags":["GitHub","PR","提醒","每日"],"type":"auto"},
    {"id":"data_sync","name":"数据同步","desc":"定时同步两个数据库之间的数据","tags":["数据库","同步","定时"],"type":"auto"},
    {"id":"image_compress","name":"图片自动压缩","desc":"监控文件夹，新图片自动压缩后上传到云存储","tags":["图片","压缩","OSS","自动"],"type":"auto"},
    {"id":"log_cleanup","name":"日志自动清理","desc":"定时清理7天前的日志文件，释放磁盘空间","tags":["日志","清理","定时","运维"],"type":"auto"},
    {"id":"weather_notify","name":"每日天气推送","desc":"每天早上获取天气信息，推送到群聊","tags":["天气","推送","每天早上","钉钉"],"type":"auto"},
    {"id":"stock_monitor","name":"股票行情监控","desc":"定时查询股票行情，异动时发送通知","tags":["股票","行情","监控","通知"],"type":"auto"},
    {"id":"news_digest","name":"新闻摘要","desc":"定时抓取新闻，生成摘要推送到群聊","tags":["新闻","摘要","每天","推送"],"type":"auto"},
    {"id":"db_backup","name":"数据库备份","desc":"定时备份数据库并上传到云存储","tags":["数据库","备份","定时","云存储"],"type":"auto"},
    {"id":"form_collect","name":"表单自动收集","desc":"自动收集在线表单提交数据，写入数据库或Excel","tags":["表单","收集","数据库","Excel"],"type":"auto"},
    {"id":"social_monitor","name":"社交媒体监控","desc":"监控社交媒体关键词，有提及自动通知","tags":["社交媒体","监控","关键词","通知"],"type":"auto"},
    {"id":"api_health","name":"API健康检查","desc":"定时检查API端点是否正常，异常时告警","tags":["API","健康","检查","告警"],"type":"auto"},
]

_DEFAULT_CATS = ["通知推送","数据备份","日报报告","监控告警","文件处理","定时任务"]

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
    """搜索工作流模板（中文优先，自动匹配，n8n结果自动翻译）"""
    ql = q.strip().lower()

    # 1. 中文模板库匹配
    results = []
    for t in _CN_TEMPLATES:
        if not ql or any(ql in kw for kw in t["tags"]) or ql in t["name"] or ql in t["desc"]:
            results.append(t)
    if results:
        return {"success": True, "templates": results[:limit], "total": len(results), "source": "cn"}

    # 2. 中文转英文搜索 n8n
    en_query = q
    if q and not re.match(r'^[a-zA-Z0-9 ]+$', q):
        try:
            from api.agent_llm import call_llm
            sp = f"将以下中文翻译为英文搜索词（只输出英文，不要解释）：{q}"
            txt, _ = call_llm([{"role":"user","content":sp}])
            if txt and txt.strip():
                en_query = txt.strip()[:50]
        except Exception as _e:
            logger.warning(f"error: {_e}")

    url = f"{N8N_API}/workflows"
    params = {"limit": limit}
    if en_query: params["search"] = en_query
    if category: params["category"] = category
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                templates = data.get("data", [])
                # 用 LLM 翻译结果名称为中文
                if templates:
                    try:
                        from api.agent_llm import call_llm as cl
                        names = [t.get("name","") for t in templates[:10]]
                        sp2 = f"将以下英文翻译为中文，每行一个：\n" + "\n".join(names)
                        txt2, _ = cl([{"role":"user","content":sp2}])
                        if txt2:
                            lines = [l.strip() for l in txt2.split("\n") if l.strip()]
                            for i, t in enumerate(templates):
                                if i < len(lines):
                                    t["name_cn"] = lines[i]
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
                return {"success": True, "templates": templates[:limit], "total": len(templates), "source": "n8n"}
    except Exception as _e:
            logger.warning(f"error: {_e}")

    # 3. n8n 不可用，返回全部中文模板
    return {"success": True, "templates": _CN_TEMPLATES[:limit], "total": len(_CN_TEMPLATES), "source": "cn"}

@router.get("/templates/categories")
async def list_categories():
    return {"success": True, "categories": _DEFAULT_CATS}

@router.get("/templates/{template_id}")
async def get_template(template_id: int):
    """获取单个 n8n 模板详情"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{N8N_API}/workflows/{template_id}")
            if r.status_code == 200:
                return {"success": True, "template": r.json()}
    except Exception as _e:
            logger.warning(f"error: {_e}")
    # 本地兜底
    for t in _CN_TEMPLATES:
        if t.get("id") == template_id:
            return {"success": True, "template": t}
    return {"success": True, "template": _CN_TEMPLATES[0]}

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
                r = await c.get(f"{N8N_API}/workflows/{template_id}")
                if r.status_code == 200:
                    workflow_data = r.json()
        except Exception as _e:
            logger.warning(f"error: {_e}")
        if not workflow_data:
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
