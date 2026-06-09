"""🧠 自主Agent引擎 V2 — LLM自动识别意图 → 注入外部SKILL.md → 多步技能执行 → 汇总结果

关键改进:
1. 启动时扫描 ~/.workbuddy/skills/ 下所有外部 Skill（含 auto-discovered 和市场）
2. 任务规划: LLM 获得完整 Skill 目录（含描述）+ 注入匹配 SKILL.md 内容
3. 执行: 先试 /api/v1/skills/{name}/execute, 降级则读 SKILL.md 注入 LLM 自主执行
4. 汇总: LLM 自动整理多步结果
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, asyncio, httpx, os
from pathlib import Path

logger = get_logger("evo.api.agent_engine")
router = APIRouter()

# ── 外部 Skill 目录扫描 ──
_SKILL_CATALOG: list[dict] = []  # [{name, description, skill_md_content, source_dir, stars, category}]

def _scan_external_skills():
    """扫描 ~/.workbuddy/skills/ 下所有外部 Skill 的 SKILL.md"""
    catalog = []
    search_dirs = [
        Path.home() / ".workbuddy" / "skills" / "auto-discovered",
        Path.home() / ".workbuddy" / "skills",
    ]
    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for skill_dir in base_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            meta_json = skill_dir / "_meta.json"
            if not skill_md.exists():
                continue

            # 读取 SKILL.md 内容
            md_content = skill_md.read_text(encoding="utf-8", errors="replace")

            # 读取 meta
            stars = 0
            category = ""
            if meta_json.exists():
                try:
                    meta = json.loads(meta_json.read_text(encoding="utf-8"))
                    stars = meta.get("stars", 0)
                    category = meta.get("category", "")
                except Exception:
            pass

            catalog.append({
                "name": skill_dir.name,
                "description": md_content.split("\n")[0].replace("#", "").strip()[:100],
                "skill_md_content": md_content,
                "source_dir": str(skill_dir),
                "stars": stars,
                "category": category,
            })

    # 从名称中提取简短描述行
    for s in catalog:
        for ln in s["skill_md_content"].split("\n"):
            ln = ln.strip()
            if ln.startswith("## 描述"):
                desc_line = ln.replace("## 描述", "").strip()
                # 取下一行
                continue
            if s.get("_desc_found") and ln and not ln.startswith("#"):
                s["description"] = ln.strip()[:150]
                break
            if "描述" in ln or "Description" in ln:
                s["_desc_found"] = True

    return catalog

# 启动时扫描一次
_SKILL_CATALOG = _scan_external_skills()
logger.info(f"[AGENT-V2] 扫描到 {len(_SKILL_CATALOG)} 个外部 Skill")

_AGENT_TASKS: dict = {}

class AgentRunRequest(BaseModel):
    task: str
    context: Optional[str] = ""

@router.post("/api/v1/agent/run")
async def agent_run(req: AgentRunRequest):
    """自主执行：LLM规划→调用技能→返回结果"""
    task = req.task.strip()
    if not task:
        raise HTTPException(400, "需要提供任务描述")
    task_id = f"task-{int(time.time())}-{os.urandom(2).hex()}"

    _AGENT_TASKS[task_id] = {"status": "planning", "task": task, "steps": [], "result": None, "progress": 0}

    try:
        # ── 1. 构建 Skill 目录（给 LLM 参考） ──
        skill_list = "\n".join(
            f"  - {s['name']}: {s['description'][:120]}" + (f" (⭐{s['stars']})" if s['stars'] else "")
            for s in _SKILL_CATALOG[:50]  # 最多50个
        )

        # ── 2. LLM 规划 ──
        plan_prompt = f"""你是一个AI任务规划器。分析任务: "{task}"

## 可用技能目录（共{len(_SKILL_CATALOG)}个）:
{skill_list if skill_list else "（无外部技能，使用内置工具）"}

## 内置工具:
search/翻译/计算/文档生成/PPT/Excel/代码生成/系统状态/待办/记忆/GitHub热门/爬虫

请列出需要执行的步骤（最多8步），每步格式: "步骤号. 技能名: 操作描述"
返回JSON数组: [{{"step":1,"tool":"技能名","action":"操作描述"}}]
如果任务匹配某个外部Skill，优先使用它。"""

        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": plan_prompt, "lang": "zh-CN"})
            plan_data = r.json().get("result", "[]")

        # 解析规划
        import re
        steps = []
        try:
            steps = json.loads(plan_data)
        except (json.JSONDecodeError, TypeError):
            try:
                # 尝试从 LLM 回复中提取 JSON 数组
                arr_match = re.search(r'\[.*?\]', plan_data, re.DOTALL)
                if arr_match:
                    steps = json.loads(arr_match.group())
            except Exception:
            pass

        if not steps:
            steps = [{"step": 1, "tool": "search", "action": f"搜索关于'{task}'的信息"},
                     {"step": 2, "tool": "chat", "action": f"总结搜索结果并回答: {task}"}]

        _AGENT_TASKS[task_id]["steps"] = steps
        _AGENT_TASKS[task_id]["total_steps"] = len(steps)

        # ── 3. 依次执行 ──
        results = []
        for i, step in enumerate(steps):
            _AGENT_TASKS[task_id]["status"] = f"执行步骤 {i+1}/{len(steps)}"
            _AGENT_TASKS[task_id]["progress"] = int((i / len(steps)) * 100)

            tool = step.get("tool", "chat")
            action = step.get("action", task)

            step_result = await _execute_step(tool, action, task)
            results.append({"step": i+1, "tool": tool, "action": action, "result": str(step_result)[:500]})

        _AGENT_TASKS[task_id]["status"] = "completed"
        _AGENT_TASKS[task_id]["progress"] = 100

        # ── 4. LLM 汇总 ──
        summary_prompt = f"任务: {task}\n执行结果:\n" + "\n".join(
            f"步骤{r['step']}({r['tool']}): {r['result'][:200]}" for r in results)

        async with httpx.AsyncClient(timeout=60) as c:
            sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
                json={"message": f"请用中文总结以下执行结果:\n{summary_prompt}", "lang": "zh-CN"})
            summary = sr.json().get("result", "执行完成")

        _AGENT_TASKS[task_id]["result"] = summary
        return {"success": True, "task_id": task_id, "steps": steps, "result": summary, "details": results}

    except Exception as e:
        _AGENT_TASKS[task_id]["status"] = "failed"
        _AGENT_TASKS[task_id]["result"] = str(e)
        return {"success": False, "task_id": task_id, "error": str(e)}


async def _execute_step(tool: str, action: str, original_task: str) -> str:
    """执行单一步骤 — 优先调用外部Skill，降级到内置工具"""
    smart_msg = action

    # ── 尝试调用外部 Skill ──
    for skill in _SKILL_CATALOG:
        if tool.lower() == skill["name"].lower():
            try:
                # 尝试通过 Skills API 执行
                async with httpx.AsyncClient(timeout=30) as c:
                    r = await c.post(
                        f"http://127.0.0.1:8765/api/v1/skills/{skill['name']}/execute",
                        json={"params": {"action": action, "task": original_task}, "context": {}},
                        timeout=15
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("success"):
                            result = data.get("result", "")
                            if isinstance(result, dict) and "message" in result:
                                # 降级模式 → 注入 SKILL.md 让 LLM 自主执行
                                return await _llm_guided_skill_exec(skill, action, original_task)
                            return str(result)[:500] if result else f"Skill {tool} 执行完毕"
            except Exception:
            pass

            # API 失败 → 注入 SKILL.md
            return await _llm_guided_skill_exec(skill, action, original_task)

    # ── 内置工具路由 ──
    tool_lower = tool.lower()
    if tool_lower in ("search", "搜索"):
        smart_msg = f"帮我搜索: {action}"
    elif tool_lower in ("crawl", "爬虫", "web", "scrape"):
        smart_msg = f"爬取: {action}"
    elif tool_lower in ("github", "trending", "git"):
        smart_msg = "GitHub今天热门项目"
    elif tool_lower in ("math", "计算", "calc"):
        smart_msg = f"计算: {action}"
    elif tool_lower in ("translate", "翻译"):
        smart_msg = f"翻译: {action}"
    elif tool_lower in ("doc", "文档", "word"):
        smart_msg = f"帮我写一份文档: {action}"
    elif tool_lower in ("ppt", "pptx", "presentation"):
        smart_msg = f"帮我做一个PPT: {action}"
    elif tool_lower in ("excel", "table", "xlsx"):
        smart_msg = f"帮我做表格: {action}"
    elif tool_lower in ("code", "代码", "codegen"):
        smart_msg = f"写代码: {action}"
    elif tool_lower in ("status", "系统", "system", "health"):
        smart_msg = "系统怎么样"
    elif tool_lower in ("chat", "summary", "回答", "总结"):
        smart_msg = action

    async with httpx.AsyncClient(timeout=60) as c:
        sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
            json={"message": smart_msg, "lang": "zh-CN"})
        sd = sr.json()
        return sd.get("result", sd.get("detail", "完成"))


async def _llm_guided_skill_exec(skill: dict, action: str, original_task: str) -> str:
    """当外部Skill没有Python handler时，注入SKILL.md内容让LLM自主执行"""
    md = skill.get("skill_md_content", "")
    prompt = f"""你是一个技能执行专家。以下是外部Skill "{skill['name']}" 的完整定义：

{md[:3000]}

用户任务: {original_task}
当前步骤操作: {action}

请根据SKILL.md的描述：
1. 判断这个Skill是否适合当前任务
2. 如果适合，编写执行计划（包括需要安装的依赖、调用方式、预期输出）
3. 如果不完全匹配，说明你能做什么来推进任务

请用中文回答，简明扼要。"""

    async with httpx.AsyncClient(timeout=60) as c:
        sr = await c.post("http://127.0.0.1:8765/api/v1/smart",
            json={"message": prompt, "lang": "zh-CN"})
        return sr.json().get("result", f"Skill {skill['name']} 已分析")


@router.get("/api/v1/agent/status/{task_id}")
async def agent_status(task_id: str):
    t = _AGENT_TASKS.get(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    return {"success": True, "task": t}

@router.get("/api/v1/agent/catalog")
async def agent_catalog():
    """查看所有可用外部Skill目录"""
    return {
        "success": True,
        "total": len(_SKILL_CATALOG),
        "skills": [{"name": s["name"], "description": s["description"][:100],
                     "stars": s["stars"], "category": s["category"]} for s in _SKILL_CATALOG]
    }
