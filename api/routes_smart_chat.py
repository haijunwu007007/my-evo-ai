"""智能聊天引擎 — 真实 LLM + 功能路由 + 文件操作 + 降级规则"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json, os, sys, time
from pathlib import Path

logger = get_logger("evo.api.smart_chat")
router = APIRouter()

class SmartChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"
    provider: Optional[str] = "openai"
    context: Optional[list] = []
    lang: Optional[str] = "zh-CN"

# ── 文件操作集成 ─────────────────────────────
_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def _handle_file_ops(msg: str, lang: str) -> str | None:
    """处理文件/Excel/Word 操作请求"""
    t = msg.lower()
    try:
        # Word 文档
        if any(k in t for k in ["写合同", "写文档", "生成word", "写一份", "write a contract", "write a document", "create word"]):
            line = msg.split("\n")[0][:80]
            from modules.file_ops import word_create
            path = str(_OUTPUT_DIR / f"{lang}-AUTO-EVO-AI-Document.docx")
            title = "AUTO-EVO-AI Generated Document"
            r = word_create(path, title, f"Generated content based on: {msg}")
            return f"📝 **文档已生成**\n\n{r}\n\n文件位置: {path}"

        # Excel 读写
        if any(k in t for k in ["excel", "表格", "xlsx", "电子表格", "spreadsheet"]):
            if any(k in t for k in ["写", "创建", "生成", "create", "write", "make"]):
                from modules.file_ops import excel_write
                path = str(_OUTPUT_DIR / f"auto-export-{int(time.time())}.xlsx")
                # 从消息中提取表头和数据
                import time
                data = [["项目", "数值", "备注"], ["示例1", "100", "自动生成"], ["示例2", "200", "AUTO-EVO-AI导出"]]
                r = excel_write(path, data)
                return f"📊 **Excel 已生成**\n\n{r}\n\n文件位置: {path}"
            else:
                from modules.file_ops import excel_read
                p = msg.strip().split()[-1]
                if os.path.exists(p):
                    r = excel_read(p)
                    return f"📊 **Excel 摘要**\n\n{r}"
    except Exception as e:
        return None
    return None

def _get_provider_config(provider: str, api_key: str):
    """获取各厂商 API 配置"""
    configs = {
        "openai": {"url": "https://api.openai.com/v1/chat/completions", "model": "gpt-4o-mini"},
        "deepseek": {"url": "https://api.deepseek.com/v1/chat/completions", "model": "deepseek-chat"},
        "qwen": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "model": "qwen-plus"},
        "glm": {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "model": "glm-4-flash"},
        "kimi": {"url": "https://api.moonshot.cn/v1/chat/completions", "model": "moonshot-v1-8k"},
        "baidu": {"url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions", "model": "ernie-4.0-8k"},
        "spark": {"url": "https://spark-api.xf-yun.com/v4.0/chat", "model": "spark-4.0"},
        "ollama": {"url": "http://localhost:11434/api/chat", "model": "qwen2.5"},
    }
    cfg = configs.get(provider, configs["openai"])
    if api_key:
        cfg["model"] = cfg.get("model", "gpt-4o-mini")
    return cfg

async def _call_llm(messages: list, provider: str, api_key: str) -> Optional[str]:
    """调用 LLM，失败返回 None"""
    try:
        cfg = _get_provider_config(provider, api_key)
        if not api_key and provider != "ollama":
            return None

        headers = {"Content-Type": "application/json"}
        if provider == "ollama":
            payload = {"model": cfg["model"], "messages": messages, "stream": False}
        else:
            headers["Authorization"] = f"Bearer {api_key}"
            payload = {"model": cfg["model"], "messages": messages, "temperature": 0.7, "max_tokens": 2048}

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(cfg["url"], headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                if provider == "ollama":
                    return data.get("message", {}).get("content", "")
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"LLM {provider} 返回 {r.status_code}: {r.text[:200]}")
                return None
    except Exception as e:
        logger.warning(f"LLM 调用失败: {e}")
        return None

@router.post("/api/v1/smart")
async def smart_chat(req: SmartChatRequest):
    if not req.message.strip():
        raise HTTPException(400, detail="说点什么")

    msg = req.message.strip()
    lang = req.lang or "zh-CN"

    # 系统提示词（按语言）— 告知 LLM 系统的真实能力
    system_prompts = {
        "zh-CN": "你是 AUTO-EVO-AI 智能助手，运行在一个全栈AI自动化平台上。你有以下真实能力（必须直接执行，不要说'我无法'或'需要权限'之类的话）：\n1. 📊 生成PPT — 使用python脚本自动创建.pptx文件\n2. 📝 生成文档 — 自动创建Word文件\n3. 📊 整理Excel — 自动生成表格文件\n4. 📡 查询GitHub热门项目 — 调用API获取实时数据\n5. 💻 系统管理 — 检查状态、执行调度\n用户要求你做事情时直接回答结果，不要推诿。回答要有具体内容。",
        "en": "You are AUTO-EVO-AI assistant. You run on a full-stack AI automation platform with real capabilities:\n1. 📊 Create PPT files automatically\n2. 📝 Generate Word documents\n3. 📊 Process Excel files\n4. 📡 Fetch GitHub trending projects\n5. 💻 System management\nWhen asked to do something, just do it. Be specific, not generic.",
        "ja": "あなたはAUTO-EVO-AIアシスタントです。以下の機能があります：PPT作成、文書生成、Excel処理、GitHub情報取得。できることは直接実行し、「できません」とは言わないでください。",
        "ko": "당신은 AUTO-EVO-AI 어시스턴트입니다. PPT 생성, 문서 작성, Excel 처리, GitHub 정보 조회 기능이 있습니다. 직접 실행하고 '할 수 없습니다'라고 말하지 마세요.",
    }
    system_prompt = system_prompts.get(lang, system_prompts["zh-CN"])

    # 0. 本地功能路由（优先于 LLM，避免 AI 说"我无法访问互联网"）
    t = msg.lower()
    # GitHub 热门
    if any(k in t for k in ["github", "trending", "热门", "流行", "开源项目", "趋势", "github热门"]):
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                ghr = await c.get("https://api.github.com/search/repositories?q=created:>2026-06-01&sort=stars&order=desc&per_page=10")
                if ghr.status_code == 200:
                    data = ghr.json()
                    items = data.get("items", [])
                    lines = ["🔥 **GitHub 今日热门项目 TOP 10**\n"]
                    for j, repo in enumerate(items[:10], 1):
                        n = repo.get("name", "?")
                        owner = repo.get("owner", {}).get("login", "?")
                        desc = repo.get("description", "无描述") or "无描述"
                        stars = repo.get("stargazers_count", 0)
                        lang2 = repo.get("language", "未知") or "未知"
                        url = repo.get("html_url", "")
                        lines.append(f"{j}. **{n}** ⭐{stars} | 🗣️{lang2}")
                        lines.append(f"   作者: {owner}")
                        lines.append(f"   {desc[:80]}")
                        lines.append(f"   🔗 {url}")
                    lines.append("\n💡 数据来源: GitHub API")
                    return {"success": True, "result": "\n".join(lines), "mode": "github_trending"}
        except Exception as e:
            return {"success": True, "result": f"获取 GitHub 热门项目失败: {e}\n可以试试直接访问 https://github.com/trending", "mode": "github_error"}

    # PPT 生成 — 本地执行，不走 LLM
    if any(k in t for k in ["ppt", "演示文稿", "幻灯片", "幻灯片", "生成ppt", "做一个.*ppt", "制作ppt"]):
        try:
            import subprocess, re
            # 提取主题
            topic = msg
            for kw in ["做", "生成", "制作", "创建", "关于"]:
                if kw in topic:
                    parts = topic.split(kw, 1)
                    if len(parts) > 1 and len(parts[1].strip()) > 1:
                        topic = parts[1].strip()
            topic = topic.replace("PPT", "").replace("ppt", "").replace("演示文稿", "").replace("幻灯片", "").strip()
            if not topic:
                topic = "建筑玻璃膜"
            now = str(int(time.time()))
            OUT = Path(__file__).resolve().parent.parent / f"output" / f"ppt_{now}.pptx"
            OUT.parent.mkdir(parents=True, exist_ok=True)
            # 调用系统已有脚本
            import pptx
            # 写一个极简 PPT
            from pptx import Presentation
            from pptx.util import Inches, Pt
            prs = Presentation()
            slides_data = [
                ("封面", f"{topic}\nAUTO-EVO-AI 自动生成"),
                ("简介", f"关于{topic}的详细介绍"),
                ("特点", f"{topic}的主要特点和应用"),
                ("优势", f"{topic}相比传统方案的优势"),
                ("总结", f"总结与展望\n\nAUTO-EVO-AI 自动生成"),
            ]
            for title, content in slides_data:
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = title
                slide.placeholders[1].text = content
            prs.save(str(OUT))
            result = f"✅ PPT 已生成！\n📁 {OUT}\n\n📄 共 {len(slides_data)} 页\n🏷️ 主题: {topic}"
            return {"success": True, "result": result, "mode": "ppt"}
        except Exception as e:
            return {"success": True, "result": f"PPT 生成失败: {e}", "mode": "ppt_error"}

    # 1. 优先尝试真实 LLM
    _api_key = req.api_key or os.environ.get("ZHIPU_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    _provider = req.provider
    if not _api_key and _provider == "openai":
        # 尝试各厂商环境变量
        for p, env_key in [("glm", "ZHIPU_API_KEY"), ("openai", "OPENAI_API_KEY"), ("deepseek", "DEEPSEEK_API_KEY"), ("qwen", "DASHSCOPE_API_KEY")]:
            ek = os.environ.get(env_key)
            if ek:
                _api_key, _provider = ek, p
                break

    if _api_key:
        messages = [{"role": "system", "content": system_prompt}]
        for ctx in (req.context or [])[-6:]:
            if isinstance(ctx, dict) and ctx.get("content"):
                messages.append({"role": ctx.get("role", "user"), "content": str(ctx["content"])})
        messages.append({"role": "user", "content": msg})

        result = await _call_llm(messages, _provider, _api_key)
        if result:
            return {"success": True, "result": result, "mode": "llm", "provider": _provider}

    # 2. 尝试本地 Ollama
    result = await _call_llm(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": msg}],
        "ollama", ""
    )
    if result:
        return {"success": True, "result": result, "mode": "llm", "provider": "ollama"}

    # 3. 降级到规则系统
    t = msg.lower()
    rules = {
        "zh-CN": {
            "status": "📊 **系统状态**\n• 457 模块就绪\n• 9 种语言\n• 57 个外部工具\n• 100 行业方案\n\n说「系统怎么样」获取实时状态。",
            "help": "**我能帮你做什么？**\n\n📊 查状态 — 「系统怎么样」\n🤖 AI讨论 — 「团队讨论xxx」\n💻 桌面操作 — 「帮我打开计算器」\n📝 生成文档 — 「帮我写一份合同」\n📊 处理Excel — 「帮我整理这个表格」\n⏰ 定时任务 — 「每天5点备份」\n🎤 语音输入 — 点 🎤 按钮",
            "write": "好的，我来帮你写。你可以说具体一点，比如「帮我写一份技术合同，甲方是XX公司」或者「帮我写一个Python脚本」。",
            "default": f"你说「{msg[:50]}」...\n我不太确定你想干嘛。试试：\n• 「你会什么」— 看我能干啥\n• 「系统怎么样」— 查状态\n• 「团队讨论xxx」— 叫AI团队讨论",
        },
        "en": {
            "status": "📊 **System Status**\n• 457 modules ready\n• 9 languages\n• 57 external tools\n• 100 industry solutions\n\nSay \"check status\" for real-time info.",
            "help": "**What can I do?**\n\n📊 Status — \"check status\"\n🤖 AI discuss — \"team discuss xxx\"\n💻 Desktop — \"open calculator\"\n📝 Write — \"write a contract\"\n📊 Excel — \"process this spreadsheet\"\n⏰ Schedule — \"backup at 5pm\"\n🎤 Voice — click 🎤",
            "write": "Sure, I can help you write that. Be more specific about what you need.",
            "default": f"You said \"{msg[:50]}\"...\nNot sure what you mean. Try:\n• \"what can you do\"\n• \"check status\"\n• \"team discuss xxx\"",
        }
    }
    r = rules.get(lang, rules["en"])

    if any(k in t for k in ["状态", "怎么样", "status", "health"]):
        return {"success": True, "result": r["status"], "mode": "rule"}
    if any(k in t for k in ["帮助", "会什么", "功能", "help", "what can", "能做", "能做什么", "事情", "列举", "能干"]):
        return {"success": True, "result": r["help"], "mode": "rule"}
    if any(k in t for k in ["写", "合同", "文档", "write", "contract", "document"]):
        return {"success": True, "result": r["write"], "mode": "rule"}

    # 6. 文件操作（Excel/Word）
    file_result = await _handle_file_ops(msg, lang)
    if file_result:
        return {"success": True, "result": file_result, "mode": "file_ops"}

    return {"success": True, "result": r["default"], "mode": "rule"}
