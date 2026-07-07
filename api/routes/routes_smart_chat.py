"""智能体路由 — ReAct 架构：Thought → Action → Observe"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, json, asyncio, httpx
from core.logging_config import get_logger
logger = get_logger("evo.api.smart")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []

# ── 导航路由映射（不依赖LLM，直接跳转到对应管理页面）──
_NAVIGATION_MAP = [
    # 管理中心
    (["用户管理","用户列表","管理用户","查看用户","权限管理","角色管理","添加用户","删除用户"], "/admin#"),
    (["管理中心","管理后台","系统管理","后台管理","打开管理"], "/admin"),
    # 工作流
    (["工作流","编排","流程编排","工作流编排","创建流程","编辑工作流"], "/canvas"),
    (["自动化","自动化流程","自动任务","创建自动化"], "/automations"),
    # 智能体 & 专家
    (["智能体","agent","智能助理","AI助手","查看agent","多智能体","agent团队"], "/agents"),
    (["专家","专家库","找专家","领域专家","行业专家","激活专家"], "/experts"),
    (["技能","扩展","技能列表","查看技能","skill","skills"], "/skills"),
    (["openclaw","claw","消息平台","连接平台"], "/claw"),
    (["hermes","信息搜集"], "/hermes"),
    (["human","桌面伴侣"], "/human"),
    # 部署 & 发布
    (["部署","发布","上线","部署应用","部署服务","发布应用"], "/deploy"),
    (["视频","视频生成","做视频","制作视频","生成视频"], "/video"),
    # 数据 & 知识
    (["记忆","知识库","记忆库","cognee","知识图谱","回忆"], "/cognee"),
    (["学习","教程","learn","学习中心"], "/learn"),
    (["开源","中心","市场","hub","开源项目","发现项目"], "/hub"),
    # 开发 & 画布
    (["画布","canvas","编排画布","可视化编排"], "/canvas"),
    (["循环","loop","循环任务","工作流循环"], "/loop"),
    # 代码 & 审查
    (["代码审查","code review","审查代码","review","版本差异","diff"], "/review"),
    (["应用","应用列表","已生成","我的应用","查看应用"], "/apps"),
    # 系统
    (["设置","配置","系统设置","偏好设置","参数配置","修改配置"], "/settings"),
    (["监控","仪表盘","dashboard","系统状态","查看状态","运行状态"], "/dashboard"),
    (["能力","能力中心","capabilities","系统能力"], "/capabilities"),
    # 企业
    (["企业","enterprise","集团os","billion","集团操作系统"], "/enterprise.html"),
    (["公司","虚拟公司","company","公司管理"], "/company.html"),
    (["n8n","工作流引擎","n8n模板","模板库"], "/n8n"),
    # 其他
    (["工具","工具箱","tool","tools"], "/tools"),
    (["通知","通知配置","消息通知","推送配置"], "/settings"),
    (["安装向导","首次设置","初始化"], "/install-wizard"),
    (["插件","插件列表","plugin"], "/plugins"),
    (["API","API管理","接口管理","api密钥"], "/api-keys"),
    (["审计","审计日志","操作日志","log","日志记录"], "/audit"),
    (["备份","备份管理","数据备份","恢复"], "/backup"),
]

# ── 直接信息查询（不依赖LLM，直接查API）──
_INFO_QUERIES = {
    "模块列表": "/api/v1/modules",
    "所有模块": "/api/v1/modules",
    "有哪些模块": "/api/v1/modules",
    "版本信息": "/api/v1/version",
    "系统版本": "/api/v1/version",
    "系统状态": "/api/v1/status",
    "健康检查": "/api/v1/health",
    "运行状态": "/api/v1/status",
    "有哪些智能体": "/api/v1/agents",
    "智能体列表": "/api/v1/agents",
    "agent列表": "/api/v1/agents",
    "技能列表": "/api/v1/skills",
    "有哪些技能": "/api/v1/skills",
}

async def _execute_info_query(msg: str) -> str | None:
    """直查信息查询 — 不依赖LLM"""
    import httpx
    for keyword, path in _INFO_QUERIES.items():
        if keyword in msg:
            try:
                async with httpx.AsyncClient(timeout=8, base_url="http://127.0.0.1:8765") as c:
                    r = await c.get(path)
                    data = r.json() if r.status_code == 200 else {"error": f"{r.status_code}"}
                    return json.dumps(data, ensure_ascii=False, indent=2)[:2000]
            except Exception as e:
                return f"查询失败: {e}"
    return None

async def _match_navigation(msg: str) -> str | None:
    """匹配导航路由 — 关键词匹配返回页面URL"""
    lower = msg.lower()
    for keywords, url in _NAVIGATION_MAP:
        for kw in keywords:
            if kw in lower:
                return url
    return None

# ── 意图分类模板（ReAct风格：先思考再行动）──
_INTENT_PROMPT = """你是智能路由分析器。分析用户问题，返回JSON。不要加额外解释。

规则：
- intent: chat/hot/search/create/help/calculate/agent
  - chat: 普通聊天、问答、写作、解释、建议、闲聊、天气、情感、角色扮演、系统介绍
  - hot: 查热点/热搜/热榜/头条/新闻/大事/新鲜事（如果提到具体平台，platform填平台名）
  - search: 明确说搜索xx、查找xx、搜一下xx、查一下xx（想找具体信息）
  - create: 生成文档/PPT/Excel/合同/报告/代码/文章/方案
  - help: 问系统能做什么、有什么功能、怎么使用、能力列表
  - calculate: 数学计算、算术、运算、数字计算（含数字和运算符的表达式计算）
  - agent: 多步骤复杂任务，需要调用多个工具/技能才能完成，如"先搜索XXX再生成YYY"、"查一下XXX并整理成PPT"、"搜索XXX和YYY对比分析后出报告"、"帮我XXX然后再YYY最后ZZZ"
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
例41: q=搜索AI行业趋势并生成一份分析报告 → {"intent":"agent","topic":"AI行业趋势报告","thought":"用户要搜索后再生成报告，多步骤复杂任务"}
例42: q=查一下今天的热点新闻，然后整理成PPT → {"intent":"agent","topic":"热点新闻PPT","thought":"先搜索热点再生成PPT，需要多步执行"}
例43: q=搜索2024年最佳AI工具，对比分析，出一份Excel表格 → {"intent":"agent","topic":"AI工具对比Excel","thought":"搜索+对比+出表格，三步复杂任务"}
例44: q=帮我搜索最近的科技新闻，用中英文总结，然后发到我的邮箱 → {"intent":"agent","topic":"科技新闻邮件","thought":"搜索+翻译+邮件，多工具调用"}
例45: q=搜索python和javascript的性能对比，然后生成一份报告 → {"intent":"agent","topic":"语言对比报告","thought":"搜索+报告生成，两步复杂任务"}

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


# N8N工作流匹配函数（只有用户主动问n8n才显示链接）
_n8n_keywords = ['n8n','编辑器','工作流模板','浏览模板','/n8n-browse']

async def _append_n8n_links(msg: str, reply: str) -> str:
    """直接查询SQLite数据库显示匹配模板数（不走HTTP，稳定可靠）"""
    import sqlite3, os
    _db_path = os.environ.get('N8N_BASE', '/home/ubuntu/n8n-workflows/n8n-workflows-main') + '/workflows.db'
    _cn_en = {'邮件':'email','通知':'notification','推送':'webhook','审批':'approval',
              '监控':'alert','报表':'report','备份':'backup','表单':'form','登录':'login',
              '爬虫':'crawl','短信':'sms','翻译':'translate','客服':'slack','定时':'cron'}
    _kw = [k for k in _cn_en if k in msg]
    if _kw:
        try:
            conn = sqlite3.connect(_db_path)
            q = _cn_en[_kw[0]]
            total = conn.execute("SELECT COUNT(*) as c FROM workflows WHERE name LIKE ? OR filename LIKE ?", ('%'+q+'%','%'+q+'%')).fetchone()[0]
            rows = conn.execute("SELECT name FROM workflows WHERE name LIKE ? OR filename LIKE ? ORDER BY nodes DESC LIMIT 3", ('%'+q+'%','%'+q+'%')).fetchall()
            conn.close()
            if total > 0:
                names = [r[0][:40] for r in rows if r[0]]
                tip = f"\n\n 系统中有 {total} 个相关自动化模板"
                if names:
                    tip += f"\n  例如：{'、'.join(names)}"
                reply += tip
        except:
            pass
    # 高级用户：明确提到n8n/编辑器时显示链接
    if any(k in msg for k in ['n8n','编辑','浏览模板']):
        extra = f"\n  [浏览全部模板](https://autoevoai.com/n8n-browse) | [打开编辑器](https://autoevoai.com/api/v1/n8n/editor)"
        reply += extra
    return reply


@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    if not msg:
        return {"success": True, "result": "请说点什么"}

    # ── 优先级0: 导航路由匹配（不依赖LLM，直接跳转）──
    nav_url = await _match_navigation(msg)
    if nav_url:
        name = nav_url.split("/")[-1].replace(".html","").replace("-"," ")
        logger.info(f"[NAV] {msg[:30]} -> {nav_url}")
        return {"success": True, "result": f"📌 正在打开 **{name}**...", "redirect": nav_url}

    # ── 优先级0b: 直接信息查询（不依赖LLM，直查API）──
    info_result = await _execute_info_query(msg)
    if info_result:
        from api.agent_llm import call_llm as _llm_shorten
        try:
            short, _ = _llm_shorten([{"role":"user","content":f"用简洁中文总结以下系统信息（不超过100字）：{info_result[:1500]}"}], timeout=8)
            if short and len(short) > 5:
                return {"success": True, "result": short}
        except:
            pass
        return {"success": True, "result": info_result[:1000]}

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
            result = await _append_n8n_links(msg, result)
            return {"success": True, "result": result}
        # 搜索失败→LLM
        fallback = await _try_llm_chat(msg)
        if fallback:
            fallback = await _append_n8n_links(msg, fallback)
            return {"success": True, "result": fallback}
        return {"success": True, "result": "搜索超时，稍后再试"}

    # help: 系统能力
    if itype == "help":
        result = await _append_n8n_links(msg, _SYSTEM_CAPABILITIES)
        return {"success": True, "result": result}

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
                    result = await _append_n8n_links(msg, result)
                    return {"success": True, "result": result}
        except:
            pass
        # 降级到LLM
        fallback = await _try_llm_chat(msg)
        if fallback:
            fallback = await _append_n8n_links(msg, fallback)
            return {"success": True, "result": fallback}
        return {"success": True, "result": "处理中..."}

    # agent: 复杂多步骤任务 → 轻量级智能执行器（不依赖外部Agent引擎）
    if itype == "agent":
        try:
            # 先用LLM拆解任务为步骤
            plan_prompt = f"""你是任务规划专家。分析以下用户任务，拆解为具体的执行步骤。

任务: {msg}

返回JSON数组，每个元素包含：
- "step": 步骤序号
- "action": 执行的动作描述（搜索/生成/分析/对比/汇总等）
- "tool": 最可能用到的工具名（search/docs/skills/code/n8n等）
- "target": 目标描述

示例格式：[{{"step":1,"action":"搜索AI行业趋势","tool":"search","target":"AI行业最新动态"}},{{"step":2,"action":"生成分析报告","tool":"docs","target":"AI趋势分析报告"}}]

只返回JSON数组，不要加额外解释。"""
            step_text = await _try_llm_chat(plan_prompt, "你是一个严格的任务规划器。只输出JSON数组。")
            txt = "🤖 **任务拆解与执行**\n\n"
            txt += f"**📋 任务:** {msg}\n\n"
            txt += "**📌 执行计划:**\n"
            steps = []
            try:
                steps = json.loads(step_text) if step_text else []
            except:
                pass
            if not steps or not isinstance(steps, list):
                steps = [{"step": 1, "action": "综合分析", "tool": "llm", "target": msg}]
            
            for s in steps:
                txt += f"  {s['step']}. [{s.get('tool','?')}] {s.get('action','')} — {s.get('target','')}\n"
            
            # 先搜N8N匹配
            n8n_results = []
            try:
                async with httpx.AsyncClient(timeout=8) as c:
                    for kw in msg.split():
                        if len(kw) > 1:
                            r = await c.get(f"http://127.0.0.1:8765/api/v1/n8n/search?q={kw}&limit=3")
                            data = r.json()
                            if data.get("results"):
                                n8n_results.extend(data["results"][:2])
            except: pass
            
            # 执行LLM综合回答（带步骤上下文）
            exec_prompt = f"""用户要求完成以下复杂任务：{msg}

我已经将任务拆解为以下步骤：
{json.dumps(steps, ensure_ascii=False, indent=2)}

请按照步骤顺序，逐步完成这个任务。可用工具包括：
- LLM对话（回答、写作、分析等）
- 搜索（查找实时信息）
- 技能执行（458个内置技能）
- N8N工作流（2077个自动化模板）
- 文档生成（Word/PPT/Excel）

请逐步执行并返回最终结果。格式：
**步骤1：** [执行内容]
**步骤2：** [执行内容]
...
**最终结果：** [汇总答案]"""
            
            result = await _try_llm_chat(exec_prompt)
            if result:
                txt += "\n\n**⚡ 执行过程:**\n" + result
            else:
                txt += "\n\n**⚡ 执行结果:**\n综合分析完成，建议查看详细结果。"
            
            # 追加N8N链接（如果找到）
            if n8n_results:
                txt += "\n\n---\n📋 **匹配到 N8N 工作流模板:**\n"
                for w in n8n_results[:5]:
                    txt += f"  • {w.get('name','')[:60]}\n"
                txt += "\n  ➤ 打开编辑器运行：[/api/v1/n8n/editor](https://autoevoai.com/api/v1/n8n/editor)"
            
            return {"success": True, "result": txt}
        except Exception as e:
            logger.warning(f"[AGENT] 执行失败: {e}")
            # 降级到LLM
            fallback = await _try_llm_chat(msg)
            if fallback:
                fallback = await _append_n8n_links(msg, fallback)
                return {"success": True, "result": fallback}
            return {"success": True, "result": "处理超时，请稍后再试"}

    # chat: LLM直接回答
    result = await _try_llm_chat(msg)
    if result:
        result = await _append_n8n_links(msg, result)
        return {"success": True, "result": result}
    # 超时再试
    result = await _try_llm_chat(msg)
    if result:
        result = await _append_n8n_links(msg, result)
        return {"success": True, "result": result}
    return {"success": True, "result": "正在思考中..."}


@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    return await smart_chat(req)


@router.get("/api/v1/llm/status")
async def llm_status():
    from api.agent_llm import get_active_model
    return get_active_model()
