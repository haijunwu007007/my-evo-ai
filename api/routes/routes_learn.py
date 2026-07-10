"""
AUTO-EVO-AI 学习系统 v2 — Record → Generate → Replay
=====================================================
架构参考：OpenAI Codex Record & Replay (2026-06-18),
         Hermes Agent 技能系统, Browser-Use Agent 循环

核心流程:
  1. Record  — 演示操作 → Playwright 自动录制每一步
  2. Generate— LLM 分析步骤 → 生成 SKILL.md (可编辑)
  3. Replay  — 执行 SKILL.md → Playwright 自动回放

存储结构:
  skills/custom/<skill_name>/
    ├── SKILL.md        (核心指令与元数据)
    ├── scripts/         (可选: Python 执行脚本)
    └── references/      (可选: 参考文件)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, hashlib, sqlite3, threading, os, logging, asyncio, uuid
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/learn", tags=["learn"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LEARN_DB = BASE_DIR / "data" / "learn_engine.db"
_LEARN_DB.parent.mkdir(exist_ok=True)
_local = threading.local()
SKILLS_CUSTOM_DIR = BASE_DIR / "skills" / "custom"

# ─── 活跃录制/回放会话 ───
_active_recordings: dict[str, dict] = {}  # browser_session_id -> recording state
_active_replays: dict[str, dict] = {}     # replay_session_id -> replay state


def _db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(_LEARN_DB))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.executescript("""
            CREATE TABLE IF NOT EXISTS demonstrations (
                id TEXT PRIMARY KEY, name TEXT, description TEXT,
                steps TEXT DEFAULT '[]', skill_code TEXT,
                created_at REAL, updated_at REAL, use_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS recordings (
                id TEXT PRIMARY KEY, demo_id TEXT,
                action TEXT, selector TEXT, value TEXT, url TEXT,
                screenshot TEXT, timestamp REAL, order_num INTEGER
            );
        """)
        _local.conn.commit()
    return _local.conn


# ─── Pydantic Models ───

class CreateDemoRequest(BaseModel):
    name: str
    description: str = ""
    auto_record_mode: bool = False

class RecordAction(BaseModel):
    demo_id: str
    action: str
    selector: str = ""
    value: str = ""
    url: str = ""

class AnalyzeRequest(BaseModel):
    demo_id: str

class ReplayRequest(BaseModel):
    demo_id: str
    variables: dict = {}


# ═══════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════

@router.get("/status")
async def status():
    """系统状态"""
    conn = _db()
    dc = conn.execute("SELECT COUNT(*) FROM demonstrations").fetchone()[0]
    rc = conn.execute("SELECT COUNT(*) FROM recordings").fetchone()[0]
    skill_count = 0
    if SKILLS_CUSTOM_DIR.exists():
        skill_count = len([d for d in SKILLS_CUSTOM_DIR.iterdir() if (d / "SKILL.md").exists()])
    return {
        "success": True,
        "demonstrations": dc,
        "recordings": rc,
        "generated_skills": skill_count,
        "active_recordings": len(_active_recordings),
        "active_replays": len(_active_replays),
        "engine": "ready"
    }


@router.post("/demo/create")
async def create_demo(req: CreateDemoRequest):
    """创建新的演示录制"""
    conn = _db()
    did = hashlib.md5((req.name + str(time.time())).encode()).hexdigest()[:12]
    now = time.time()
    conn.execute(
        "INSERT INTO demonstrations(id,name,description,created_at,updated_at) VALUES(?,?,?,?,?)",
        (did, req.name, req.description, now, now)
    )
    conn.commit()

    # 如果是自动录制模式, 启动 Playwright 录制会话
    session = None
    if req.auto_record_mode:
        session = await _start_recording_session(did, req.name)

    return {
        "success": True,
        "id": did,
        "message": f"演示 '{req.name}' 已创建",
        "auto_recording": req.auto_record_mode,
        "session_id": session.get("session_id") if session else None
    }


@router.post("/record")
async def record_action(req: RecordAction):
    """录制一个操作步骤 (手动)"""
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (req.demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "演示不存在"}
    rid = hashlib.md5((req.demo_id + str(time.time())).encode()).hexdigest()[:16]
    max_order = conn.execute("SELECT MAX(order_num) FROM recordings WHERE demo_id=?", (req.demo_id,)).fetchone()[0] or 0
    conn.execute(
        "INSERT INTO recordings(id,demo_id,action,selector,value,url,timestamp,order_num) VALUES(?,?,?,?,?,?,?,?)",
        (rid, req.demo_id, req.action, req.selector, req.value, req.url, time.time(), max_order + 1)
    )
    conn.execute("UPDATE demonstrations SET updated_at=? WHERE id=?", (time.time(), req.demo_id))
    conn.commit()
    return {"success": True, "id": rid, "order": max_order + 1, "message": "步骤已录制"}


@router.post("/record-auto/{demo_id}")
async def record_auto_step(demo_id: str):
    """LLM自动执行并录制一步 (Playwright驱动)"""
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "演示不存在"}

    if demo_id not in _active_recordings:
        # 首次调用: 启动 Playwright + 分析任务
        result = await _auto_record(demo_id, demo["name"], demo["description"] or "")
        if not result.get("success"):
            return result
        _active_recordings[demo_id] = {"session": result, "started": time.time()}

    session = _active_recordings.get(demo_id, {})
    if session.get("done"):
        return {"success": True, "done": True, "message": "录制已完成"}

    # 执行下一步
    browser_session = session.get("session", {})
    next_action = browser_session.get("next_action")
    if next_action:
        # 保存到 recordings 表
        conn = _db()
        rid = hashlib.md5((demo_id + str(time.time())).encode()).hexdigest()[:16]
        max_order = conn.execute("SELECT MAX(order_num) FROM recordings WHERE demo_id=?", (demo_id,)).fetchone()[0] or 0
        conn.execute(
            "INSERT INTO recordings(id,demo_id,action,selector,value,url,timestamp,order_num) VALUES(?,?,?,?,?,?,?,?)",
            (rid, demo_id, next_action.get("action",""), next_action.get("selector",""),
             next_action.get("value",""), next_action.get("url",""), time.time(), max_order + 1)
        )
        conn.commit()

    return {
        "success": True,
        "step": browser_session.get("step_index", 0),
        "total_steps": browser_session.get("total_steps", 0),
        "current_action": browser_session.get("current_action", ""),
        "screenshot": browser_session.get("last_screenshot", ""),
        "url": browser_session.get("current_url", ""),
        "done": session.get("done", False)
    }


@router.post("/record-stop/{demo_id}")
async def stop_recording(demo_id: str):
    """停止自动录制"""
    if demo_id in _active_recordings:
        del _active_recordings[demo_id]
    return {"success": True, "message": "录制已停止"}


@router.post("/analyze/{demo_id}")
async def analyze_demo(demo_id: str):
    """AI 分析录制的操作，生成可复用技能代码"""
    conn = _db()
    recs = conn.execute("SELECT * FROM recordings WHERE demo_id=? ORDER BY order_num", (demo_id,)).fetchall()
    if not recs:
        return {"success": False, "error": "没有录制数据"}

    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    demo_name = demo["name"] if demo else "未命名"

    # 构建步骤描述
    steps_text = "\n".join([
        f"{r['order_num']}. [{r['action']}] selector='{r['selector']}' value='{r['value'][:60]}' url='{r['url'][:80]}'"
        for r in recs
    ])

    prompt = f"""分析以下浏览器操作序列，生成一份完整的 SKILL.md 文件。

演示名称: {demo_name}

操作步骤:
{steps_text}

请生成 SKILL.md，格式如下:
```markdown
---
name: {demo_name}
description: 此技能的简要描述
inputs:
  - name: 变量1
    description: 变量1的描述
    type: string
  - name: 变量2
    description: 变量2的描述  
    type: string
---

## 步骤

1. 步骤1的描述
2. 步骤2的描述
...

## 验证方法

- 如何确认任务成功执行
```

请直接输出 SKILL.md 内容，不要额外解释。"""

    skill_code = await _call_llm_for_skill(prompt, steps_text)

    conn.execute("UPDATE demonstrations SET skill_code=?, description=?, updated_at=? WHERE id=?",
                 (skill_code, f"AI从{len(recs)}步操作自动生成", time.time(), demo_id))
    conn.commit()

    return {
        "success": True,
        "skill_code": skill_code,
        "steps_count": len(recs),
        "message": "分析完成，已生成 Skill"
    }


@router.post("/generate-skill/{demo_id}")
async def generate_skill(demo_id: str):
    """从演示生成可安装的 SKILL.md (安装到 skills/custom/)"""
    conn = _db()
    recs = conn.execute("SELECT * FROM recordings WHERE demo_id=? ORDER BY order_num", (demo_id,)).fetchall()
    if not recs:
        return {"success": False, "error": "没有录制数据"}

    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "演示不存在"}

    demo_name = demo["name"]
    skill_dir_name = demo_name.lower().replace(" ", "_").replace("-", "_")[:32]
    skill_dir = SKILLS_CUSTOM_DIR / skill_dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 先生成 skill_code (如果还没生成)
    skill_code = demo["skill_code"] or "" if demo["skill_code"] else ""

    steps_text = "\n".join([
        f"{r['order_num']}. [{r['action']}] selector='{r['selector']}' value='{r['value'][:60]}' url='{r['url'][:80]}'"
        for r in recs
    ])

    if not skill_code:
        skill_code = await _call_llm_for_skill(f"演示名称: {demo_name}\n操作步骤:\n{steps_text}", steps_text)
        conn.execute("UPDATE demonstrations SET skill_code=? WHERE id=?", (skill_code, demo_id))
        conn.commit()

    # 生成 SKILL.md
    skill_md = f"""---
name: {demo_name}
description: 通过录屏学习自动生成的技能 - {len(recs)}步操作
inputs: []
version: 1.0
created_by: AUTO-EVO-AI Learn System
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

{skill_code}

## 原始录制信息

- 总步骤数: {len(recs)}
- 录制时间: {datetime.fromtimestamp(demo['created_at']).strftime('%Y-%m-%d %H:%M') if demo['created_at'] else 'N/A'}

## 操作步骤明细

{steps_text}
"""
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 生成 Python 脚本
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    py_code = _generate_python_script(recs, demo_name)
    (scripts_dir / "replay.py").write_text(py_code, encoding="utf-8")

    return {
        "success": True,
        "skill_path": str(skill_dir),
        "skill_name": demo_name,
        "message": f"技能 '{demo_name}' 已安装到 skills/custom/{skill_dir_name}/",
        "steps_count": len(recs)
    }


@router.post("/replay/{demo_id}")
async def replay_demo(demo_id: str):
    """使用 Playwright 回放演示操作"""
    conn = _db()
    recs = conn.execute("SELECT * FROM recordings WHERE demo_id=? ORDER BY order_num", (demo_id,)).fetchall()
    if not recs:
        return {"success": False, "error": "没有录制数据"}

    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    demo_name = demo["name"] if demo else "未命名"

    # 启动回放会话 (后台异步执行)
    session_id = uuid.uuid4().hex[:12]
    _active_replays[session_id] = {
        "demo_id": demo_id,
        "demo_name": demo_name,
        "status": "running",
        "current_step": 0,
        "total_steps": len(recs),
        "result": "",
        "error": None,
        "started_at": time.time()
    }

    # 后台执行回放
    asyncio.create_task(_execute_replay(session_id, recs))

    return {
        "success": True,
        "session_id": session_id,
        "demo_name": demo_name,
        "total_steps": len(recs),
        "message": "回放已开始"
    }


@router.get("/replay-status/{session_id}")
async def replay_status(session_id: str):
    """查询回放进度"""
    session = _active_replays.get(session_id)
    if not session:
        return {"success": False, "error": "回放会话不存在"}
    return {
        "success": True,
        "status": session["status"],
        "current_step": session["current_step"],
        "total_steps": session["total_steps"],
        "result": session.get("result", ""),
        "error": session.get("error"),
        "elapsed": round(time.time() - session["started_at"], 1)
    }


@router.get("/demo/{demo_id}")
async def get_demo(demo_id: str):
    """获取演示详情"""
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "不存在"}
    recs = conn.execute(
        "SELECT action,selector,value,url,order_num FROM recordings WHERE demo_id=? ORDER BY order_num",
        (demo_id,)
    ).fetchall()
    # 检查是否有对应 skill
    skill_path = None
    if demo["name"]:
        skill_dir_name = demo["name"].lower().replace(" ", "_").replace("-", "_")[:32]
        sp = SKILLS_CUSTOM_DIR / skill_dir_name / "SKILL.md"
        if sp.exists():
            skill_path = str(sp)
    return {
        "success": True,
        "demo": dict(demo),
        "recordings": [dict(r) for r in recs],
        "skill_path": skill_path
    }


@router.get("/list")
async def list_demos():
    """列出所有演示"""
    conn = _db()
    rows = conn.execute(
        "SELECT id,name,description,created_at,use_count FROM demonstrations ORDER BY created_at DESC"
    ).fetchall()
    demos = []
    for r in rows:
        d = dict(r)
        skill_dir_name = d["name"].lower().replace(" ", "_").replace("-", "_")[:32]
        has_skill = (SKILLS_CUSTOM_DIR / skill_dir_name / "SKILL.md").exists()
        d["has_skill"] = has_skill
        demos.append(d)
    return {"success": True, "demonstrations": demos}


@router.delete("/demo/{demo_id}")
async def delete_demo(demo_id: str):
    """删除演示(包括对应skill文件)"""
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "不存在"}

    # 删除 skill 目录
    skill_dir_name = demo["name"].lower().replace(" ", "_").replace("-", "_")[:32]
    skill_dir = SKILLS_CUSTOM_DIR / skill_dir_name
    if skill_dir.exists():
        import shutil
        shutil.rmtree(skill_dir, ignore_errors=True)

    conn.execute("DELETE FROM recordings WHERE demo_id=?", (demo_id,))
    conn.execute("DELETE FROM demonstrations WHERE id=?", (demo_id,))
    conn.commit()

    if demo_id in _active_recordings:
        del _active_recordings[demo_id]

    return {"success": True, "message": f"演示 '{demo['name']}' 已删除"}


# ═══════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════

async def _call_llm_for_skill(prompt: str, steps_text: str = "") -> str:
    """调用智谱 LLM 分析操作并生成 Skill 代码"""
    try:
        from api.agent_llm import call_llm, _get_key
        key = _get_key()
        if not key:
            return f"# 无法生成 Skill: 未配置 LLM Key\n# 请先设置 ZHIPU_API_KEY\n\n# 录制步骤:\n{steps_text[:500]}"
        content, _ = call_llm([{"role": "user", "content": prompt}], timeout=30)
        if content:
            return content
    except Exception as e:
        logger.warning(f"[LEARN] LLM调用失败: {e}")
    return f"# LLM分析失败\n# 请手动编辑\n\n# 录制步骤:\n{steps_text[:500]}"


async def _start_recording_session(demo_id: str, demo_name: str) -> dict:
    """启动 Playwright 录制会话"""
    try:
        from core.browser_engine import PlaywrightEngine
        engine = PlaywrightEngine(headless=True)
        result = await engine.launch()
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "浏览器启动失败")}
        # 导航到首页
        await engine.goto("about:blank")
        session = {
            "engine": engine,
            "demo_id": demo_id,
            "demo_name": demo_name,
            "step_index": 0,
            "actions": [],
            "started": time.time()
        }
        return {"success": True, "session_id": demo_id, "session": session}
    except Exception as e:
        logger.warning(f"[LEARN] 录制会话启动失败: {e}")
        return {"success": False, "error": str(e)}


async def _auto_record(demo_id: str, demo_name: str, description: str) -> dict:
    """LLM 驱动自动录制：分析任务意图 → 生成执行计划 → Playwright执行"""
    try:
        from api.agent_llm import call_llm, _get_key
        key = _get_key()
        if not key:
            return {"success": False, "error": "未配置 LLM Key"}

        # 1. LLM 生成执行计划
        plan_prompt = f"""任务: {description or demo_name}

请分析这个浏览器自动化任务，生成一个详细的执行计划（JSON数组）。
每步包含: action, selector, value, url
可能的action: navigate(导航), click(点击), fill(填表), screenshot(截图), scroll(滚动), extract(提取)

示例:
[
  {{"action": "navigate", "url": "https://www.baidu.com", "selector": "", "value": ""}},
  {{"action": "fill", "selector": "#kw", "value": "python教程", "url": ""}},
  {{"action": "click", "selector": "#su", "value": "", "url": ""}},
  {{"action": "extract", "selector": ".result", "value": "", "url": ""}}
]

只返回 JSON 数组，不要额外文字。"""
        plan_text, _ = call_llm([{"role": "user", "content": plan_prompt}], timeout=30)
        if not plan_text:
            return {"success": False, "error": "LLM 无法生成执行计划"}

        # 解析 JSON
        cleaned = plan_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        plan = json.loads(cleaned)
        if not isinstance(plan, list):
            plan = [plan]

        # 2. 启动 Playwright
        from core.browser_engine import PlaywrightEngine
        engine = PlaywrightEngine(headless=True)
        launch_result = await engine.launch()
        if not launch_result.get("success"):
            return {"success": False, "error": launch_result.get("error", "浏览器启动失败")}

        # 3. 逐条执行并录制
        executed_actions = []
        for i, step in enumerate(plan):
            action = step.get("action", "")
            selector = step.get("selector", "")
            value = step.get("value", "")
            url = step.get("url", "")

            try:
                if action == "navigate" and url:
                    r = await engine.goto(url)
                    await asyncio.sleep(2)
                elif action == "click" and selector:
                    if engine._page:
                        await engine._page.click(selector)
                        await asyncio.sleep(1)
                    r = {"success": True}
                elif action == "fill" and selector:
                    if engine._page:
                        await engine._page.fill(selector, value)
                        await asyncio.sleep(0.5)
                    r = {"success": True}
                elif action == "screenshot":
                    ss = await engine.screenshot(full_page=True) if hasattr(engine, 'screenshot') else {"success": False}
                    r = ss
                elif action == "scroll":
                    if engine._page:
                        await engine._page.evaluate(f"window.scrollBy(0, {value or 500})")
                        await asyncio.sleep(0.5)
                    r = {"success": True}
                else:
                    r = {"success": True}

                executed_actions.append({
                    "action": action,
                    "selector": selector,
                    "value": value,
                    "url": url,
                    "result": r.get("success", False),
                    "timestamp": time.time(),
                    "order_num": i + 1
                })
            except Exception as step_err:
                executed_actions.append({
                    "action": action,
                    "selector": selector,
                    "value": value,
                    "url": url,
                    "result": False,
                    "error": str(step_err),
                    "timestamp": time.time(),
                    "order_num": i + 1
                })

        # 4. 保存到数据库
        conn = _db()
        for act in executed_actions:
            rid = hashlib.md5((demo_id + str(time.time() + act["order_num"])).encode()).hexdigest()[:16]
            conn.execute(
                "INSERT INTO recordings(id,demo_id,action,selector,value,url,timestamp,order_num) VALUES(?,?,?,?,?,?,?,?)",
                (rid, demo_id, act["action"], act["selector"], act["value"], act.get("url", ""),
                 act["timestamp"], act["order_num"])
            )
        conn.execute("UPDATE demonstrations SET updated_at=? WHERE id=?", (time.time(), demo_id))
        conn.commit()

        # 5. 关闭浏览器
        await engine.close()

        # 6. 自动生成 SKILL.md
        skill_code = await _call_llm_for_skill(
            f"演示名称: {demo_name}\n操作步骤:\n" + "\n".join([
                f"{a['order_num']}. [{a['action']}] {a.get('selector','')} = '{a.get('value','')}'"
                for a in executed_actions
            ]),
            ""
        )
        conn.execute("UPDATE demonstrations SET skill_code=? WHERE id=?", (skill_code, demo_id))
        conn.commit()

        # 标记录制完成
        _active_recordings[demo_id] = {
            "done": True,
            "steps_count": len(executed_actions),
            "skill_generated": bool(skill_code)
        }

        return {
            "success": True,
            "steps_executed": len(executed_actions),
            "steps_failed": sum(1 for a in executed_actions if not a["result"]),
            "skill_generated": bool(skill_code),
            "plan": plan
        }

    except json.JSONDecodeError:
        return {"success": False, "error": "LLM返回的JSON格式错误"}
    except Exception as e:
        logger.error(f"[LEARN] 自动录制失败: {e}")
        return {"success": False, "error": str(e)}


async def _execute_replay(session_id: str, recordings: list):
    """后台执行回放"""
    try:
        from core.browser_engine import PlaywrightEngine
        engine = PlaywrightEngine(headless=False)
        launch_result = await engine.launch()
        if not launch_result.get("success"):
            _active_replays[session_id]["status"] = "failed"
            _active_replays[session_id]["error"] = launch_result.get("error", "启动失败")
            return

        for i, rec in enumerate(recordings):
            _active_replays[session_id]["current_step"] = i + 1
            action = rec["action"]
            selector = rec["selector"]
            value = rec["value"]
            url = rec["url"]

            try:
                if action == "navigate" and url:
                    await engine.goto(url)
                    await asyncio.sleep(1.5)
                elif action == "click":
                    if engine._page and selector:
                        try:
                            await engine._page.click(selector, timeout=5000)
                        except Exception:
                            # try by text
                            try:
                                await engine._page.click(f"text={selector}", timeout=5000)
                            except Exception as _ex:
                                logger.warning(f"[routes_learn]" + str(_ex)[:80])
                    await asyncio.sleep(1)
                elif action == "fill":
                    if engine._page and selector:
                        try:
                            await engine._page.fill(selector, value, timeout=5000)
                        except Exception as _ex:
                            logger.warning(f"[routes_learn]" + str(_ex)[:80])
                    await asyncio.sleep(0.5)
                elif action == "screenshot":
                    if hasattr(engine, 'screenshot'):
                        await engine.screenshot(full_page=True)
                elif action == "scroll":
                    if engine._page:
                        pixels = int(value) if value and value.isdigit() else 500
                        await engine._page.evaluate(f"window.scrollBy(0, {pixels})")
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"[REPLAY] 步骤{i+1}执行失败: {e}")

        await engine.close()
        _active_replays[session_id]["status"] = "completed"
        _active_replays[session_id]["result"] = f"回放完成，共{len(recordings)}步"
        _active_replays[session_id]["ended_at"] = time.time()

        # 更新使用计数
        if recordings:
            demo_id = recordings[0]["demo_id"]
            conn = _db()
            conn.execute("UPDATE demonstrations SET use_count=use_count+1 WHERE id=?", (demo_id,))
            conn.commit()

    except Exception as e:
        _active_replays[session_id]["status"] = "failed"
        _active_replays[session_id]["error"] = str(e)


def _generate_python_script(recordings, demo_name) -> str:
    """从录制步骤生成可执行的 Python 回放脚本"""
    lines = [
        f'"""',
        f'AUTO-EVO-AI 自动生成的回放脚本: {demo_name}',
        f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'步骤数: {len(recordings)}',
        f'"""',
        '',
        'import asyncio',
        'import sys',
        'sys.path.insert(0, ".")',
        '',
        '',
        'async def replay():',
        '    """Execute the recorded skill"""',
        '    try:',
        '        from core.browser_engine import PlaywrightEngine',
        '        engine = PlaywrightEngine(headless=False)',
        '        result = await engine.launch()',
        '        if not result.get("success"):',
        f'            print(f"Failed: {{result.get(\\"error\\")}}")',
        '            return',
        '',
    ]

    for i, rec in enumerate(recordings):
        action = rec["action"]
        selector = rec["selector"]
        value = rec["value"]
        url = rec["url"]
        lines.append(f'        # Step {i+1}: {action}')
        if action == "navigate" and url:
            lines.append(f'        await engine.goto("{url}")')
            lines.append('        await asyncio.sleep(1.5)')
        elif action == "click" and selector:
            escaped = selector.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'        try:')
            lines.append(f'            await engine._page.click("{escaped}", timeout=5000)')
            lines.append(f'        except:')
            lines.append(f'            try:')
            lines.append(f'                await engine._page.click(f"text={{selector}}", timeout=5000)')
            lines.append(f'            except: pass')
            lines.append(f'        await asyncio.sleep(1)')
        elif action == "fill" and selector:
            escaped_sel = selector.replace('\\', '\\\\').replace('"', '\\"')
            escaped_val = value.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'        try:')
            lines.append(f'            await engine._page.fill("{escaped_sel}", "{escaped_val}", timeout=5000)')
            lines.append(f'        except: pass')
            lines.append(f'        await asyncio.sleep(0.5)')
        elif action == "scroll":
            pixels = int(value) if value and value.isdigit() else 500
            lines.append(f'        await engine._page.evaluate("window.scrollBy(0, {pixels})")')
            lines.append(f'        await asyncio.sleep(0.5)')
        elif action == "screenshot":
            lines.append(f'        await engine.screenshot(full_page=True)')
        else:
            lines.append(f'        # unknown action: {action}')
        lines.append('')

    lines.extend([
        '    await engine.close()',
        '    print("Replay completed")',
        '',
        '',
        'if __name__ == "__main__":',
        '    asyncio.run(replay())',
    ])

    return '\n'.join(lines)
