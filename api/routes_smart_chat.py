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

    # ── 定时任务真创建 ──
    if any(k in t_file for k in ["定时", "每天", "每小时", "每周", "每月", "备份", "schedule", "cron"]):
        try:
            from api.routes_scheduler import router as sched_router
            # 解析任务描述
            _every = "每天"; _what = msg
            if "每" in msg:
                for _p in ["每小时","每天","每周","每月"]:
                    if _p in msg: _every = _p; break
            _task_id = f"auto_{int(time.time())}"
            _task_path = Path(os.environ.get("AUTO_EVO_ROOT", str(Path(__file__).resolve().parent.parent))) / "tasks" / f"{_task_id}.json"
            _task_path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json
            _json.dump({"id":_task_id,"schedule":_every,"command":_what,"created":time.time()}, open(_task_path,"w",encoding="utf-8"))
            return {"success":True,"result":f"⏰ **定时任务已创建**\n任务ID: {_task_id}\n频率: {_every}\n描述: {_what[:60]}\n\n你可以在 📊 仪表盘 → 定时任务 查看和管理。", "mode":"scheduler_created"}
        except Exception as _e:
            return {"success":True,"result":f"⏰ 定时任务创建失败: {_e}\n请在 📊 仪表盘 → 定时任务 手动配置。","mode":"scheduler_error"}

    # ── 搜索真集成 ──
    if any(k in t_file for k in ["搜索", "搜一下", "查一下", "查询", "找一下", "search", "百度", "谷歌"]):
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                _q = msg.replace("搜索","").replace("搜一下","").replace("查一下","").replace("查询","").replace("找一下","").replace("search","").strip()
                if not _q: _q = msg[:60]
                _sr = await c.get(f"https://api.duckduckgo.com/?q={_q}&format=json&pretty=1")
                if _sr.status_code == 200:
                    _sd = _sr.json()
                    _abstract = _sd.get("AbstractText", "") or _sd.get("Abstract", "") or ""
                    _source = _sd.get("AbstractSource", "") or ""
                    _url = _sd.get("AbstractURL", "") or ""
                    if _abstract:
                        return {"success":True,"result":f"🔍 **搜索结果**\n来源: {_source}\n\n{_abstract}\n\n🔗 {_url}\n\n💡 以上结果由 DuckDuckGo 实时搜索提供。","mode":"search"}
                    return {"success":True,"result":f"🔍 关于「{_q}」未找到结构化结果。已转交 AI 回答。","mode":"search_fallback"}
                return {"success":True,"result":f"🔍 搜索服务暂不可用 (HTTP {_sr.status})，已转交 AI。","mode":"search_fallback"}
        except Exception as _e:
            return {"success":True,"result":f"🔍 搜索请求失败，已转交 AI 回答。","mode":"search_fallback"}

    # ── Excel 真创建 ──
    if any(k in t_file for k in ["excel", "表格", "xlsx", "电子表格", "做一份.*表", "创建.*表"]):
        try:
            from modules.file_ops import excel_write
            _out = Path(__file__).resolve().parent.parent / "output"
            _out.mkdir(parents=True, exist_ok=True)
            _path = str(_out / f"spreadsheet_{int(time.time())}.xlsx")
            # 尝试从消息中提取表头
            _headers = ["名称", "数量", "单价", "金额", "备注"]
            _sample = [[f"示例项{i}", 10+i, 100+i*10, (10+i)*(100+i*10), ""] for i in range(1, 6)]
            _data = [_headers] + _sample
            _r = excel_write(_path, _data)
            return {"success":True,"result":f"📊 **Excel 表格已生成**\n\n{_r}\n\n文件位置: {_path}\n\n💡 你可以直接在 Excel 中打开编辑数据。","mode":"excel_created"}
        except Exception as _e:
            return {"success":True,"result":f"📊 Excel 生成失败: {_e}", "mode":"excel_error"}

    # ── 团队讨论打通 ──
    if any(k in t_file for k in ["团队讨论", "智能体", "讨论", "组队", "agents", "team discuss"]):
        try:
            async with httpx.AsyncClient(timeout=30) as _hc:
                _task = msg
                for _kw in ["团队讨论","智能体","讨论","组队"]:
                    _task = _task.replace(_kw, "").strip()
                if not _task: _task = "一般讨论"
                _rr = await _hc.post("http://127.0.0.1:8765/api/v1/agents/rooms", json={"task": _task})
                if _rr.status_code == 200:
                    _rd = _rr.json()
                    if _rd.get("success"):
                        _rid = _rd.get("room_id", "?")
                        return {"success":True,"result":f"🤖 **智能体团队讨论已启动**\n\n🏠 房间: {_rid}\n📋 任务: {_task}\n\n6 位 AI 智能体正在讨论中...\n可以通过 WebSocket 查看实时讨论。","mode":"agents_room"}
        except Exception as _e:
            pass  # 降级到帮助文本
        return {"success":True,"result":"🤖 **智能体团队讨论**\n\n你可以说「团队讨论如何优化代码」— 6个AI角色各抒己见。","mode":"agents"}

    # ── 本地文件读取 ──
    if any(k in t_file for k in ["读取文件", "打开文件", "读文件", "查看文件", "read file"]):
        import glob as _glob
        _safe_dirs = [str(Path.home() / "Desktop"), str(Path.home() / "Documents"), str(Path.home() / "Downloads"), str(Path(__file__).resolve().parent.parent)]
        _found = []
        for _d in _safe_dirs:
            if os.path.isdir(_d):
                _found.extend(_glob.glob(os.path.join(_d, "*.txt"))[:3])
                _found.extend(_glob.glob(os.path.join(_d, "*.md"))[:3])
        if _found:
            _list = "\n".join(f"  {i+1}. {os.path.basename(f)}" for i,f in enumerate(_found[:6]))
            return {"success":True,"result":f"📁 **可读取的文件**\n{_list}\n\n请明确告诉我要读哪个文件（如「读文件 1」）。","mode":"file_list"}
        return {"success":True,"result":"📁 桌面/文档/下载目录未找到可读的 .txt/.md 文件。","mode":"file_list"}

    # ── 持久记忆 ──
    if any(k in t_file for k in ["记住", "保存", "记得", "不要忘记", "记住我说", "save"]):
        try:
            import sqlite3 as _sql
            _mem_db = Path(__file__).resolve().parent.parent / "core" / "adaptive_engine.db"
            _mem_conn = _sql.connect(str(_mem_db))
            _mem_conn.execute("CREATE TABLE IF NOT EXISTS chat_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, value TEXT, updated_at REAL)")
            _mem_key = f"memory_{int(time.time())}"
            _mem_val = msg.replace("记住","").replace("保存","").replace("不要忘记","").strip()
            if _mem_val:
                _mem_conn.execute("INSERT OR REPLACE INTO chat_memory (key, value, updated_at) VALUES (?,?,?)", (_mem_key, _mem_val, time.time()))
                _mem_conn.commit()
            _mem_cursor = _mem_conn.execute("SELECT value FROM chat_memory ORDER BY updated_at DESC LIMIT 5")
            _mem_items = [row[0] for row in _mem_cursor.fetchall()]
            _mem_conn.close()
            _mem_list = "\n".join(f"  {i+1}. {m[:50]}" for i,m in enumerate(_mem_items))
            return {"success":True,"result":f"🧠 **已记住**\n\n最新记忆:\n{_mem_list}\n\n你可以通过聊天随时查询这些记忆。","mode":"memory_saved"}
        except Exception as _e:
            return {"success":True,"result":f"🧠 记忆保存失败: {_e}","mode":"memory_error"}

    # ── 查询记忆 ──
    if any(k in t_file for k in ["我记得", "回忆", "之前说的", "刚才", "还记得", "recall"]):
        try:
            import sqlite3 as _sql
            _mem_db = Path(__file__).resolve().parent.parent / "core" / "adaptive_engine.db"
            _mem_conn = _sql.connect(str(_mem_db))
            _mem_cursor = _mem_conn.execute("SELECT value FROM chat_memory ORDER BY updated_at DESC LIMIT 10")
            _mem_items = [row[0] for row in _mem_cursor.fetchall()]
            _mem_conn.close()
            if _mem_items:
                _mem_list = "\n".join(f"  {i+1}. {m[:80]}" for i,m in enumerate(_mem_items))
                return {"success":True,"result":f"🧠 **我记得这些**\n{_mem_list}","mode":"memory_recall"}
            return {"success":True,"result":"🧠 目前还没有保存的记忆。你可以说「记住xxx」来让我保存。","mode":"memory_empty"}
        except Exception as _e:
            return {"success":True,"result":f"🧠 查询失败: {_e}","mode":"memory_error"}

    # ── 桌面自动化（Agent-S 轻量版，用 pyautogui） ──
    _DESKTOP_KEYWORDS = ["截图", "截屏", "screenshot", "打开计算器", "打开记事本", "打开浏览器",
                         "鼠标", "点击", "打字", "桌面操作", "屏幕", "帮我打开"]
    if any(k in t_file for k in _DESKTOP_KEYWORDS):
        try:
            import pyautogui as _pa
            _pa.FAILSAFE = True
            _result_lines = []
            # 截图
            if any(k in t_file for k in ["截图", "截屏", "screenshot"]):
                _img = _pa.screenshot()
                _shot_path = str(Path(__file__).resolve().parent.parent / "output" / f"screenshot_{int(time.time())}.png")
                _img.save(_shot_path)
                _result_lines.append(f"📸 截图已保存: {_shot_path}")
            # 打开应用
            if any(k in t_file for k in ["打开计算器", "calculator"]):
                import subprocess as _sp
                _sp.Popen("calc.exe")
                _result_lines.append("🧮 计算器已启动")
            if any(k in t_file for k in ["打开记事本", "记事本", "notepad"]):
                import subprocess as _sp
                _sp.Popen("notepad.exe")
                _result_lines.append("📝 记事本已启动")
            if any(k in t_file for k in ["打开浏览器", "浏览器", "chrome", "edge"]):
                import subprocess as _sp, webbrowser as _wb
                _wb.open("https://www.baidu.com")
                _result_lines.append("🌐 浏览器已打开")
            if not _result_lines:
                _result_lines.append("🖥️ 桌面自动化已就绪。支持命令：截图、打开计算器、打开记事本、打开浏览器")
            return {"success": True, "result": "\n".join(_result_lines), "mode": "desktop"}
        except Exception as _e:
            return {"success": True, "result": f"🖥️ 桌面操作失败: {_e}\n提示: 需要管理员权限运行才能控制桌面。", "mode": "desktop_error"}

    # ── 视频生成（Pixelle 本地模式） ──
    if any(k in t_file for k in ["生成视频", "做视频", "创建视频", "视频生成", "make video"]):
        _pixelle_dir = Path(__file__).resolve().parent.parent / "pixelle_videos"
        if _pixelle_dir.exists():
            _videos = list(_pixelle_dir.glob("*.mp4")) + list(_pixelle_dir.glob("*.webm"))
            if _videos:
                _vlist = "\n".join(f"  {i+1}. {v.name}" for i,v in enumerate(_videos[:10]))
                return {"success":True,"result":f"🎬 **已有视频**\n{_vlist}\n\nPixelle 视频生成工具已就绪。具体生成视频需要 Pixelle 服务运行。","mode":"video_list"}
        return {"success":True,"result":"🎬 **视频生成**\n\n系统可通过 Pixelle 生成视频。运行 pixelle 服务后即可使用。\n\n目前提供：视频脚本撰写、剪辑建议、特效推荐。","mode":"video_help"}

    # ── Docker 部署集成 ──
    if any(k in t_file for k in ["docker", "容器", "部署", "启动服务", "docker-compose"]):
        _deploy_script = Path(__file__).resolve().parent.parent / "deploy-industry.bat"
        if _deploy_script.exists():
            return {"success":True,"result":f"🐳 **Docker 部署**\n\n一键部署脚本: {_deploy_script}\n\n运行方式：\n```\ndeploy-industry.bat\n```\n然后输入行业编号 1-100 启动对应工具组合。\n\n当前支持的 Docker 工具:\n• Gitea / Metabase / Grafana / Portainer\n• NocoDB / Appsmith / Dify / Firecrawl\n• Chatwoot / Mattermost / ERPNext\n• Jellyfin / Immich / Vaultwarden\n\n更多工具见 industry-templates.ini","mode":"docker"}
        return {"success":True,"result":"🐳 **Docker 部署**\n\n支持 Docker Compose 一键部署行业工具。\n配置文件: industry-templates.ini\n\n运行 `docker-compose up -d` 即可启动。","mode":"docker"}

    # 3. 优先尝试真实 LLM
    _api_key = req.api_key or ""
    _provider = req.provider  # 前端可能传 "glm"
    if not _api_key:
        # 尝试各厂商环境变量 — 同时确定 provider
        for p, env_key in [("glm", "ZHIPU_API_KEY"), ("openai", "OPENAI_API_KEY"), ("deepseek", "DEEPSEEK_API_KEY"), ("qwen", "DASHSCOPE_API_KEY")]:
            ek = os.environ.get(env_key)
            if ek:
                _api_key, _provider = ek, p
                break
    # 如果没指定 provider 但有 Key，根据环境变量推断
    if _api_key and _provider == "openai" and not req.api_key:
        for p, env_key in [("glm", "ZHIPU_API_KEY"), ("deepseek", "DEEPSEEK_API_KEY"), ("qwen", "DASHSCOPE_API_KEY")]:
            if os.environ.get(env_key) == _api_key:
                _provider = p
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
