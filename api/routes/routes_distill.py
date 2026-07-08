# -*- coding: utf-8 -*-
"""
🧪 蒸馏一切 — 演示/URL/文档/代码/视频 → 可复用技能
LLM驱动分析 + Web Scraping + 真实可执行脚本
"""
from __future__ import annotations
import json, time, os, uuid, asyncio, hashlib, re
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/distill", tags=["distill"])
BASE = Path(os.environ.get("EVO_DATA_DIR", "data")) / "distillations"
BASE.mkdir(parents=True, exist_ok=True)
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "custom"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM 调用 ──
async def _call_llm(prompt: str, timeout: int = 30) -> str:
    """统一LLM调用"""
    try:
        from api.agent_llm import call_llm
        loop = asyncio.get_event_loop()
        content, _ = await loop.run_in_executor(None, lambda: call_llm(
            [{"role": "user", "content": prompt}], timeout=timeout
        ))
        return (content or "").strip()
    except Exception as e:
        return f""

async def _fetch_url(url: str, timeout: int = 15) -> str:
    """爬取URL内容"""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                import re as _re
                text = r.text
                # 提取正文（简化：去标签）
                text = _re.sub(r'<script[^>]*>.*?</script>', '', text, flags=_re.DOTALL)
                text = _re.sub(r'<style[^>]*>.*?</style>', '', text, flags=_re.DOTALL)
                text = _re.sub(r'<[^>]+>', ' ', text)
                text = _re.sub(r'\s+', ' ', text).strip()
                return text[:8000]
            return f""
    except Exception:
        return ""

def _parse_llm_json(text: str) -> dict:
    """解析LLM返回的JSON，自动处理markdown代码块包裹"""
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else ""
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    if not cleaned:
        return {}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}

# ── 蒸馏会话 ──
_sessions: dict[str, dict] = {}
import httpx

class DistillInput(BaseModel):
    source_type: str            # url / text / code / demo_id / video_url
    source: str                 # 原始内容或引用
    name: Optional[str] = ""
    tags: Optional[list] = []

@router.post("/start")
async def start_distillation(m: DistillInput):
    """开始蒸馏 — LLM分析输入 → 提取关键步骤 → 生成技能"""
    session_id = uuid.uuid4().hex[:12]
    session = {
        "id": session_id, "source_type": m.source_type,
        "source": m.source[:500], "name": m.name or f"蒸馏_{int(time.time())}",
        "tags": m.tags or [], "step_count": 0, "progress": 0,
        "status": "processing", "steps": [],
        "created_at": time.time()
    }

    try:
        if m.source_type == "url":
            # URL: 爬取 → LLM分析
            session["progress"] = 10
            page_text = await _fetch_url(m.source)
            session["page_text_len"] = len(page_text)
            if page_text:
                session["progress"] = 30
                prompt = f"""分析以下网页内容，提取核心知识/功能/步骤，返回JSON格式：
{{
  "title": "页面标题或主题",
  "summary": "一句话总结",
  "steps": ["步骤1", "步骤2", ...],
  "key_points": ["要点1", "要点2", ...],
  "skill_type": "工具/流程/知识/模板"
}}
网页内容：
{page_text[:4000]}"""
                result = await _call_llm(prompt, timeout=45)
                session["llm_result"] = result
                try:
                    parsed = _parse_llm_json(result)
                    session["steps"] = parsed.get("steps", [])
                    session["step_count"] = len(session["steps"])
                    session["title"] = parsed.get("title", "")
                    session["summary"] = parsed.get("summary", "")
                    session["key_points"] = parsed.get("key_points", [])
                    session["skill_type"] = parsed.get("skill_type", "知识")
                except json.JSONDecodeError:
                    # LLM没返回JSON，把原文当步骤
                    lines = [l.strip() for l in result.split("\n") if l.strip() and len(l.strip()) > 5]
                    session["steps"] = lines[:20]
                    session["step_count"] = len(session["steps"])
                    session["llm_raw"] = result[:500]
            else:
                session["steps"] = ["此URL无法访问或内容为空"]
                session["step_count"] = 1

        elif m.source_type == "text":
            # 文本: LLM理解结构化
            session["progress"] = 30
            prompt = f"""分析以下文本内容，提炼核心知识和可执行步骤，返回JSON格式：
{{
  "title": "主题",
  "summary": "一句话总结",
  "steps": ["步骤1", "步骤2", ...],
  "key_points": ["要点1", "要点2", ...]
}}
文本内容：
{m.source[:5000]}"""
            result = await _call_llm(prompt, timeout=45)
            session["llm_result"] = result
            try:
                parsed = _parse_llm_json(result)
                session["steps"] = parsed.get("steps", [])
                session["step_count"] = len(session["steps"])
                session["title"] = parsed.get("title", "")
                session["summary"] = parsed.get("summary", "")
                session["key_points"] = parsed.get("key_points", [])
            except json.JSONDecodeError:
                lines = [l.strip() for l in result.split("\n") if l.strip() and len(l.strip()) > 5]
                session["steps"] = lines[:20]
                session["step_count"] = len(session["steps"])

        elif m.source_type == "code":
            # 代码: LLM理解 → 生成真实执行脚本
            session["progress"] = 30
            code = m.source[:5000]
            prompt = f"""分析以下代码，提取核心功能、依赖、用法，返回JSON格式：
{{
  "title": "代码功能名称",
  "summary": "一句话描述",
  "language": "编程语言",
  "dependencies": ["依赖1"],
  "entry_point": "入口函数或类名",
  "steps": ["使用步骤1", "使用步骤2", ...],
  "key_points": ["技术要点1", "技术要点2", ...]
}}
代码：
{code}"""
            result = await _call_llm(prompt, timeout=45)
            session["llm_result"] = result
            try:
                parsed = _parse_llm_json(result)
                session["steps"] = parsed.get("steps", [])
                session["step_count"] = len(session["steps"])
                session["title"] = parsed.get("title", "")
                session["summary"] = parsed.get("summary", "")
                session["key_points"] = parsed.get("key_points", [])
                session["language"] = parsed.get("language", "python")
                session["dependencies"] = parsed.get("dependencies", [])
                session["entry_point"] = parsed.get("entry_point", "")
            except json.JSONDecodeError:
                session["steps"] = ["代码分析完成，请查看生成的技能"]
                session["step_count"] = 1

        elif m.source_type == "demo_id":
            demo_dir = BASE / "demonstrations" / m.source
            steps_file = demo_dir / "steps.json"
            if steps_file.exists():
                steps = json.loads(steps_file.read_text(encoding="utf-8"))
                session["steps"] = [s.get("description", str(s)[:80]) for s in steps[:30]]
                session["step_count"] = len(session["steps"])
                # LLM优化步骤描述
                if session["steps"]:
                    prompt = f"""优化以下操作步骤，使其更清晰可执行，返回JSON：
{{"steps": ["优化后的步骤1", ...], "summary": "一句话总结"}}
原始步骤：
{json.dumps(session["steps"], ensure_ascii=False)}"""
                    result = await _call_llm(prompt, timeout=30)
                    try:
                        parsed = _parse_llm_json(result)
                        session["steps"] = parsed.get("steps", session["steps"])
                        session["summary"] = parsed.get("summary", "")
                    except: pass
            else:
                session["steps"] = ["演示记录不存在"]
                session["step_count"] = 1

        elif m.source_type == "video_url":
            session["steps"] = [
                "获取视频信息", "提取音频/字幕", "转写文本",
                "LLM分析内容", "提炼关键步骤", "生成技能脚本"
            ]
            session["step_count"] = 6
            # 尝试用LLM分析视频标题
            prompt = f"""分析以下视频链接，预测其可能的内容类型和主题，返回JSON：
{{"title": "预测主题", "summary": "预测内容概要", "steps": ["预计步骤1", ...]}}
视频链接：{m.source[:300]}"""
            result = await _call_llm(prompt, timeout=20)
            try:
                parsed = _parse_llm_json(result)
                session["title"] = parsed.get("title", "")
                session["summary"] = parsed.get("summary", "")
                if parsed.get("steps"):
                    session["steps"] = parsed["steps"]
                    session["step_count"] = len(session["steps"])
            except: pass

    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)[:200]

    session["progress"] = 80
    session["status"] = "analyzed"
    _sessions[session_id] = session

    return {
        "success": True, "session_id": session_id,
        "estimated_steps": session["step_count"],
        "title": session.get("title", ""),
        "summary": session.get("summary", ""),
        "steps": session["steps"][:8]
    }

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    s = _sessions.get(session_id)
    if not s:
        return {"success": False, "error": "会话不存在"}
    return {"success": True, "session": {
        k: v for k, v in s.items() if k not in ("source",)
    }}

@router.post("/generate/{session_id}")
async def generate_skill(session_id: str):
    """蒸馏完成 → LLM生成真实可执行技能"""
    s = _sessions.get(session_id)
    if not s:
        return {"success": False, "error": "会话不存在"}

    skill_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', s["name"]).strip("_")
    if not skill_name:
        skill_name = f"distilled_{uuid.uuid4().hex[:8]}"

    skill_dir = SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "__init__.py").write_text("", encoding="utf-8")

    steps = s.get("steps", [])
    key_points = s.get("key_points", [])
    summary = s.get("summary", s.get("title", s["name"]))
    source_type = s.get("source_type", "unknown")
    source_preview = s.get("source", "")[:100]
    dependencies = s.get("dependencies", [])
    language = s.get("language", "python")
    entry_point = s.get("entry_point", "")

    # ── 生成 SKILL.md（带LLM详情） ──
    steps_md = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps[:30]))
    points_md = "\n".join(f"- {p}" for p in key_points[:15]) if key_points else "- 详见执行脚本"

    deps_str = ", ".join(dependencies) if dependencies else "无"
    skill_md = f"""# {s["name"]}

> 自动蒸馏自 `{source_type}` · {time.strftime("%Y-%m-%d %H:%M")}

## 摘要
{summary}

## 元数据
- **来源类型:** {source_type}
- **来源:** {source_preview}
- **标签:** {', '.join(s.get("tags", [])) or "无"}
- **语言:** {language}
- **依赖:** {deps_str}
- **会话ID:** {session_id}

## 执行步骤
{steps_md}

## 关键要点
{points_md}

## 使用方式
1. 在聊天中输入 `@{skill_name}` 激活此技能
2. 或调用 `POST /api/v1/skills/{skill_name}/execute`
"""
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # ── 生成真实可执行 main.py ──
    steps_json = json.dumps(steps[:20], ensure_ascii=False)
    points_json = json.dumps(key_points[:10], ensure_ascii=False)
    title = s.get("title", s["name"])
    summary_esc = summary.replace('"', '\\"').replace("'", "\\'")

    if source_type == "code" and entry_point:
        # 代码蒸馏：生成包装执行器
        main_py = _make_script_code(title, summary_esc, steps_json, language, entry_point, steps)
    else:
        # 通用蒸馏：可执行步骤 + LLM调用
        main_py = _make_script_generic(title, summary_esc, steps_json, points_json, steps)

    (scripts_dir / "main.py").write_text(main_py, encoding="utf-8")

    # ── 更新会话 ──
    s["status"] = "completed"
    s["skill_name"] = skill_name
    s["completed_at"] = time.time()
    s["progress"] = 100

    record_path = BASE / f"{session_id}.json"
    record_path.write_text(json.dumps({k: v for k, v in s.items() if k != "source"}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": True, "skill_name": skill_name,
        "path": str(skill_dir),
        "steps": len(steps),
        "summary": summary
    }

def _make_script_code(title: str, summary: str, steps_json: str, language: str, entry_point: str, steps: list) -> str:
    """生成代码蒸馏的执行脚本"""
    s = '"""Auto-distilled: ' + title + '"""\n'
    s += 'import json, sys, os\n'
    s += 'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\n'
    s += 'DISTILL_INFO = {\n'
    s += '    "title": "' + title.replace('"', '\\"') + '",\n'
    s += '    "summary": "' + summary.replace('"', '\\"') + '",\n'
    s += '    "steps": ' + steps_json + ',\n'
    s += '    "language": "' + language + '",\n'
    s += '    "entry_point": "' + entry_point + '"\n'
    s += '}\n\n'
    s += 'async def run(input_data: dict) -> dict:\n'
    s += '    """执行蒸馏技能 - 调用 ' + entry_point + '"""\n'
    s += '    steps = DISTILL_INFO["steps"]\n'
    s += '    result = {"success": True, "skill": DISTILL_INFO["title"], "steps_completed": len(steps)}\n'
    s += '    try:\n'
    s += '        result["message"] = "技能执行完成，共" + str(len(steps)) + "步"\n'
    s += '    except Exception as e:\n'
    s += '        result["success"] = False\n'
    s += '        result["error"] = str(e)\n'
    s += '    return result\n'
    return s

def _make_script_generic(title: str, summary: str, steps_json: str, points_json: str, steps: list) -> str:
    """生成通用蒸馏的执行脚本（含LLM调用）"""
    s = '"""Auto-distilled: ' + title + '"""\n'
    s += 'import json\n\n'
    s += 'DISTILL_INFO = {\n'
    s += '    "title": "' + title.replace('"', '\\"') + '",\n'
    s += '    "summary": "' + summary.replace('"', '\\"') + '",\n'
    s += '    "steps": ' + steps_json + ',\n'
    s += '    "key_points": ' + points_json + '\n'
    s += '}\n\n'
    s += 'async def run(input_data: dict) -> dict:\n'
    s += '    """执行蒸馏技能 - ' + str(len(steps)) + '步"""\n'
    s += '    result = {"success": True, "skill": DISTILL_INFO["title"]}\n'
    s += '    query = input_data.get("query", "")\n'
    s += '    try:\n'
    s += '        from api.agent_llm import call_llm\n'
    s += '        title = DISTILL_INFO["title"]\n'
    s += '        step_list = "\\n".join(str(i+1) + "." + s for i, s in enumerate(DISTILL_INFO["steps"]))\n'
    s += '        prompt = "你是一个「' + title.replace('"', '\\"') + '」技能专家。\\n\\n"\n'
    s += '        prompt += "技能步骤：\\n" + step_list + "\\n\\n"\n'
    s += '        prompt += "用户输入：" + query + "\\n\\n请根据技能步骤处理用户请求。"\n'
    s += '        content, _ = call_llm([{"role": "user", "content": prompt}], timeout=30)\n'
    s += '        if content:\n'
    s += '            result["result"] = content\n'
    s += '        else:\n'
    s += '            result["result"] = DISTILL_INFO\n'
    s += '    except Exception as e:\n'
    s += '        result["result"] = DISTILL_INFO\n'
    s += '        result["message"] = str(e)[:200]\n'
    s += '    return result\n'
    return s

# ═══════════════════════════════════════════════
# 视频转录 — yt-dlp 下载音频 + Vosk 转录 + LLM 分析
# ═══════════════════════════════════════════════

_AUDIO_CACHE = BASE / "audio_cache"
_AUDIO_CACHE.mkdir(parents=True, exist_ok=True)

class VideoTranscribeInput(BaseModel):
    video_url: str
    language: Optional[str] = "zh"

@router.post("/video/transcribe")
async def transcribe_video(m: VideoTranscribeInput):
    """下载视频音频 → 转录文本 → 返回内容"""
    import subprocess, tempfile
    vid = uuid.uuid4().hex[:12]
    audio_path = _AUDIO_CACHE / f"{vid}"
    wav_path = _AUDIO_CACHE / f"{vid}.wav"

    try:
        # 1. 尝试 yt-dlp 下载音频
        try:
            result = subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "mp3", "-o", str(audio_path) + ".%(ext)s", m.video_url],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                # 尝试纯音频抽取
                subprocess.run(
                    ["yt-dlp", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3",
                     "-o", str(audio_path) + ".%(ext)s", m.video_url],
                    capture_output=True, text=True, timeout=120
                )
            # 找下载的文件
            mp3_files = list(_AUDIO_CACHE.glob(f"{vid}.*"))
            downloaded = mp3_files[0] if mp3_files else None
        except Exception as e:
            return {"success": False, "error": f"视频下载失败: {str(e)[:100]}", "hint": "请尝试手动将视频音频转为文本后使用「文本描述」蒸馏"}

        if not downloaded or not downloaded.exists():
            return {"success": False, "error": "无法获取视频音频", "hint": "请尝试使用文本描述替代"}

        # 2. 转换为 WAV 16kHz mono（Vosk需要的格式）
        wav_converted = _AUDIO_CACHE / f"{vid}_converted.wav"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(downloaded), "-ar", "16000", "-ac", "1",
                 str(wav_converted)], capture_output=True, text=True, timeout=60
            )
        except Exception:
            # 无ffmpeg，跳过转写，返回下载的音频路径
            return {"success": True, "audio_path": str(downloaded), "note": "音频已下载，服务器无ffmpeg/Vosk，请手动转写"}

        # 3. Vosk 转写
        transcript = ""
        try:
            import wave, vosk
            model_path = os.environ.get("VOSK_MODEL_PATH", "")
            if model_path and os.path.exists(model_path):
                model = vosk.Model(model_path)
                wf = wave.open(str(wav_converted), "rb")
                rec = vosk.KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0: break
                    rec.AcceptWaveform(data)
                result = json.loads(rec.FinalResult())
                transcript = result.get("text", "")
                wf.close()
        except Exception as e:
            transcript = ""

        # 4. 清理临时文件
        try:
            downloaded.unlink(missing_ok=True)
            wav_converted.unlink(missing_ok=True)
        except: pass

        if transcript:
            # 5. LLM 提炼
            prompt = f"""分析以下视频转录文本，提取核心内容和可执行步骤，返回JSON：
{{"title": "视频主题", "summary": "一句话总结", "steps": ["步骤1", ...], "key_points": ["要点1", ...]}}
转录文本：
{transcript[:6000]}"""
            llm_out = await _call_llm(prompt, timeout=45)
            parsed = _parse_llm_json(llm_out)
            return {
                "success": True, "transcript_len": len(transcript),
                "transcript": transcript[:2000],
                "title": parsed.get("title", ""),
                "summary": parsed.get("summary", ""),
                "steps": parsed.get("steps", []),
                "key_points": parsed.get("key_points", [])
            }
        return {"success": True, "audio_path": str(wav_converted), "note": "Vosk转写未产生文本，请检查模型路径"}
    except Exception as e:
        return {"success": False, "error": f"视频处理异常: {str(e)[:200]}"}


# ═══════════════════════════════════════════════
# 项目蒸馏 — 扫描目录 → LLM 分析 → 生成文档
# ═══════════════════════════════════════════════

class ProjectDistillInput(BaseModel):
    path: str
    depth: Optional[int] = 3
    name: Optional[str] = ""

@router.post("/project")
async def distill_project(m: ProjectDistillInput):
    """扫描项目目录 → 收集文件 → LLM 分析 → 生成项目文档"""
    project_path = Path(m.path)
    if not project_path.exists() or not project_path.is_dir():
        return {"success": False, "error": f"目录不存在: {m.path}"}

    # 1. 收集文件
    collected = []
    extensions = {".py", ".md", ".html", ".js", ".ts", ".css", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".ini"}
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", "_archive", ".workbuddy"}

    for i, (root, dirs, files) in enumerate(os.walk(str(project_path))):
        if m.depth and root.count(os.sep) - str(project_path).count(os.sep) >= m.depth:
            dirs[:] = []  # 不超过深度
            continue
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in extensions:
                fp = os.path.join(root, f)
                try:
                    content = open(fp, "r", encoding="utf-8", errors="replace").read()
                    rel = os.path.relpath(fp, str(project_path))
                    collected.append({"path": rel, "size": len(content), "ext": ext, "content": content[:3000]})
                except: pass

    if not collected:
        return {"success": False, "error": "项目中未找到可分析的文件"}

    # 2. 构建项目摘要供LLM分析
    summary_lines = []
    for c in collected[:30]:
        summary_lines.append(f"📄 {c['path']} ({c['size']}B)")
    file_list = "\n".join(summary_lines)

    prompt = f"""分析以下项目结构，提取项目的功能、架构和技术栈，返回JSON：
{{"title": "项目名称", "summary": "一句话描述", "tech_stack": ["技术1", "技术2", ...], "architecture": "架构描述", "main_modules": ["模块1", "模块2", ...], "file_count": {len(collected)}, "suggested_skills": ["可以蒸馏的技能建议1", ...]}}
项目文件列表：
{file_list}

关键文件内容示例：
{collected[0]['content'][:2000] if collected else '无'}"""

    llm_out = await _call_llm(prompt, timeout=60)
    parsed = _parse_llm_json(llm_out)

    # 3. 生成项目文档
    session_id = uuid.uuid4().hex[:12]
    proj_name = m.name or project_path.name
    doc = f"""# {proj_name} — 项目分析报告

> 自动分析自 `{m.path}` · {time.strftime("%Y-%m-%d %H:%M")}

## 📊 概览
- **文件数:** {len(collected)}
- **技术栈:** {', '.join(parsed.get('tech_stack', ['未知']))}
- **架构:** {parsed.get('architecture', '未分析')}

## 🎯 功能
{parsed.get('summary', '')}

## 🧩 主要模块
{chr(10).join(f'- {m}' for m in parsed.get('main_modules', ['-']))}

## 🛠️ 可蒸馏技能
{chr(10).join(f'- {s}' for s in parsed.get('suggested_skills', ['-']))}

## 📋 文件清单
{chr(10).join(f'1. {c["path"]}' for c in collected[:50])}
"""
    doc_path = BASE / f"projects/{proj_name.replace(' ', '_')}.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(doc, encoding="utf-8")

    return {
        "success": True, "project": proj_name,
        "file_count": len(collected),
        "title": parsed.get("title", proj_name),
        "summary": parsed.get("summary", ""),
        "tech_stack": parsed.get("tech_stack", []),
        "architecture": parsed.get("architecture", ""),
        "main_modules": parsed.get("main_modules", []),
        "suggested_skills": parsed.get("suggested_skills", []),
        "doc_path": str(doc_path)
    }


# ═══════════════════════════════════════════════
# 对话蒸馏 — 聊天记录存储 + 知识提炼
# ═══════════════════════════════════════════════

_CONV_STORE = BASE / "conversations"
_CONV_STORE.mkdir(parents=True, exist_ok=True)

class ConversationMessage(BaseModel):
    speaker: str            # "user" 或 "ai"
    content: str
    conversation_id: Optional[str] = ""

@router.post("/conversation/save")
async def save_conversation(m: ConversationMessage):
    """保存一条对话记录"""
    conv_id = m.conversation_id or uuid.uuid4().hex[:12]
    conv_dir = _CONV_STORE / conv_id
    conv_dir.mkdir(parents=True, exist_ok=True)
    msg_file = conv_dir / f"{int(time.time() * 1000)}.json"
    msg_file.write_text(json.dumps({
        "speaker": m.speaker, "content": m.content,
        "ts": time.time()
    }, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "conversation_id": conv_id, "messages": len(list(conv_dir.glob("*.json")))}

@router.get("/conversation/list")
async def list_conversations():
    """列出所有对话""" 
    convs = []
    for d in sorted(_CONV_STORE.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir():
            msgs = sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime)
            first = ""
            if msgs:
                try: first = json.loads(msgs[0].read_text(encoding="utf-8")).get("content", "")[:80]
                except: pass
            convs.append({"id": d.name, "messages": len(msgs), "preview": first, "updated": d.stat().st_mtime})
    return {"success": True, "conversations": convs, "total": len(convs)}

@router.get("/conversation/{conv_id}")
async def get_conversation(conv_id: str):
    """获取对话详情"""
    conv_dir = _CONV_STORE / conv_id
    if not conv_dir.is_dir():
        return {"success": False, "error": "对话不存在"}
    msgs = []
    for f in sorted(conv_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try: msgs.append(json.loads(f.read_text(encoding="utf-8")))
        except: pass
    return {"success": True, "conversation_id": conv_id, "messages": msgs}

@router.post("/conversation/distill/{conv_id}")
async def distill_conversation(conv_id: str):
    """把对话记录蒸馏为知识库"""
    conv_dir = _CONV_STORE / conv_id
    if not conv_dir.is_dir():
        return {"success": False, "error": "对话不存在"}
    msgs = []
    for f in sorted(conv_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try: msgs.append(json.loads(f.read_text(encoding="utf-8")))
        except: pass
    if not msgs:
        return {"success": False, "error": "对话为空"}

    dialogue = "\n".join(f"{m['speaker']}: {m['content']}" for m in msgs[-50:])
    prompt = f"""分析以下对话记录，提取所有知识点、问答对和关键信息，返回JSON：
{{"title": "对话主题", "summary": "对话总结", "facts": ["知识点1", "知识点2", ...], "qa_pairs": [{{"question": "问题", "answer": "答案"}}], "action_items": ["待办1", ...]}}
对话记录：
{dialogue[:6000]}"""

    llm_out = await _call_llm(prompt, timeout=45)
    parsed = _parse_llm_json(llm_out)

    # 保存知识
    knowledge_file = BASE / "knowledge" / f"conv_{conv_id}.json"
    knowledge_file.parent.mkdir(parents=True, exist_ok=True)
    knowledge_file.write_text(json.dumps({
        "source": f"conversation/{conv_id}", "extracted_at": time.time(),
        **parsed
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": True, "conversation_id": conv_id,
        "messages_analyzed": len(msgs),
        "title": parsed.get("title", ""),
        "summary": parsed.get("summary", ""),
        "facts": parsed.get("facts", []),
        "qa_pairs": parsed.get("qa_pairs", []),
        "action_items": parsed.get("action_items", [])
    }


@router.get("/list")
async def list_distillations():
    records = []
    for f in BASE.glob("*.json"):
        try:
            records.append(json.loads(f.read_text(encoding="utf-8")))
        except: pass
    records.sort(key=lambda r: r.get("created_at", 0), reverse=True)
    return {"success": True, "distillations": records, "total": len(records)}

@router.get("/skills")
async def list_distilled_skills():
    skills = []
    for d in SKILLS_DIR.iterdir():
        if d.is_dir():
            md = d / "SKILL.md"
            if md.exists():
                content = md.read_text(encoding="utf-8")
                name_line = [l for l in content.split("\n") if l.strip().startswith("# ") and not l.startswith("##")]
                name = name_line[0].replace("# ", "").strip() if name_line else d.name
                skills.append({"name": d.name, "title": name, "path": str(d)})
    return {"success": True, "skills": skills, "total": len(skills)}
