"""
AUTO-EVO-AI V0.1 — 服务类路由
=============================
从 api_server.py 提取：文档生成、通知服务、浏览器自动化、LLM 网关、CI/CD、GitHub 扫描、插件市场

用法:
    from api.routes_services import router
    app.include_router(router)
"""

from __future__ import annotations

import os
import base64
from typing import Any, Dict, List

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from api.infra import (
    registry, logger, BASE_DIR,
    NotificationRequest, EmailConfigRequest,
    LLMChatRequest, LLMProviderRequest,
    DocReportRequest, DocPresentationRequest,
)
from core.evolution_engine import engine as evo_engine

router = APIRouter()


# ═══════════════════════════════════════════════════
# CI/CD 集成 — GitHub/Git/Docker/Webhook
# ═══════════════════════════════════════════════════
from core.cicd_engine import get_cicd_engine


@router.get("/api/cicd/github/config")
async def cicd_github_config():
    """GitHub连接配置状态"""
    cicd = get_cicd_engine()
    return {"success": True, **cicd.github_config()}


@router.get("/api/cicd/github/repos")
async def cicd_github_repos(org: str = ""):
    """列出GitHub仓库"""
    cicd = get_cicd_engine()
    return {"success": True, "repos": cicd.github_repos(org)}


@router.get("/api/cicd/github/branches")
async def cicd_github_branches(repo: str = ""):
    """列出仓库分支"""
    cicd = get_cicd_engine()
    return {"success": True, "branches": cicd.github_branches(repo)}


@router.get("/api/cicd/github/issues")
async def cicd_github_issues(repo: str = "", state: str = "open"):
    """列出Issues"""
    cicd = get_cicd_engine()
    return {"success": True, "issues": cicd.github_issues(repo, state)}


@router.post("/api/cicd/github/issues/create")
async def cicd_github_create_issue(request: Request):
    """创建Issue"""
    body = await request.json()
    cicd = get_cicd_engine()
    return cicd.github_create_issue(body.get("repo", ""), body.get("title", ""), body.get("body", ""))


@router.get("/api/cicd/github/pulls")
async def cicd_github_prs(repo: str = "", state: str = "open"):
    """列出PR"""
    cicd = get_cicd_engine()
    return {"success": True, "pulls": cicd.github_prs(repo, state)}


@router.get("/api/cicd/github/workflows")
async def cicd_github_workflows(repo: str = ""):
    """列出Actions Workflows"""
    cicd = get_cicd_engine()
    return {"success": True, "workflows": cicd.github_workflows(repo)}


@router.post("/api/cicd/github/workflows/trigger")
async def cicd_github_trigger(request: Request):
    """触发Workflow"""
    body = await request.json()
    cicd = get_cicd_engine()
    return cicd.github_trigger_workflow(body.get("repo", ""), body.get("workflow", ""),
                                        body.get("ref", "main"), body.get("inputs"))


@router.get("/api/cicd/git/status")
async def cicd_git_status(path: str = ""):
    """Git仓库状态"""
    cicd = get_cicd_engine()
    return cicd.git_status(path or str(BASE_DIR))


@router.get("/api/cicd/git/log")
async def cicd_git_log(path: str = "", n: int = 10):
    """Git提交历史"""
    cicd = get_cicd_engine()
    return cicd.git_log(path or str(BASE_DIR), n)


@router.post("/api/cicd/git/pull")
async def cicd_git_pull(path: str = ""):
    """Git Pull"""
    cicd = get_cicd_engine()
    return cicd.git_pull(path or str(BASE_DIR))


@router.post("/api/cicd/git/push")
async def cicd_git_push(path: str = ""):
    """Git Push"""
    cicd = get_cicd_engine()
    return cicd.git_push(path or str(BASE_DIR))


@router.post("/api/cicd/git/commit")
async def cicd_git_commit(request: Request):
    """Git Add+Commit+Push"""
    body = await request.json()
    cicd = get_cicd_engine()
    return cicd.git_commit_push(body.get("path", str(BASE_DIR)), body.get("message", "auto commit"))


@router.post("/api/cicd/deploy/build")
async def cicd_deploy_build(path: str = "", tag: str = "latest"):
    """Docker构建"""
    cicd = get_cicd_engine()
    return cicd.deploy_docker_build(path or str(BASE_DIR), tag)


@router.post("/api/cicd/deploy/up")
async def cicd_deploy_up(path: str = ""):
    """Docker Compose Up"""
    cicd = get_cicd_engine()
    return cicd.deploy_docker_up(path or str(BASE_DIR))


@router.post("/api/cicd/deploy/down")
async def cicd_deploy_down(path: str = ""):
    """Docker Compose Down"""
    cicd = get_cicd_engine()
    return cicd.deploy_docker_down(path or str(BASE_DIR))


@router.post("/api/cicd/webhook/{source}")
async def cicd_webhook(source: str, request: Request):
    """接收CI/CD Webhook"""
    body = await request.json()
    event_type = request.headers.get("X-GitHub-Event", request.headers.get("X-Gitlab-Event", "unknown"))
    cicd = get_cicd_engine()
    return cicd.receive_webhook(source, event_type, body)


@router.get("/api/cicd/webhooks")
async def cicd_list_webhooks(limit: int = 50):
    """列出Webhook事件"""
    cicd = get_cicd_engine()
    return {"success": True, "events": cicd.list_webhooks(limit)}


# ═══════════════════════════════════════════════════════
# GitHub Webhook 接收与事件管理 (V2 — 生产级)
# ═══════════════════════════════════════════════════════
from modules.github_webhook import process_webhook, list_events, get_event_stats, clear_events, get_config, update_config, health_check as gh_health
from pydantic import BaseModel

class GithubWebhookConfig(BaseModel):
    enabled: bool | None = None
    channels: list[dict] | None = None
    events: list[str] | None = None
    min_priority: int | None = None

@router.post("/api/webhook/github")
async def webhook_github(request: Request):
    """接收 GitHub Webhook (push/pr/workflow/issues/release/ping)"""
    event_type = request.headers.get("X-GitHub-Event", "ping")
    signature = request.headers.get("X-Hub-Signature-256", "") or request.headers.get("X-Hub-Signature", "")
    secret = (get_config().get("secret") or "")
    payload = await request.json()
    return await process_webhook(event_type, payload, signature, secret)

@router.get("/api/webhook/github/events")
async def webhook_events(event_type: str = "", repo: str = "", limit: int = 50, offset: int = 0):
    """查询 GitHub Webhook 事件历史"""
    return {"success": True, "events": list_events(
        event_type=event_type or None,
        repo=repo or None,
        limit=limit,
        offset=offset,
    )}

@router.get("/api/webhook/github/stats")
async def webhook_stats():
    """事件统计"""
    return {"success": True, **get_event_stats()}

@router.post("/api/webhook/github/clear")
async def webhook_clear(older_than: int = 0):
    """清理事件历史"""
    n = clear_events(older_than)
    return {"success": True, "deleted": n}

@router.get("/api/webhook/github/config")
async def webhook_get_config():
    """获取通知配置"""
    return {"success": True, "config": get_config()}

@router.post("/api/webhook/github/config")
async def webhook_set_config(body: GithubWebhookConfig):
    """更新通知配置"""
    cfg = {k: v for k, v in body.model_dump().items() if v is not None}
    return {"success": True, "config": update_config(cfg)}

@router.get("/api/webhook/github/health")
async def webhook_health():
    """健康检查"""
    result = gh_health()
    if isinstance(result, dict) and "success" not in result:
        return {"success": True, **result}
    return result


# ═══════════════════════════════════════════════════
# 文档生成引擎 — Word/Excel/PPT/Markdown
# ═══════════════════════════════════════════════════
from core.doc_generator import get_doc_generator


@router.post("/api/docs/report")
async def generate_report(request: Request):
    """生成报告文档 (markdown/html/word)"""
    body = await request.json()
    gen = get_doc_generator()
    result = gen.generate_report(
        body.get("title", "报告"), body.get("sections", []),
        body.get("format", "markdown"), body.get("metadata") or {},
    )
    return result


@router.post("/api/docs/table-report")
async def generate_table_report(request: Request):
    """生成表格报告"""
    body = await request.json()
    gen = get_doc_generator()
    result = gen.generate_table_report(body.get("title", "数据报告"), body.get("tables") or {}, body.get("format", "excel"))
    return result


@router.post("/api/docs/presentation")
async def generate_presentation(request: Request):
    """生成PPT演示文稿"""
    body = await request.json()
    gen = get_doc_generator()
    result = gen.generate_presentation(body.get("title", "演示文稿"), body.get("slides", []))
    return result


@router.post("/api/docs/excel")
async def generate_excel(tables: dict = None):
    """生成Excel并下载"""
    gen = get_doc_generator()
    buf = gen.data_to_excel_bytes(tables or {})
    return StreamingResponse(iter([buf]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              headers={"Content-Disposition": "attachment; filename=report.xlsx"})


@router.post("/api/docs/word")
async def generate_word(title: str = "文档", sections: list[dict] = []):
    """生成Word并下载"""
    gen = get_doc_generator()
    buf = gen.data_to_word_bytes(title, sections)
    return StreamingResponse(iter([buf]), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                              headers={"Content-Disposition": "attachment; filename=report.docx"})


@router.get("/api/docs/files")
async def list_doc_files():
    """列出已生成的文档文件"""
    gen = get_doc_generator()
    return {"success": True, "files": gen.list_output_files()}


# ═══════════════════════════════════════════════════
# 外部通知服务 — 邮件/IM/Webhook/推送
# ═══════════════════════════════════════════════════
from core.external_services import get_notification_service


@router.get("/api/notify/channels")
async def notify_channels():
    """列出所有通知渠道及配置状态"""
    ns = get_notification_service()
    return {
        "success": True,
        "channels": [
            {"id": "email", "name": "邮件", "configured": ns.email_config().get("configured", False)},
            {"id": "wechat_work", "name": "企业微信", "configured": True},
            {"id": "dingtalk", "name": "钉钉", "configured": True},
            {"id": "feishu", "name": "飞书", "configured": True},
            {"id": "serverchan", "name": "Server酱", "configured": True},
            {"id": "pushplus", "name": "PushPlus", "configured": True},
        ],
        "email_config": ns.email_config(),
    }


@router.post("/api/notify/email/configure")
async def notify_email_configure(req: EmailConfigRequest):
    """配置SMTP邮箱"""
    ns = get_notification_service()
    return ns.configure_email(host=req.host, port=req.port, user=req.user,
                               password=req.password, ssl=req.ssl, from_name=req.from_name)


@router.post("/api/notify/send")
async def notify_send(req: NotificationRequest):
    """统一发送通知"""
    ns = get_notification_service()
    result = ns.send(
        channel=req.channel,
        to=req.to,
        subject=req.subject,
        content=req.content,
        msg_type=req.msg_type,
        secret=req.secret,
        html=req.html,
    )
    return result


@router.post("/api/notify/email")
async def notify_email(to: str = "", subject: str = "", body: str = "", html: str = ""):
    """发送邮件"""
    ns = get_notification_service()
    return ns.send_email(to=to, subject=subject, body=body, html=html)


@router.post("/api/notify/wechat_work")
async def notify_wechat_work(webhook_url: str = "", content: str = "", msg_type: str = "text"):
    """企业微信通知"""
    ns = get_notification_service()
    return ns.send_wechat_work(webhook_url, content, msg_type)


@router.post("/api/notify/dingtalk")
async def notify_dingtalk(webhook_url: str = "", content: str = "", secret: str = "", msg_type: str = "text"):
    """钉钉通知"""
    ns = get_notification_service()
    return ns.send_dingtalk(webhook_url, content, secret, msg_type)


@router.post("/api/notify/feishu")
async def notify_feishu(webhook_url: str = "", content: str = "", msg_type: str = "text", title: str = "通知"):
    """飞书通知"""
    ns = get_notification_service()
    return ns.send_feishu(webhook_url, content, msg_type, title)


@router.post("/api/notify/serverchan")
async def notify_serverchan(sendkey: str = "", title: str = "", desp: str = ""):
    """Server酱推送"""
    ns = get_notification_service()
    return ns.send_serverchan(sendkey, title, desp)


@router.post("/api/notify/pushplus")
async def notify_pushplus(token: str = "", title: str = "", content: str = "", template: str = "txt"):
    """PushPlus推送"""
    ns = get_notification_service()
    return ns.send_pushplus(token, title, content, template)


@router.post("/api/notify/bark")
async def notify_bark(device_key: str = "", title: str = "", body: str = ""):
    """Bark推送"""
    ns = get_notification_service()
    return ns.send_bark(device_key, title, body)


@router.post("/api/notify/webhook")
async def notify_webhook(url: str = "", data: str = "", secret: str = "", retries: int = 0):
    """发送Webhook"""
    import json as _json
    ns = get_notification_service()
    try:
        parsed_data = _json.loads(data) if data else {}
    except _json.JSONDecodeError:
        parsed_data = {"message": data}
    return ns.send_webhook(url, parsed_data, secret=secret, retries=retries)


@router.get("/api/notify/history")
async def notify_history(channel: str = "", limit: int = 50):
    """获取通知发送历史"""
    ns = get_notification_service()
    return {"success": True, "history": ns.get_history(channel, limit)}


@router.get("/api/notify/stats")
async def notify_stats():
    """通知统计"""
    ns = get_notification_service()
    return {"success": True, **ns.get_stats()}


@router.get("/api/notify/templates")
async def notify_templates():
    """列出通知模板"""
    ns = get_notification_service()
    return {"success": True, "templates": ns.list_templates()}


# ═══════════════════════════════════════════════════
# AI 聊天聚合 API — 统一多模型接入
# ═══════════════════════════════════════════════════

from pydantic import BaseModel

class AIChatMessage(BaseModel):
    role: str = "user"
    content: str = ""

class AIChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[AIChatMessage] = []
    temperature: float = 0.7

@router.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    """统一AI聊天API：自动选择最优provider，支持负载均衡和故障转移"""
    from modules.ai_gateway import AIGateway
    gw = AIGateway()
    gw.initialize()
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    params = {"model": req.model, "messages": msgs, "temperature": req.temperature}
    result = await gw.execute("chat", params)
    gw.shutdown()
    return {"success": True, "data": result, "providers": {
        "openai": bool(os.environ.get("OPENAI_API_KEY","")),
        "claude": bool(os.environ.get("ANTHROPIC_API_KEY","")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY","")),
    }}


@router.get("/api/ai/providers")
async def ai_providers():
    """列出可用的AI provider及状态"""
    cfg = {
        "openai": {"configured": bool(os.environ.get("OPENAI_API_KEY","") or os.environ.get("OPENAI_BASE_URL",""))},
        "claude": {"configured": bool(os.environ.get("ANTHROPIC_API_KEY",""))},
        "gemini": {"configured": bool(os.environ.get("GEMINI_API_KEY",""))},
    }
    return {"success": True, "providers": cfg}

@router.get("/api/ai/models")
async def ai_models():
    """列出支持的模型"""
    models = [
        {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o 旗舰"},
        {"id": "gpt-4o-mini", "provider": "openai", "description": "OpenAI GPT-4o-mini 轻量"},
        {"id": "gpt-4-turbo", "provider": "openai", "description": "OpenAI GPT-4 Turbo"},
        {"id": "claude-sonnet-4-20250514", "provider": "claude", "description": "Claude Sonnet 4"},
        {"id": "claude-haiku-3-20250313", "provider": "claude", "description": "Claude Haiku 3"},
        {"id": "gemini-2.0-flash", "provider": "gemini", "description": "Gemini 2.0 Flash"},
        {"id": "gemini-2.0-pro", "provider": "gemini", "description": "Gemini 2.0 Pro"},
    ]
    return {"success": True, "models": models}

# ═══════════════════════════════════════════════════
# 浏览器自动化引擎 — Web操作API
# ═══════════════════════════════════════════════════
from core.browser_engine import get_browser_engine, close_browser as _close_browser


@router.post("/api/browser/launch")
async def browser_launch(headless: bool = True, engine_type: str = "auto"):
    """启动浏览器引擎"""
    engine = await get_browser_engine()
    return await engine.launch(engine_type=engine_type, headless=headless)


@router.post("/api/browser/close")
async def browser_close_endpoint():
    """关闭浏览器引擎"""
    await _close_browser()
    return {"success": True}


@router.get("/api/browser/status")
async def browser_status():
    """获取浏览器状态"""
    engine = await get_browser_engine()
    return await engine.get_status()


@router.post("/api/browser/goto")
async def browser_goto(url: str = "", wait_until: str = "domcontentloaded", timeout: int = 30000):
    """导航到URL"""
    engine = await get_browser_engine()
    return await engine.goto(url, wait_until=wait_until, timeout=timeout)


@router.post("/api/browser/screenshot")
async def browser_screenshot(selector: str = "", full_page: bool = False):
    """页面截图"""
    engine = await get_browser_engine()
    result = await engine.screenshot(selector=selector, full_page=full_page)
    return {
        "success": bool(result.base64),
        "base64": result.base64[:100] + "..." if result.base64 else "",
        "base64_length": len(result.base64) if result.base64 else 0,
        "width": result.width,
        "height": result.height,
    }


@router.post("/api/browser/screenshot/image")
async def browser_screenshot_image(selector: str = "", full_page: bool = False):
    """截图图片直出"""
    import base64 as _b64
    engine = await get_browser_engine()
    result = await engine.screenshot(selector=selector, full_page=full_page)
    if result.base64:
        return StreamingResponse(
            iter([_b64.b64decode(result.base64)]),
            media_type="image/png",
        )
    raise HTTPException(status_code=500, detail="截图失败")


@router.post("/api/browser/click")
async def browser_click(selector: str = ""):
    """点击元素"""
    engine = await get_browser_engine()
    return await engine.click(selector)


@router.post("/api/browser/fill")
async def browser_fill(selector: str = "", value: str = ""):
    """填写输入框"""
    engine = await get_browser_engine()
    return await engine.fill(selector, value)


@router.post("/api/browser/type")
async def browser_type(selector: str = "", text: str = "", delay: int = 50):
    """模拟键盘输入"""
    engine = await get_browser_engine()
    return await engine.type_text(selector, text, delay)


@router.post("/api/browser/select")
async def browser_select(selector: str = "", value: str = "", label: str = ""):
    """选择下拉选项"""
    engine = await get_browser_engine()
    return await engine.select_option(selector, value=value, label=label)


@router.post("/api/browser/hover")
async def browser_hover(selector: str = ""):
    """悬停"""
    engine = await get_browser_engine()
    return await engine.hover(selector)


@router.post("/api/browser/press")
async def browser_press(key: str = "Enter"):
    """按键"""
    engine = await get_browser_engine()
    return await engine.press_key(key)


@router.post("/api/browser/wait")
async def browser_wait(selector: str = "", timeout: int = 10000):
    """等待元素出现"""
    engine = await get_browser_engine()
    return await engine.wait_for_selector(selector, timeout)


@router.post("/api/browser/evaluate")
async def browser_evaluate(script: str = ""):
    """执行JavaScript"""
    engine = await get_browser_engine()
    return await engine.evaluate(script)


@router.post("/api/browser/scroll")
async def browser_scroll(position: str = "bottom", selector: str = ""):
    """滚动页面"""
    engine = await get_browser_engine()
    return await engine.scroll_to(position, selector)


@router.post("/api/browser/extract")
async def browser_extract(what: str = "all"):
    """提取页面数据(text/tables/links/images/forms/all)"""
    engine = await get_browser_engine()
    result = {}
    if what in ("text", "content", "all"):
        content = await engine.get_content()
        result["content"] = content
    if what in ("tables", "all"):
        result["tables"] = await engine.extract_tables()
    if what in ("links", "all"):
        result["links"] = await engine.extract_links()
    if what in ("images", "all"):
        result["images"] = await engine.extract_images()
    if what in ("forms", "all"):
        result["forms"] = await engine.extract_forms()
    return {"success": True, **result}


@router.post("/api/browser/form/auto-fill")
async def browser_auto_fill(form_index: int = 0, data: dict = None):
    """自动填写表单"""
    import base64 as _b64
    engine = await get_browser_engine()
    return await engine.auto_fill_form(form_index, data or {})


@router.get("/api/browser/cookies")
async def browser_cookies():
    """获取Cookie"""
    engine = await get_browser_engine()
    cookies = await engine.get_cookies()
    return {"success": True, "cookies": cookies}


@router.post("/api/browser/cookies/set")
async def browser_set_cookies(cookies: list[dict] = None):
    """设置Cookie"""
    engine = await get_browser_engine()
    return await engine.set_cookies(cookies or [])


@router.get("/api/browser/network")
async def browser_network_log():
    """获取网络请求日志"""
    engine = await get_browser_engine()
    log = await engine.network_log()
    return {"success": True, "log": log}


@router.post("/api/browser/task")
async def browser_run_task(task: dict):
    """执行自动化任务脚本"""
    from core.browser_engine import BrowserTask
    engine = await get_browser_engine()
    bt = BrowserTask(
        id=task.get("id", hashlib.md5(str(time.time()).encode()).hexdigest()[:8]),
        name=task.get("name", "unnamed"),
        steps=task.get("steps", []),
    )
    result = await engine.execute_task(bt)
    return {
        "success": result.status == "completed",
        "task_id": result.id,
        "status": result.status,
        "steps_completed": result.current_step + 1,
        "steps_total": len(result.steps),
        "results": result.result,
        "error": result.error,
        "duration_ms": round((result.finished_at - result.started_at) * 1000) if result.started_at else 0,
    }


# ═══════════════════════════════════════════════════
# LLM 智能网关 — 统一AI对话接口
# ═══════════════════════════════════════════════════
from core.llm_gateway import get_llm_pool, reset_llm_pool


@router.get("/api/llm/providers")
async def llm_providers():
    """列出所有LLM Provider"""
    pool = get_llm_pool()
    return {"success": True, "providers": pool.list_providers()}


@router.get("/api/llm/models")
async def llm_models():
    """列出所有可用模型"""
    pool = get_llm_pool()
    return {"success": True, "models": pool.list_models()}


@router.post("/api/llm/providers/add")
async def llm_add_provider(req: LLMProviderRequest):
    """动态添加LLM Provider"""
    pool = get_llm_pool()
    ok = pool.add_provider(req.name, {
        "provider_type": req.provider_type,
        "base_url": req.base_url,
        "api_key": req.api_key,
        "models": req.models,
        "priority": req.priority,
    })
    return {"success": ok}


@router.delete("/api/llm/providers/{name}")
async def llm_remove_provider(name: str):
    """移除LLM Provider"""
    pool = get_llm_pool()
    ok = pool.remove_provider(name)
    return {"success": ok}


@router.post("/api/llm/default")
async def llm_set_default(provider: str = "", model: str = ""):
    """设置默认Provider和模型"""
    pool = get_llm_pool()
    ok = pool.set_default(provider, model)
    return {"success": ok, "default": pool.list_providers()}


@router.get("/api/llm/stats")
async def llm_stats(hours: int = 24):
    """LLM使用统计"""
    pool = get_llm_pool()
    return {"success": True, **pool.get_stats(), "cost_report": pool.get_cost_report(hours)}


@router.get("/api/llm/health")
async def llm_health():
    """检查所有Provider连通性"""
    pool = get_llm_pool()
    return {"success": True, "providers": pool.health_check()}


@router.post("/api/llm/cache/clear")
async def llm_cache_clear():
    """清空LLM响应缓存"""
    pool = get_llm_pool()
    pool.clear_cache()
    return {"success": True}


@router.get("/api/llm/sessions")
async def llm_sessions():
    """列出所有对话会话"""
    pool = get_llm_pool()
    return {"success": True, "sessions": pool.list_sessions()}


@router.delete("/api/llm/sessions/{session_id}")
async def llm_clear_session(session_id: str):
    """清除指定会话"""
    pool = get_llm_pool()
    pool.clear_session(session_id)
    return {"success": True}


@router.get("/api/llm/sessions/{session_id}/history")
async def llm_session_history(session_id: str, last_n: int = 20):
    """获取会话历史"""
    pool = get_llm_pool()
    return {"success": True, "messages": pool.get_session_history(session_id, last_n)}


@router.post("/api/llm/chat")
async def llm_chat(req: LLMChatRequest):
    """LLM对话 — 非流式"""
    pool = get_llm_pool()
    result = pool.chat_sync(
        prompt=req.prompt,
        model=req.model,
        session_id=req.session_id,
        system_prompt=req.system_prompt,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        use_cache=req.use_cache,
    )
    return result


@router.post("/api/llm/chat/stream")
async def llm_chat_stream(req: LLMChatRequest):
    """LLM对话 — SSE流式"""
    import asyncio
    pool = get_llm_pool()
    messages = []
    if req.system_prompt:
        messages.append({"role": "system", "content": req.system_prompt})
    if req.session_id:
        history = pool.get_session_history(req.session_id, 20)
        messages.extend(history)
    if req.messages:
        messages.extend(req.messages)
    if req.prompt:
        messages.append({"role": "user", "content": req.prompt})

    if not messages:
        return JSONResponse({"success": False, "error": "无消息内容"})

    model = req.model or ""

    async def event_generator():
        loop = asyncio.get_event_loop()
        for chunk in pool.chat_stream_sync(
            prompt=req.prompt,
            model=model,
            session_id=req.session_id,
            system_prompt=req.system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════
# GitHub 智能扫描
# ═══════════════════════════════════════════════════
from core.github_scanner import get_github_scanner
from core.plugin_manager import PluginManager

_gh_scanner = None


def _get_gh_scanner():
    global _gh_scanner
    if _gh_scanner is None:
        _gh_scanner = get_github_scanner()
    return _gh_scanner


@router.get("/api/github/stats")
async def github_stats():
    """GitHub扫描统计"""
    gh = _get_gh_scanner()
    return {"success": True, **gh.get_stats()}


@router.get("/api/github/reports")
async def github_reports(limit: int = 20, scan_type: str = None):
    """扫描报告列表"""
    gh = _get_gh_scanner()
    reports = gh.get_reports(limit=limit)
    return {"success": True, "reports": reports}


@router.get("/api/github/reports/{report_id}")
async def github_report_detail(report_id: str):
    """扫描报告详情"""
    gh = _get_gh_scanner()
    report = gh.get_report(report_id)
    if not report:
        return {"success": False, "error": "报告不存在"}
    return {"success": True, **report}


@router.post("/api/github/scan")
async def github_scan(body: dict = None):
    """触发扫描 (支持指定模式: full/dependencies/trending/tracked)"""
    gh = _get_gh_scanner()
    mode = (body or {}).get("mode", "full")
    report = await gh.run_scan(mode=mode)
    return {"success": True, **report}


@router.get("/api/github/tracked")
async def github_tracked():
    """关注的仓库"""
    from core.github_scanner import TRACKED_REPOS
    return {"success": True, "repos": TRACKED_REPOS}


# ═══════════════════════════════════════════════════════
# 插件市场 API
# ═══════════════════════════════════════════════════════


def _get_plugin_manager() -> PluginManager:
    return PluginManager()


@router.get("/api/plugins")
async def plugin_list():
    """列出已安装插件"""
    pm = _get_plugin_manager()
    return {"success": True, **pm.get_stats()}


@router.get("/api/plugins/repository")
async def plugin_repository(tag: str = "", search: str = ""):
    """浏览插件仓库"""
    pm = _get_plugin_manager()
    return {"success": True, "plugins": pm.browse_repository(tag=tag, search=search)}


@router.get("/api/plugins/{name}")
async def plugin_detail(name: str):
    """插件详情"""
    pm = _get_plugin_manager()
    plugin = pm.get_plugin(name)
    if not plugin:
        return {"success": False, "error": "Plugin not found"}, 404
    return {"success": True, **plugin}


@router.post("/api/plugins/{name}/install")
async def plugin_install(name: str, source: str = "builtin"):
    """安装插件"""
    pm = _get_plugin_manager()
    return pm.install_plugin(name, source=source)


@router.post("/api/plugins/{name}/enable")
async def plugin_enable(name: str):
    """启用插件"""
    pm = _get_plugin_manager()
    return pm.enable_plugin(name)


@router.post("/api/plugins/{name}/disable")
async def plugin_disable(name: str):
    """禁用插件"""
    pm = _get_plugin_manager()
    return pm.disable_plugin(name)


@router.post("/api/plugins/{name}/uninstall")
async def plugin_uninstall(name: str, remove_data: bool = False):
    """卸载插件"""
    pm = _get_plugin_manager()
    return pm.uninstall_plugin(name, remove_data=remove_data)


# ═══════════════════════════════════════════════════
# MySQL CDC (Change Data Capture)
# ═══════════════════════════════════════════════════
from modules.mysql_cdc import execute as cdc_execute


@router.get("/api/cdc/status")
async def cdc_status():
    """CDC 运行状态"""
    return cdc_execute("status")


@router.post("/api/cdc/start")
async def cdc_start(config: dict = {}):
    """启动 CDC"""
    return cdc_execute("start", {"config": config})


@router.post("/api/cdc/stop")
async def cdc_stop():
    """停止 CDC"""
    return cdc_execute("stop")


@router.post("/api/cdc/config")
async def cdc_config(config: dict = {}):
    """更新配置"""
    return cdc_execute("config", config)


@router.get("/api/cdc/events")
async def cdc_events(limit: int = 100):
    """获取变更事件"""
    return cdc_execute("events", {"limit": limit})


@router.get("/api/cdc/tables")
async def cdc_tables():
    """获取可监听表清单"""
    return cdc_execute("tables")


@router.post("/api/cdc/reset")
async def cdc_reset():
    """重置断点"""
    return cdc_execute("reset")


@router.post("/api/plugins/{name}/execute")
async def plugin_execute(name: str, action: str = "status", params: dict = None):
    """执行插件操作"""
    pm = _get_plugin_manager()
    return await pm.execute_plugin(name, action, params)


@router.get("/api/plugins/{name}/compatibility")
async def plugin_compatibility(name: str):
    """检查插件兼容性"""
    pm = _get_plugin_manager()
    return {"success": True, **pm.check_compatibility(name)}


# ═══════════════════════════════════════════════════════
# 进化引擎 API
# ═══════════════════════════════════════════════════════

@router.get("/api/evo/summary")
async def evo_summary():
    """进化引擎概要"""
    evo_engine.start_scoring_loop()
    return {"success": True, "data": evo_engine.summary()}

@router.get("/api/evo/ranking")
async def evo_ranking(top_n: int = Query(5, ge=1, le=50)):
    """模块评分排名"""
    return {"success": True, "data": evo_engine.ranking(top_n)}

@router.get("/api/evo/module/{module}")
async def evo_module(module: str):
    """模块进化详情"""
    detail = evo_engine.module_detail(module)
    if not detail:
        raise HTTPException(status_code=404, detail="Module not tracked")
    return {"success": True, "data": detail}

@router.get("/api/evo/degraded")
async def evo_degraded():
    """degraded 模块列表"""
    return {"success": True, "data": evo_engine.degraded_modules()}

@router.get("/api/evo/suggestions")
async def evo_suggestions():
    """优化建议"""
    return {"success": True, "data": evo_engine.suggestions()}

@router.post("/api/evo/record")
async def evo_record(req: Request):
    """手动记录一次执行"""
    body = await req.json()
    evo_engine.record(
        module=body.get("module", "unknown"),
        action=body.get("action", "execute"),
        success=body.get("success", True),
        latency_ms=body.get("latency_ms", 0),
        error=body.get("error", ""),
        context=body.get("context"),
    )
    return {"success": True}


__all__ = ["router"]
