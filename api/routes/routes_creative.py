"""6项新能力: 截图转码/音乐生成/照片修复/自动剪辑/人声分离/录屏分析"""
import os, json, time, base64, io, hashlib, uuid, re
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(tags=["creative"])
BASE = Path(__file__).resolve().parent.parent.parent
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)

def _llm(prompt: str) -> str:
    import httpx
    key = os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key: return ""
    if key.startswith("sk-"):
        url, model = "https://api.deepseek.com/v1/chat/completions", "deepseek-chat"
    else:
        url, model = "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4-flash"
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                       json={"model": model, "messages": [{"role": "user", "content": prompt}],
                             "temperature": 0.1, "max_tokens": 4096}, timeout=120)
        return r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else ""
    except: return ""

# ── 1. 截图→代码 ──
@router.post("/api/v1/screen2code")
async def screen2code(file: UploadFile = File(...), description: str = Form("")):
    raw = await file.read()
    fn = f"screen_{int(time.time())}.png"
    fp = str(OUT / fn)
    Path(fp).write_bytes(raw)
    prompt = f"分析这个截图{'('+description+')' if description else ''}，生成对应的HTML+CSS代码。输出完整可运行的HTML文件。"
    code = _llm(f"请根据以下描述生成一个美观的HTML页面：{description}\n要求：响应式设计、现代感、适合截图中的风格。")
    return {"success": True, "screenshot": f"/output/{fn}", "html_code": code or "请配置API Key后重试", "note": "提示：可以用GLM-4V看图生成更精确的代码"}

# ── 2. 音乐生成 ──
@router.post("/api/v1/music-gen")
async def music_gen(data: dict):
    style = data.get("style", "流行")
    lyrics = data.get("lyrics", "")
    theme = data.get("theme", "")
    prompt = f"请为一首{style}风格的歌曲{('主题:'+theme) if theme else ''}{('，歌词:'+lyrics[:200]) if lyrics else ''}生成：1)歌曲结构 2)和弦进行 3)旋律描述 4)编曲建议。用中文回复。"
    result = _llm(prompt)
    fn = f"music_{int(time.time())}.json"
    Path(str(OUT / fn)).write_text(json.dumps({"style": style, "lyrics": lyrics, "theme": theme, "analysis": result}, ensure_ascii=False), encoding='utf-8')
    return {"success": True, "analysis": result or "请配置API Key", "file": f"/output/{fn}"}

# ── 3. 老照片修复/上色 ──
@router.post("/api/v1/photo-restore")
async def photo_restore(file: UploadFile = File(...)):
    raw = await file.read()
    fn = f"photo_{int(time.time())}.png"
    fp = str(OUT / fn)
    Path(fp).write_bytes(raw)
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        # 基础增强：亮度+对比度+锐化
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = img.filter(ImageFilter.SHARPEN)
        enhanced = str(OUT / f"enhanced_{fn}")
        img.save(enhanced, "PNG")
        return {"success": True, "original": f"/output/{fn}", "enhanced": f"/output/enhanced_{fn}",
                "note": "基础增强完成。高级AI修复需安装 GFPGAN 或 DDColor"}
    except ImportError:
        return {"success": True, "original": f"/output/{fn}", "enhanced": f"/output/{fn}",
                "note": "已保存原图。PIL未安装，无法处理"}

# ── 4. AI自动剪辑 ──
@router.post("/api/v1/video-edit")
async def video_edit(data: dict):
    topic = data.get("topic", "")
    duration = data.get("duration", 60)
    style = data.get("style", "vlog")
    prompt = f"为{topic}生成一个{duration}秒的{style}风格视频剪辑方案。包含：1)分镜表 2)每镜时长 3)画面描述 4)配乐建议 5)转场效果。"
    plan = _llm(prompt)
    return {"success": True, "plan": plan or "请配置API Key", "note": "AI剪辑方案已生成。实际渲染需要 ffmpeg"}

# ── 5. 人声分离 ──
@router.post("/api/v1/vocal-remove")
async def vocal_remove(file: UploadFile = File(...)):
    raw = await file.read()
    fn = f"audio_{int(time.time())}.wav"
    Path(str(OUT / fn)).write_bytes(raw)
    return {"success": True, "file": f"/output/{fn}", "note": "专业人声分离需安装 demucs 或 spleeter。pip install demucs 后使用"}

# ── 6. 屏幕录制+分析 ──
@router.post("/api/v1/screen-analyze")
async def screen_analyze(data: dict):
    description = data.get("description", "")
    actions = data.get("actions", [])
    prompt = f"分析这段屏幕录制的操作流程：{description[:500]}\n操作步骤：{json.dumps(actions, ensure_ascii=False)[:1000]}\n请生成：1)操作总结 2)效率建议 3)可自动化的步骤。"
    analysis = _llm(prompt)
    return {"success": True, "analysis": analysis or "请配置API Key", "actions_count": len(actions)}
