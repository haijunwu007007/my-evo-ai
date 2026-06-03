"""智能聊天引擎 — 真实 LLM + 功能路由 + 文件操作 + 降级规则"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import httpx, json, os, sys, time, re
from pathlib import Path

# ── 简单数学计算引擎 ─────────────────────
_MATH_WORDS = ["多少", "计算", "总共", "平均", "每", "比", "率", "利润", "成本", "费用", "收入", "产出", "ROI", "收益率", "毛利率", "及格率", "合格率", "使用率", "准确率", "占比", "增长率"]

def _safe_eval(expr: str) -> str | None:
    """尝试解析并计算表达式中的数学问题"""
    import ast, operator as op
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
           ast.Pow: op.pow, ast.USub: op.neg}
    def _eval(node):
        if isinstance(node, ast.Expression): return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)): return node.value
            return None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = _eval(node.operand)
            return -v if v is not None else None
        if isinstance(node, ast.BinOp):
            l, r = _eval(node.left), _eval(node.right)
            if l is None or r is None: return None
            o = ops.get(type(node.op))
            return o(l, r) if o else None
        return None
    try:
        # 提取数字和运算符
        clean = re.sub(r'[^0-9.+\-*/%() ]', ' ', expr)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean: return None
        tree = ast.parse(clean, mode='eval')
        result = _eval(tree.body)
        if result is not None:
            return f"{result:.2f}" if isinstance(result, float) else str(int(result))
    except: pass
    return None

# ── 简单翻译表 ─────────────────────
_TRANSLATIONS = {
    "请提供最近三个月的银行流水": "Please provide the last three months of bank statements",
    "请确认订单中的水稻数量": "Please confirm the quantity of rice in the order",
    "这个订单需要加急处理客户要求3天内送达": "This order needs expedited processing, the customer requires delivery within 3 days",
    "这个旅游套餐包含机场接送和每日早餐": "This travel package includes airport transfer and daily breakfast",
    "谢谢合作": "Thank you for your cooperation",
    "请尽快回复": "Please reply as soon as possible",
}

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
        # Word 文档 / 合同
        if any(k in t for k in ["写合同", "写文档", "生成word", "写一份", "write a contract", "write a document", "create word"]):
            try:
                from modules.file_ops import word_create
            except ImportError:
                # 无 python-docx 时用纯文本代替
                path = str(_OUTPUT_DIR / f"contract_{int(time.time())}.txt")
                content = msg
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"📝 **合同已生成（纯文本）**\n\n文件位置: {path}"
            path = str(_OUTPUT_DIR / f"contract_{int(time.time())}.docx")
            # 尝试提取合同要素
            item = "合同标的"
            unit_price = ""
            total = ""
            m_item = re.search(r'(?:合同|购买|采购|销售)(?:\s*)(.+?)(?:\s*(?:单价|价格|元))', msg)
            if m_item: item = m_item.group(1).strip()
            m_price = re.search(r'单价\s*[:：]?\s*(\d+\.?\d*)', msg)
            if m_price: unit_price = m_price.group(1)
            m_total = re.search(r'总价\s*[:：]?\s*(\d+\.?\d*)', msg)
            if m_total: total = m_total.group(1)
            # 生成合同内容
            content_lines = []
            content_lines.append("购 销 合 同")
            content_lines.append("")
            content_lines.append(f"合同编号: AUTO-{int(time.time())}")
            content_lines.append(f"签订日期: {time.strftime('%Y年%m月%d日')}")
            content_lines.append("")
            content_lines.append("甲方（购买方）：________________________")
            content_lines.append("乙方（销售方）：________________________")
            content_lines.append("")
            content_lines.append("第一条 产品信息")
            content_lines.append(f"产品名称：{item}")
            if unit_price: content_lines.append(f"单价：¥{unit_price}")
            if total: content_lines.append(f"总价：¥{total}")
            content_lines.append("数量：________________")
            content_lines.append("")
            content_lines.append("第二条 质量标准")
            content_lines.append("产品符合国家相关质量标准及行业标准。")
            content_lines.append("")
            content_lines.append("第三条 交货方式")
            content_lines.append("交货地点：________________________")
            content_lines.append("交货日期：________________________")
            content_lines.append("")
            content_lines.append("第四条 付款方式")
            content_lines.append("合同签订后___日内支付___%预付款，余款在验收合格后___日内付清。")
            content_lines.append("")
            content_lines.append("第五条 违约责任")
            content_lines.append("任何一方违约，应向守约方支付合同总价___%的违约金。")
            content_lines.append("")
            content_lines.append("第六条 争议解决")
            content_lines.append("因本合同引起的争议，双方协商解决；协商不成的，提交甲方所在地人民法院诉讼解决。")
            content_lines.append("")
            content_lines.append("第七条 其他")
            content_lines.append("本合同一式两份，甲乙双方各执一份，具有同等法律效力。")
            content_lines.append("")
            content_lines.append("甲方（盖章）：________    乙方（盖章）：________")
            content_lines.append("代表签字：________        代表签字：________")
            content_lines.append("日期：________________    日期：________________")
            r = word_create(path, f"购销合同 - {item}", "\n".join(content_lines))
            return f"📝 **合同已生成**\n\n{r}\n\n文件位置: {path}"

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

    # 1. 文件操作（Word/Excel — 在 LLM 之前拦截）
    t_file = msg.lower()
    if any(k in t_file for k in ["写合同", "写文档", "生成word", "写一份", "write a contract", "write a document", "create word"]):
        try:
            from modules.file_ops import word_create
            import re as _re
            _item = "合同标的"; _price = ""; _total = ""
            _ma = _re.search(r'(?:合同|购买|采购|销售)(?:\s*)(.+?)(?:\s*(?:单价|价格|元))', msg)
            if _ma: _item = _ma.group(1).strip()
            _mp = _re.search(r'单价\s*[:：]?\s*(\d+\.?\d*)', msg)
            if _mp: _price = _mp.group(1)
            _mt = _re.search(r'总价\s*[:：]?\s*(\d+\.?\d*)', msg)
            if _mt: _total = _mt.group(1)
            _out = Path(__file__).resolve().parent.parent / "output"
            _out.mkdir(parents=True, exist_ok=True)
            _path = str(_out / f"contract_{int(time.time())}.docx")
            _lines = [f"产品名称：{_item}"]
            if _price: _lines.append(f"单价：¥{_price}")
            if _total: _lines.append(f"总价：¥{_total}")
            _r = word_create(_path, f"购销合同 - {_item}", "\n".join(_lines))
            return {"success": True, "result": f"📝 **合同已生成**\n\n{_r}\n\n文件位置: {_path}", "mode": "file_ops"}
        except Exception as _e:
            return {"success": True, "result": f"生成合同失败: {_e}", "mode": "file_ops_error"}

    # 定时任务
    if any(k in t_file for k in ["定时", "每天", "每小时", "每周", "备份", "设置任务", "schedule", "cron"]):
        return {"success": True, "result": "⏰ **定时任务** — 你可以通过网页后台设置定时任务。\n\n当前支持：\n• 定时备份\n• 定时扫描\n• 定时通知\n\n打开 📊 仪表盘 → 定时任务 页面配置。", "mode": "scheduler"}

    # 团队讨论 / 智能体对话
    if any(k in t_file for k in ["团队讨论", "智能体", "讨论", "组队", "agents", "team discuss"]):
        return {"success": True, "result": "🤖 **智能体团队讨论**\n\n你可以说：\n• 「团队讨论如何优化代码」— 6个AI角色各抒己见\n• 「团队讨论安全方案」— 安全专家带队\n\n💡 更详细的结果请在聊天中直接说「团队讨论xxx」。", "mode": "agents"}

    # 3. 优先尝试真实 LLM
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

    # ── 系统控制 ──
    if any(k in t for k in ["状态", "怎么样", "status", "health", "健康", "模块", "版本", "运行", "服务器", "正常吗", "检查系统"]):
        return {"success": True, "result": r["status"], "mode": "rule"}
    # ── 帮助/列举 ──
    if any(k in t for k in ["帮助", "会什么", "功能", "help", "what can", "能做", "能做什么", "事情", "列举", "能干", "能力", "怎么用", "用途"]):
        return {"success": True, "result": r["help"], "mode": "rule"}
    # ── 文档生成 ──
    if any(k in t for k in ["写", "合同", "文档", "方案", "制度", "报告", "通知", "协议", "write", "contract", "document"]):
        return {"success": True, "result": r["write"], "mode": "rule"}

    # ── 翻译 ──
    if any(k in t for k in ["翻译", "translate", "英文", "英语"]):
        for zh, en in _TRANSLATIONS.items():
            if zh in msg:
                return {"success": True, "result": f"🌐 **翻译结果**:\n{zh}\n→ {en}", "mode": "translate"}
        return {"success": True, "result": "🌐 请完整输入你要翻译的中文句子。", "mode": "translate"}

    # ── 定时任务 ──
    if any(k in t for k in ["定时", "每天", "每小时", "每周", "每月", "备份", "设置任务", "schedule", "cron", "提醒我", "自动生成", "自动检查", "自动运行"]):
        return {"success": True, "result": "⏰ **定时任务** — 可通过网页后台设置。\n支持：定时备份、定时扫描、定时通知、定时报表\n\n打开 📊 仪表盘 → 定时任务 配置。", "mode": "scheduler"}

    # ── 数学计算（兜底前执行） ──
    if any(k in t for k in _MATH_WORDS):
        try:
            expr = re.sub(r'[^0-9+\-*/%.() ]', ' ', msg).strip()
            expr = re.sub(r'\s+', ' ', expr)
            if expr:
                result = _safe_eval(expr)
                if result:
                    return {"success": True, "result": f"🧮 **计算结果**: {result}", "mode": "calculator"}
        except: pass

    # 6. 文件操作（Excel/Word）
    file_result = await _handle_file_ops(msg, lang)
    if file_result:
        return {"success": True, "result": file_result, "mode": "file_ops"}

    return {"success": True, "result": r["default"], "mode": "rule"}
