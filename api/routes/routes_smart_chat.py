"""智能体路由 — 纯LLM意图理解，无任何硬编码路由"""
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
OUT = BASE / "output"; OUT.mkdir(exist_ok=True)
TOOLS_DIR = OUT / "tools"; TOOLS_DIR.mkdir(exist_ok=True)
MEM_DB = BASE / "data" / "agent_memory.db"; MEM_DB.parent.mkdir(parents=True, exist_ok=True)

# ── LLM意图路由（唯一路由逻辑）──
_INTENT_PROMPT = """你是一个意图分析专家。分析用户消息，判断最合适的处理方式。
可选处理方式:
1. hot: 用户想查某个平台的热点/热搜/榜单
2. search: 用户想搜索信息
3. create: 用户想生成文档/PPT/Excel/代码
4. help: 用户问系统能力
5. chat: 其他对话

只返回JSON: {"intent":"xxx","source":"平台名(仅hot时需要)","topic":"主题"}"""

_REMEMBER_URLS = {}  # 记住最近生成的文件

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []

async def _llm_analyze(msg: str) -> dict:
    """LLM分析意图"""
    from api.agent_llm import call_llm
    text, _ = call_llm([{"role":"user","content":_INTENT_PROMPT + "\n\n用户消息:" + msg}], timeout=8)
    if text:
        try:
            text = text.strip()
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            elif "```" in text: text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except: pass
    return {"intent":"chat"}

async def _execute_source(source: str, topic: str) -> str | None:
    """执行数据源获取 - 所有数据源统一入口"""
    source_lower = source.lower().replace(" ","").replace("_","")
    try:
        import urllib.request, re
        # 百度热搜
        if "baidu" in source_lower or "百度" in source_lower or not source_lower:
            req = urllib.request.Request("https://top.baidu.com/board?tab=realtime",
                headers={"User-Agent":"Mozilla/5.0","Cookie":"PSTM=0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8","replace")
            items = re.findall(r'"word":"([^"]+)"', html) or re.findall(r'"title":"([^"]+)"', html)[:30]
            if items:
                txt = "🔥 **百度热搜**\n\n"
                seen=set(); c=0
                for t in items:
                    t=t.strip()
                    if t and len(t)>2 and t not in seen: seen.add(t); c+=1; txt+=f"**{c}.** {t}\n"
                    if c>=30: break
                return txt
        # 其他数据源
        for name, cfg in [("weibo","https://api.vvhan.com/api/hotlist?type=weiboHot"),
                           ("zhihu","https://api.vvhan.com/api/hotlist?type=zhihuHot"),
                           ("douyin","https://api.vvhan.com/api/hotlist?type=douyinHot"),
                           ("bilibili","https://api.vvhan.com/api/hotlist?type=biliHot"),
                           ("tieba","https://api.vvhan.com/api/hotlist?type=tiebaHot"),
                           ("toutiao","https://api.vvhan.com/api/hotlist?type=toutiaoHot"),
                           ("tencent","https://api.vvhan.com/api/hotlist?type=qqHot")]:
            if name in source_lower:
                req2 = urllib.request.Request(cfg, headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    d = json.loads(resp2.read().decode("utf-8","replace"))
                if d.get("success") and d.get("data"):
                    titles = [x.get("title","") for x in d["data"] if x.get("title")]
                    names = {"weibo":"微博","zhihu":"知乎","douyin":"抖音","bilibili":"B站","tieba":"贴吧","toutiao":"头条","tencent":"腾讯"}
                    n = names.get(name, name)
                    txt = f"🔥 **{n}热搜**\n\n"
                    for i, t in enumerate(titles[:30]): txt += f"**{i+1}.** {t}\n"
                    return txt
    except Exception:
        pass
    # 所有源都失败时提示
    return None

async def _smart_route(msg: str, do_search=True) -> dict:
    """LLM意图路由 - 唯一的路由入口"""
    intent = await _llm_analyze(msg)
    itype = intent.get("intent","chat")
    source = intent.get("source","")
    topic = intent.get("topic","")

    # hot → 查热点
    if itype == "hot":
        result = await _execute_source(source, topic)
        if result:
            return {"success": True, "result": result}
        # 降级: 全部源不可用时提示
        return {"success": True, "result": f"⚠️ {source or '指定平台'}热点暂时不可用，稍后再试"}

    # search → 搜索
    if itype == "search" and do_search:
        try:
            from skills.builtin.search_web import execute as _sw
            r = _sw({"query": topic or msg, "count": 8})
            items = r.get("results", [])
            if items:
                txt = f"🔍 **{topic or msg}**\n\n"
                for i, item in enumerate(items[:8]):
                    t = item.get("title","")[:60]
                    u = item.get("url","")
                    txt += f"**{i+1}.** [{t}]({u})\n" if u else f"**{i+1}.** {t}\n"
                return {"success": True, "result": txt}
        except Exception:
            pass

    # create → 生成
    if itype == "create":
        return {"success": True, "result": f"收到生成请求：{topic or msg}。请补充具体描述。"}

    # help → 能力列表
    if itype == "help":
        return {"success": True, "result": "🤖 **AUTO-EVO-AI 能力**\n直接说需求，我会理解并执行。"}

    # chat → LLM
    return None

@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    if not msg:
        return {"success": True, "result": "请说点什么"}

    # 唯一路由：LLM理解意图
    result = await _smart_route(msg)
    if result:
        return result

    # LLM兜底
    from api.agent_llm import call_llm, _get_key
    key = _get_key()
    text, _ = call_llm([{"role":"user","content":msg}], key=key)
    if text:
        return {"success": True, "result": text}
    return {"success": True, "result": "处理完成"}

@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    """流式输出"""
    msg = req.message or ""
    result = await _smart_route(msg, do_search=False)

    async def gen():
        yield json.dumps({"type":"start"}, ensure_ascii=False) + "\n"
        if result:
            text = result.get("result","")
            for i in range(0, len(text), 20):
                yield json.dumps({"type":"chunk","text":text[i:i+20]}, ensure_ascii=False) + "\n"
            yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
            return
        from api.agent_llm import call_llm_stream
        for chunk in call_llm_stream([{"role":"user","content":msg}]):
            if chunk == "__DONE__":
                yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
                return
            yield json.dumps({"type":"chunk","text":chunk}, ensure_ascii=False) + "\n"
        yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
    return StreamingResponse(gen(), media_type="application/x-ndjson")

@router.get("/api/v1/llm/status")
async def llm_status():
    from api.agent_llm import get_active_model
    return get_active_model()

def register_routes(app):
    app.include_router(router)
setup_smart_chat_routes = register_routes
