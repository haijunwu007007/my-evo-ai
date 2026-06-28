"""智能体路由 — ReAct 架构：Thought → Action → Observe"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, json, asyncio
from core.logging_config import get_logger
logger = get_logger("evo.api.smart")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []

# ── 意图分类模板（ReAct风格：先思考再行动）──
_INTENT_PROMPT = """你是智能路由分析器。分析用户问题，返回JSON。不要加额外解释。

规则：
- intent: chat/hot/search/create/help/calculate
  - chat: 普通聊天、问答、写作、解释、建议、闲聊、天气、情感、角色扮演、系统介绍
  - hot: 查热点/热搜/热榜/头条/新闻/大事/新鲜事（如果提到具体平台，platform填平台名）
  - search: 明确说搜索xx、查找xx、搜一下xx、查一下xx（想找具体信息）
  - create: 生成文档/PPT/Excel/合同/报告/代码/文章/方案
  - help: 问系统能做什么、有什么功能、怎么使用、能力列表
  - calculate: 数学计算、算术、运算、数字计算（含数字和运算符的表达式计算）
- platform: 如果intent=hot且用户提到具体平台(百度/微博/抖音/知乎/B站/头条/腾讯/贴吧/小红书)，填平台名。否则""
- topic: 搜索主题或热点话题
- thought: 你分析用户意图的原因（一句话）

例1: q=今日百度热点 → {"intent":"hot","platform":"百度","topic":"","thought":"用户想查看百度热搜"}
例2: q=抖音热搜 → {"intent":"hot","platform":"抖音","topic":"","thought":"用户想看抖音热点"}
例3: q=腾讯微博今日热点 → {"intent":"hot","platform":"微博","topic":"","thought":"用户提到腾讯微博，其实是微博平台"}
例4: q=知乎热榜 → {"intent":"hot","platform":"知乎","topic":"","thought":"用户想看知乎热门话题"}
例5: q=今天有什么新闻 → {"intent":"hot","platform":"","topic":"新闻","thought":"用户想看通用新闻热点"}
例6: q=最近有什么大事 → {"intent":"hot","platform":"","topic":"大事","thought":"用户想了解近期重要事件"}
例7: q=B站热搜 → {"intent":"hot","platform":"B站","topic":"","thought":"B站弹幕网的热搜"}
例8: q=小红书热门 → {"intent":"hot","platform":"小红书","topic":"","thought":"小红书的热门内容"}
例9: q=搜索 python教程 → {"intent":"search","platform":"","topic":"python教程","thought":"用户明确说搜索"}
例10: q=帮我查一下北京的天气 → {"intent":"search","platform":"","topic":"北京天气","thought":"用户要查具体信息"}
例11: q=搜一下人工智能最新动态 → {"intent":"search","platform":"","topic":"人工智能最新动态","thought":"用户用\"搜一下\"关键词"}
例12: q=本系统可以做什么 → {"intent":"help","platform":"","topic":"","thought":"用户问系统功能"}
例13: q=你会什么 → {"intent":"help","platform":"","topic":"","thought":"用户想知道AI的能力"}
例14: q=如何使用这个系统 → {"intent":"help","platform":"","topic":"","thought":"用户问使用方式"}
例15: q=你好 → {"intent":"chat","platform":"","topic":"","thought":"普通打招呼"}
例16: q=帮我写一份合同 → {"intent":"create","platform":"","topic":"合同","thought":"用户要生成文档"}
例17: q=做个PPT → {"intent":"create","platform":"","topic":"PPT","thought":"用户要生成PPT"}
例18: q=今天天气怎么样 → {"intent":"chat","platform":"","topic":"","thought":"闲聊类问题，LLM直接回答"}
例19: q=我心情不好 → {"intent":"chat","platform":"","topic":"","thought":"情感支持类对话"}
例20: q=帮我分析一下这个数据 → {"intent":"chat","platform":"","topic":"","thought":"用户需要分析，走LLM"}
例21: q=系统的架构是怎样的 → {"intent":"chat","platform":"","topic":"","thought":"用户问系统技术细节"}
例22: q=中午吃什么 → {"intent":"chat","platform":"","topic":"","thought":"闲聊建议类"}
例23: q=杭州亚运会 → {"intent":"chat","platform":"","topic":"","thought":"不含搜索/热点关键词，走LLM回答"}
例24: q=王宝强新电影 → {"intent":"chat","platform":"","topic":"","thought":"不含明确搜索词，LLM直接回答"}
例25: q=给我讲个笑话 → {"intent":"chat","platform":"","topic":"","thought":"娱乐聊天"}
例26: q=你是用什么模型 → {"intent":"chat","platform":"","topic":"","thought":"用户问AI的技术背景"}
例27: q=李子柒现在怎么样了 → {"intent":"chat","platform":"","topic":"","thought":"关于个人的问题"}
例28: q=帮我做一个Excel表格 → {"intent":"create","platform":"","topic":"Excel表格","thought":"用户要生成Excel"}
例29: q=生成季度报告 → {"intent":"create","platform":"","topic":"季度报告","thought":"用户要生成报告"}
例30: q=写一段Python代码 → {"intent":"create","platform":"","topic":"Python代码","thought":"用户要生成代码"}
例31: q=请帮我查询今日头条热点 → {"intent":"hot","platform":"头条","topic":"","thought":"用户明确说今日头条"}
例32: q=贴吧热榜 → {"intent":"hot","platform":"贴吧","topic":"","thought":"贴吧的热门帖子"}
例33: q=网易新闻热点 → {"intent":"hot","platform":"网易","topic":"","thought":"网易新闻热榜"}
例34: q=有什么新鲜事 → {"intent":"hot","platform":"","topic":"新鲜事","thought":"用户想看近期发生的事"}
例35: q=hacker news hot → {"intent":"hot","platform":"Hacker News","topic":"","thought":"英文技术社区热点"}
例36: q=reddit热门 → {"intent":"hot","platform":"Reddit","topic":"","thought":"Reddit热门话题"}
例37: q=数学计算: 2+3*4 → {"intent":"calculate","expression":"2+3*4","thought":"用户要求数学计算"}
例38: q=100/5+3等于多少 → {"intent":"calculate","expression":"100/5+3","thought":"用户问算术题"}
例39: q=计算 1024*768 → {"intent":"calculate","expression":"1024*768","thought":"用户要求做乘法"}
例40: q=(15+3)*2-10 → {"intent":"calculate","expression":"(15+3)*2-10","thought":"用户给了一个数学表达式"}

现在分析: q="""


# ── 系统能力描述（LLM回复时用来介绍自己）──
_SYSTEM_CAPABILITIES = """**我能做什么：**
1. 💬 **聊天问答** — 任何问题直接问，我直接回答
2. 🔍 **搜索信息** — 说"搜索: xxx"或"帮我查一下xxx"
3. 🔥 **热搜热点** — 说"今日xx热点"（百度/微博/抖音/知乎/B站/头条等）
4. 📄 **生成文档** — PPT/Excel/合同/报告/代码，说"帮我做一个xxx"
5. 🎤 **语音输入** — 按住🎤说话，自动识别
6. 🧠 **记忆功能** — 说"记住xxx"或"回忆xxx"
7. 📅 **定时任务** — 说"每天早上9点xxx"
8. 🛠️ **系统诊断** — 说"查看系统状态"
9. 👥 **266位专家** — 点左侧专家列表，切换角色对话
10. 📊 **数据分析** / 🐳 **Docker操作** / 🌐 **翻译翻译**

**直接说你想要什么，我来搞定。**"""


async def _classify_intent(msg: str):
    """ReAct 阶段1: 智能意图分类（Thought）"""
    from api.agent_llm import call_llm
    prompt = _INTENT_PROMPT + msg[:120]
    for _ in range(2):
        try:
            text, _ = call_llm([{"role": "user", "content": prompt}], timeout=8)
            if not text:
                continue
            # 提取JSON
            cleaned = text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            d = json.loads(cleaned)
            itype = d.get("intent", "chat")
            platform = d.get("platform", "")
            topic = d.get("topic", "")
            thought = d.get("thought", "")
            expression = d.get("expression", "")
            logger.info(f"[INTENT] {msg[:40]} -> {itype} platform={platform} topic={topic} expression={expression[:20]} thought={thought}")
            return itype, platform, topic, expression
        except Exception as e:
            logger.warning(f"[INTENT] retry: {e}")
            continue
    # 兜底：chat
            logger.info(f"[INTENT] fallback chat for: {msg[:40]}")
    return "chat", "", "", ""


async def _execute_search(query: str, count: int = 8):
    """执行搜索"""
    from skills.builtin.search_web import execute as _search
    try:
        r = _search({"query": query, "count": count})
        items = r.get("results", [])
        if items:
            txt = f"🔍 **搜索结果：{query[:30]}**\n\n"
            seen = set()
            for i, item in enumerate(items[:count]):
                t = item.get("title", "")[:60]
                u = item.get("url", "")
                if t and t not in seen:
                    seen.add(t)
                    txt += f"**{i+1}.** [{t}]({u})\n"
            return txt
    except Exception as e:
        logger.warning(f"[SEARCH] error: {e}")
    return None


async def _answer_hot(msg: str, platform: str, topic: str):
    """处理热点查询 — 先用LLM回答，搜索兜底"""
    # 先用LLM回答
    from api.agent_llm import call_llm
    try:
        platform_desc = platform if platform else "今天的"
        sp = f"用户问: {msg}。请列出{platform_desc}的热点话题5-8条，每条用数字开头。不用搜索，直接按你知道的列出来。不要加\"根据我的知识库\"这类话。"
        content, _ = call_llm([{"role": "user", "content": sp}], timeout=15)
        if content:
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            hot_lines = [l for l in lines if any(c.isdigit() for c in l[:4])]
            if hot_lines:
                tag = platform if platform else "今日"
                txt = f"🔥 **{tag}热点**\n\n" + "\n".join(hot_lines[:8])
                return txt
    except:
        pass

    # 搜索兜底
    search_query = f"{platform or ''} {topic or '热点'} 今日热搜最新"
    result = await _execute_search(search_query.strip())
    if result:
        return result

    return None


async def _try_llm_chat(msg: str, system_hint: str = ""):
    """LLM直接回答"""
    from api.agent_llm import call_llm
    try:
        if system_hint:
            prompt = f"{system_hint}\n\n用户: {msg}\n回答:"
        else:
            prompt = f"用户: {msg}\n\n请直接回答，简洁、有用。"
        content, _ = call_llm([{"role": "user", "content": prompt}], timeout=20)
        if content and len(content) > 3:
            return content
    except:
        pass
    return None


@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    if not msg:
        return {"success": True, "result": "请说点什么"}

    # ── ReAct 阶段1: Thought（意图分类）──
    itype, platform, topic, expression = await _classify_intent(msg)
    logger.info(f"[ROUTE] {itype} p={platform} t={topic} e={expression[:20]}")

    # ── ReAct 阶段2: Action（执行）──

    # hot: 热点查询
    if itype == "hot":
        result = await _answer_hot(msg, platform, topic)
        if result:
            return {"success": True, "result": result}
        # 兜底：LLM试一下
        fallback = await _try_llm_chat(msg, "用户想查热点。列出你知道的热点话题，5条左右。")
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": "暂无热点数据，稍后再试"}

    # search: 搜索
    if itype == "search":
        result = await _execute_search(topic or msg)
        if result:
            return {"success": True, "result": result}
        # 搜索失败→LLM
        fallback = await _try_llm_chat(msg)
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": "搜索超时，稍后再试"}

    # help: 系统能力
    if itype == "help":
        return {"success": True, "result": _SYSTEM_CAPABILITIES}

    # calculate: 数学计算
    if itype == "calculate":
        expr = (expression or topic or msg).strip()
        import re as _re_calc
        clean = ''.join(_re_calc.findall(r'[\d+\-*/().% ]+', expr)).strip()
        if not clean or len(clean) < 2:
            nums = _re_calc.findall(r'[\d+\-*/().% ]+', msg)
            clean = max(nums, key=len).strip() if nums else ""
        # 只去空格，括号必须保留
        clean = clean.strip()
        if len(clean) >= 2:
            try:
                ns = {"__builtins__": {}}; exec(compile(f"_r={clean}", "", "exec"), ns)
                val = ns.get("_r")
                if isinstance(val, (int, float)):
                    return {"success": True, "result": f"📐 **{clean} = {val}**"}
            except Exception as _ce:
                logger.warning(f"[CALC] exec fail: {_ce}")
            try:
                import ast, operator
                ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
                def _se(n):
                    if isinstance(n, ast.Constant): return n.value
                    if isinstance(n, ast.BinOp): return ops[type(n.op)](_se(n.left), _se(n.right))
                    if isinstance(n, ast.UnaryOp): return operator.neg(_se(n.operand))
                    raise ValueError
                val = _se(ast.parse(clean, mode='eval').body)
                return {"success": True, "result": f"📐 **{clean} = {val}**"}
            except Exception as _ce:
                logger.warning(f"[CALC] ast fail: {_ce}")
        fallback = await _try_llm_chat(f"计算一下: {expr}")
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": f"📐 {expr} 无法计算"}

    # create: 生成文档/代码
    if itype == "create":
        from api.agent_core import create_engine
        eng = create_engine(BASE, BASE/"output", BASE/"output"/"tools", BASE/"data"/"agent_memory.db")
        try:
            r = await asyncio.to_thread(eng, msg, "", "zh-CN", [])
            if isinstance(r, dict):
                result = r.get("result", "") or ""
                if result:
                    return {"success": True, "result": result}
        except:
            pass
        # 降级到LLM
        fallback = await _try_llm_chat(msg)
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": "处理中..."}

    # chat: LLM直接回答
    result = await _try_llm_chat(msg)
    if result:
        return {"success": True, "result": result}
    # 超时再试
    result = await _try_llm_chat(msg)
    if result:
        return {"success": True, "result": result}
    return {"success": True, "result": "正在思考中..."}


@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    return await smart_chat(req)


@router.get("/api/v1/llm/status")
async def llm_status():
    from api.agent_llm import get_active_model
    return get_active_model()
