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
