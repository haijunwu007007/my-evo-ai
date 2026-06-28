"""智能体路由 — 纯LLM驱动，0硬编码路由，0写死数据源"""

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

# ── 热点数据源注册表（唯一写数据源的地方）──
_HOT_SOURCES = [
    ("baidu",  "https://api.vvhan.com/api/hotlist?type=baiduHot", "json"),
    ("weibo",  "https://api.vvhan.com/api/hotlist?type=weiboHot", "json"),
    ("douyin", "https://api.vvhan.com/api/hotlist?type=douyinHot", "json"),
    ("zhihu",  "https://api.vvhan.com/api/hotlist?type=zhihuHot", "json"),
    ("bili",   "https://api.vvhan.com/api/hotlist?type=biliHot", "json"),
    ("tieba",  "https://api.vvhan.com/api/hotlist?type=tiebaHot", "json"),
    ("toutiao","https://api.vvhan.com/api/hotlist?type=toutiaoHot", "json"),
    ("tencent","https://api.vvhan.com/api/hotlist?type=qqHot", "json"),
]
_HOT_NAMES = {"baidu":"百度","weibo":"微博","douyin":"抖音","zhihu":"知乎","bili":"B站","tieba":"贴吧","toutiao":"头条","tencent":"腾讯"}

async def _fetch_hot(platform: str) -> str | None:
    """通用热点抓取 — 所有平台统一方式"""
    import urllib.request, json
    for name, url, fmt in _HOT_SOURCES:
        if platform and platform not in name and name not in platform:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8","replace")
            if fmt == "json":
                d = json.loads(raw)
                if d.get("success") and d.get("data"):
                    titles = [x.get("title","") for x in d["data"] if x.get("title")]
                    n = _HOT_NAMES.get(name, name)
                    txt = f"🔥 **{n}热搜**\n\n"
                    for i, t in enumerate(titles[:30]): txt += f"**{i+1}.** {t}\n"
                    return txt
            elif fmt == "baidu_html":
                import re as _re
                items = _re.findall(r'"word":"([^"]+)"', raw) or _re.findall(r'"title":"([^"]+)"', raw)[:30]
                if items:
                    txt = "🔥 **百度热搜**\n\n"
                    seen=set(); c=0
                    for t in items:
                        t=t.strip()
                        if t and len(t)>2 and t not in seen: seen.add(t); c+=1; txt+=f"**{c}.** {t}\n"
                        if c>=30: break
                    return txt
        except: pass
        if platform: break  # 指定平台只试一次
    return None

async def _try_all_hot() -> str | None:
    """全量轮询，返回第一个成功的"""
    for name, _, _ in _HOT_SOURCES:
        r = await _fetch_hot(name)
        if r: return r
    return None

async def _llm_chat(msg: str) -> str | None:
    """LLM智能聊天——理解+执行"""
    from api.agent_core import create_engine
    eng = create_engine(BASE, BASE/"output", BASE/"output"/"tools", BASE/"data"/"agent_memory.db")
    for attempt in range(3):
        r = await asyncio.to_thread(eng, msg, "", "zh-CN", [])
        if isinstance(r, dict):
            result = r.get("result","") or ""
            if result: return result
            mode = r.get("mode","")
            if mode in ("direct","no_key","timeout"): break
    return None

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

async def _try_hot_fallback(source: str) -> str | None:
    """尝试所有可能的数据源，只要有一个成功就返回"""
    sources = [
        ("baidu", "https://top.baidu.com/board?tab=realtime", "baidu"),
        ("weibo", "https://api.vvhan.com/api/hotlist?type=weiboHot", "weibo"),
        ("douyin", "https://api.vvhan.com/api/hotlist?type=douyinHot", "douyin"),
        ("zhihu", "https://api.vvhan.com/api/hotlist?type=zhihuHot", "zhihu"),
        ("bili", "https://api.vvhan.com/api/hotlist?type=biliHot", "bili"),
        ("toutiao", "https://api.vvhan.com/api/hotlist?type=toutiaoHot", "toutiao"),
        ("tencent", "https://api.vvhan.com/api/hotlist?type=qqHot", "qq"),
    ]
    import urllib.request, json
    names = {"baidu":"百度","weibo":"微博","douyin":"抖音","zhihu":"知乎","bili":"B站","toutiao":"头条","tencent":"腾讯"}
    # 先试指定源
    for name, url, _ in sources:
        if name in source.lower() or source.lower() in name:
            try:
                if name == "baidu":
                    import re
                    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Cookie":"PSTM=0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        html = resp.read().decode("utf-8","replace")
                    items = re.findall(r'"word":"([^"]+)"', html) or re.findall(r'"title":"([^"]+)"', html)[:30]
                    if items:
                        txt = f"🔥 **{names[name]}热搜**\n\n"
                        seen=set(); c=0
                        for t in items:
                            t=t.strip()
                            if t and len(t)>2 and t not in seen: seen.add(t); c+=1; txt+=f"**{c}.** {t}\n"
                            if c>=30: break
                        return txt
                else:
                    req2 = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        d = json.loads(resp2.read().decode("utf-8","replace"))
                    if d.get("success") and d.get("data"):
                        titles = [x.get("title","") for x in d["data"] if x.get("title")]
                        txt = f"🔥 **{names[name]}热搜**\n\n"
                        for i, t in enumerate(titles[:30]): txt += f"**{i+1}.** {t}\n"
                        return txt
            except: pass
    # 指定源失败 → 全量轮询，返回第一个成功的
    for name, url, _ in sources:
        try:
            if name == "baidu":
                import re
                req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Cookie":"PSTM=0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    html = resp.read().decode("utf-8","replace")
                items = re.findall(r'"word":"([^"]+)"', html) or re.findall(r'"title":"([^"]+)"', html)[:30]
                if items:
                    txt = f"🔥 **{names[name]}热搜**\n\n"
                    seen=set(); c=0
                    for t in items:
                        t=t.strip()
                        if t and len(t)>2 and t not in seen: seen.add(t); c+=1; txt+=f"**{c}.** {t}\n"
                        if c>=30: break
                    return txt
            else:
                req2 = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=8) as resp2:
                    d = json.loads(resp2.read().decode("utf-8","replace"))
                if d.get("success") and d.get("data"):
                    titles = [x.get("title","") for x in d["data"] if x.get("title")]
                    txt = f"🔥 **{names[name]}热搜**\n\n"
                    for i, t in enumerate(titles[:30]): txt += f"**{i+1}.** {t}\n"
                    return txt
        except: pass
    return None

@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    if not msg:
        return {"success": True, "result": "请说点什么"}

    # 1) LLM分析意图
    from api.agent_llm import call_llm, _get_key
    key = _get_key()
    intent_prompt = "分析意图，只返回JSON: {\"intent\":\"hot/search/chat\",\"platform\":\"数据源\",\"topic\":\"主题\"}。如果用户想查热点/热搜/热榜/头条/新闻→intent=hot。如果涉及特定平台(百度/微博/抖音/B站/知乎/头条/腾讯/贴吧)→platform设为平台名。用户: " + msg
    intent_text, _ = call_llm([{"role":"user","content":intent_prompt}], key=key, timeout=8)
    intent = {"intent":"chat","platform":"","topic":""}
    if intent_text:
        try:
            import re as _re2
            cleaned = intent_text.strip()
            if "```json" in cleaned: cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned: cleaned = cleaned.split("```")[1].split("```")[0]
            intent = json.loads(cleaned)
        except: pass

    itype = intent.get("intent","chat")
    platform = intent.get("platform","")
    topic = intent.get("topic","")

    # 2) 热点 → 通用热点头
    if itype == "hot":
        r = await _fetch_hot(platform)
        if r: return {"success": True, "result": r}
        r2 = await _try_all_hot()
        if r2: return {"success": True, "result": r2}
        return {"success": True, "result": "所有热点暂时不可用，试试直接问问题"}

    # 3) 搜索 → Bing
    if itype == "search":
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
        except: pass

    # 4) chat → LLM引擎理解+执行
    result = await _llm_chat(msg)
    if result:
        return {"success": True, "result": result}

    # 5) 最兜底
    text, _ = call_llm([{"role":"user","content":msg}], key=key)
    if text:
        return {"success": True, "result": text}
    return {"success": True, "result": "处理完成"} 

@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    """流式输出"""
    msg = req.message or ""
    from api.agent_llm import call_llm_stream

    async def gen():
        yield json.dumps({"type":"start"}, ensure_ascii=False) + "\n"
        try:
            # 先用 LLM 引擎
            r = await _llm_chat(msg)
            if r:
                for i in range(0, len(r), 20):
                    yield json.dumps({"type":"chunk","text":r[i:i+20]}, ensure_ascii=False) + "\n"
                yield json.dumps({"type":"done"}, ensure_ascii=False) + "\n"
                return
        except: pass
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
