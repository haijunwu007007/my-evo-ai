"""
AUTO-EVO-AI V0.1 — Skill 标准化接口
全量外部集成：WorkBuddy 技能目录 + MCP 工具桥接 + 项目级技能 + 手动注册
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, importlib, inspect, hashlib, httpx, re
from pathlib import Path

logger = get_logger("evo.api.skills")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── 数据模型 ──────────────────────────
class SkillDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "auto-evo-ai"
    category: str = "通用"
    icon: str = "🔧"
    tags: list = []
    input_schema: dict = {}
    output_schema: dict = {}
    handler: str = ""   # module.function 路径
    endpoint: str = ""  # API 端点或 MCP 桥接

class SkillExecuteRequest(BaseModel):
    params: dict = {}
    context: Optional[dict] = {}

# ─── 注册表 ──────────────────────────
_SKILL_REGISTRY: dict[str, SkillDefinition] = {}
_SKILL_HANDLERS: dict[str, callable] = {}
_SKILL_EXECUTION_LOG: list = []


# ============================================================
# 1. 内置技能
# ============================================================
def _load_builtin_skills():
    """从 skills/builtin/ 目录加载内置技能"""
    builtin_dir = BASE_DIR / "skills" / "builtin"
    builtin_dir.mkdir(parents=True, exist_ok=True)

    # Python 模块
    for f in sorted(builtin_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        mod_name = f"skills.builtin.{f.stem}"
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "skill_def"):
                sd = getattr(mod, "skill_def")
                if isinstance(sd, dict):
                    skill = SkillDefinition(**sd)
                    _SKILL_REGISTRY[skill.name] = skill
                    if hasattr(mod, "execute"):
                        _SKILL_HANDLERS[skill.name] = getattr(mod, "execute")
                        logger.info(f"  ✅ Skill loaded: {skill.name} v{skill.version}")
        except Exception as e:
            logger.warning(f"  ⚠️  Skill: {f.name}: {e}")

    # JSON 定义
    for f in sorted(builtin_dir.glob("*.json")):
        try:
            data = json.load(open(f, encoding="utf-8"))
            items = data if isinstance(data, list) else [data]
            for item in items:
                skill = SkillDefinition(**item)
                _SKILL_REGISTRY[skill.name] = skill
        except Exception as e:
            logger.warning(f"  ⚠️  Skill json: {f.name}: {e}")


def _load_custom_skills():
    """从 skills/custom/ 加载自定义技能"""
    custom_dir = BASE_DIR / "skills" / "custom"
    if not custom_dir.exists():
        return
    for f in sorted(custom_dir.glob("*")):
        if f.is_dir():
            # 子目录: 尝试读取 SKILL.md
            smd = f / "SKILL.md"
            if smd.exists():
                _register_from_skill_md(smd, f.name, "custom", f"skills/custom/{f.name}")
        elif f.suffix == ".py" and not f.name.startswith("_"):
            mod_name = f"skills.custom.{f.stem}"
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "skill_def"):
                    data = getattr(mod, "skill_def")
                    if isinstance(data, dict):
                        skill = SkillDefinition(**data)
                        _SKILL_REGISTRY[skill.name] = skill
                        if hasattr(mod, "execute"):
                            _SKILL_HANDLERS[skill.name] = getattr(mod, "execute")
            except Exception as e:
                logger.warning(f"  ⚠️  Custom skill: {f.name}: {e}")


# ============================================================
# 2. 外部技能 — 全量发现（WorkBuddy 所有技能目录）
# ============================================================
def _register_from_skill_md(skill_md: Path, name: str, source: str, handler_path: str = ""):
    """从 SKILL.md 解析并注册技能"""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")

        skill_name = ""
        desc = ""
        tags = []
        gh_url = ""

        for line in lines:
            if line.startswith("# ") and not skill_name:
                skill_name = line[2:].strip()
            elif line.startswith("- GitHub:"):
                gh_url = line.split(": ", 1)[-1].strip() if ": " in line else ""

        if not skill_name:
            skill_name = name

        # 提取 tags
        in_capabilities = False
        for line in lines:
            if line.startswith("## 核心能力") or line.startswith("能力"):
                in_capabilities = True
                continue
            if in_capabilities:
                if line.startswith("## ") or line.strip() == "---":
                    in_capabilities = False
                    continue
                if line.startswith("- "):
                    tags.append(line[2:].strip())

        slug = skill_name.lower().replace(" ", "-").replace("/", "-")

        skill = SkillDefinition(
            name=slug,
            version="1.0.0",
            description=desc or f"WorkBuddy 外部技能: {skill_name}",
            author="WorkBuddy",
            category="外部集成",
            icon="🔌",
            tags=tags[:10] if tags else [skill_name],
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            handler=handler_path,
            endpoint=gh_url or "",
        )
        if skill.name not in _SKILL_REGISTRY:
            _SKILL_REGISTRY[skill.name] = skill
            return True
    except Exception as e:
        logger.warning(f"  ⚠️  SKILL.md parse: {skill_md.name}: {e}")
    return False


def _scan_external_skills():
    """扫描 ALL WorkBuddy 技能目录 → 自动发现标准技能"""
    # 扫描目录列表（覆盖所有可能的技能来源）
    ext_dirs = [
        Path.home() / ".workbuddy" / "skills" / "auto-discovered",
        Path.home() / ".workbuddy" / "skills",
    ]

    # 也扫描当前工作区的 .workbuddy/skills/
    try:
        ws_path = Path.cwd() / ".workbuddy" / "skills"
        if ws_path.exists():
            ext_dirs.append(ws_path)
        # 尝试 D 盘项目
        d_ws = Path("D:/AUTO-EVO-AI-V0.1/.workbuddy/skills")
        if d_ws.exists():
            ext_dirs.append(d_ws)
    except Exception:
            pass

    found = 0
    for ext_dir in ext_dirs:
        if not ext_dir.exists():
            continue
        for item in sorted(ext_dir.iterdir()):
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    if _register_from_skill_md(skill_md, item.name, "workbuddy"):
                        found += 1
            elif item.suffix == ".md" and item.name.upper() == "SKILL.MD":
                dir_name = item.parent.name
                if _register_from_skill_md(item, dir_name, "workbuddy"):
                    found += 1

    if found:
        logger.info(f"  🔌 扫描到 {found} 个外部 Skill")


# ============================================================
# 3. MCP 工具桥接为技能
# ============================================================
def _bridge_mcp_tools_as_skills():
    """将 MCP 注册表中的所有工具桥接为技能"""
    try:
        from api.routes.routes_mcp import get_mcp_tools_as_skills
        mcp_skills = get_mcp_tools_as_skills()
        count = 0
        for skill_dict in mcp_skills:
            name = skill_dict["name"]
            if name not in _SKILL_REGISTRY:
                skill = SkillDefinition(**skill_dict)
                _SKILL_REGISTRY[name] = skill
                count += 1
        if count:
            logger.info(f"  [BRIDGE] MCP 工具桥接为 Skill: {count} 个")
    except Exception as e:
        logger.warning(f"  ⚠️  MCP 桥接失败: {e}")


def _bridge_connectors_as_skills():
    """将连接器注册表桥接为技能"""
    try:
        from api.routes.routes_connectors import get_connector_skills
        connector_skills = get_connector_skills()
        count = 0
        for skill_dict in connector_skills:
            name = skill_dict.get("name", "")
            if name and name not in _SKILL_REGISTRY:
                _SKILL_REGISTRY[name] = SkillDefinition(**skill_dict)
                count += 1
        if count:
            logger.info(f"  🔗 连接器桥接: {count} 个技能")
    except Exception as e:
        logger.warning(f"  ⚠️ 连接器桥接失败: {e}")


def _bridge_mcpize_as_skills():
    """将 MCPize 万能集成桥的工具桥接为技能"""
    try:
        from api.routes.routes_mcpize import get_mcpize_skills
        skills = get_mcpize_skills()
        count = 0
        for sd in skills:
            name = sd.get("name", "")
            if name and name not in _SKILL_REGISTRY:
                _SKILL_REGISTRY[name] = SkillDefinition(**sd)
                count += 1
        if count:
            logger.info(f"  🧩 MCPize 桥接: {count} 个技能")
    except Exception as e:
        logger.warning(f"  ⚠️ MCPize 桥接失败: {e}")


def _bridge_gateway_as_skills():
    """将 Gateway 集成模板桥接为技能"""
    try:
        from api.routes.routes_gateway import list_gateway_as_skills
        skills = list_gateway_as_skills()
        count = 0
        for sd in skills:
            name = sd.get("name", "")
            if name and name not in _SKILL_REGISTRY:
                _SKILL_REGISTRY[name] = SkillDefinition(**sd)
                count += 1
        if count:
            logger.info(f"  🔗 Gateway 桥接: {count} 个技能")
    except Exception as e:
        logger.warning(f"  ⚠️ Gateway 桥接失败: {e}")


# ============================================================
# 4. 初始化
# ============================================================
def init_skills():
    """初始化所有技能（内置 + 外部 + MCP 桥接）"""
    _load_builtin_skills()
    _load_custom_skills()
    _scan_external_skills()
    _bridge_mcp_tools_as_skills()
    _bridge_connectors_as_skills()
    _bridge_mcpize_as_skills()
    _bridge_gateway_as_skills()
    count = len(_SKILL_REGISTRY)
    logger.info(f"[SKILL] 技能注册完毕: {count} 个技能（内置 + 外部 + MCP桥接 + 连接器桥接 + MCPize + Gateway桥接）")
    return count

init_skills()


# ============================================================
# 5. API 端点
# ============================================================

@router.get("/api/v1/skills")
async def list_skills(category: str = ""):
    """列出所有技能，可按分类过滤"""
    skills = list(_SKILL_REGISTRY.values())
    if category:
        skills = [s for s in skills if s.category == category]
    return {"success": True, "skills": [s.model_dump() for s in skills], "total": len(skills)}


@router.get("/api/v1/skills/search")
async def search_skills(q: str = ""):
    """搜索技能（名称/描述/标签）"""
    if not q:
        return await list_skills()
    ql = q.lower()
    results = []
    for s in _SKILL_REGISTRY.values():
        if (ql in s.name.lower() or
            ql in s.description.lower() or
            any(ql in t.lower() for t in s.tags)):
            results.append(s)
    return {"success": True, "skills": [s.model_dump() for s in results], "total": len(results)}


@router.get("/api/v1/skills/{name}")
async def get_skill(name: str):
    """获取单个技能详情"""
    if name not in _SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return {"success": True, "skill": _SKILL_REGISTRY[name].model_dump()}


@router.post("/api/v1/skills/register")
async def register_skill(skill: SkillDefinition):
    """注册自定义技能"""
    if skill.name in _SKILL_REGISTRY:
        return {"success": False, "detail": f"Skill already exists: {skill.name}"}
    _SKILL_REGISTRY[skill.name] = skill
    logger.info(f"  ✅ Skill registered: {skill.name} v{skill.version}")
    return {"success": True, "result": f"Skill registered: {skill.name} v{skill.version}"}


@router.post("/api/v1/skills/{name}/execute")
async def execute_skill(name: str, req: SkillExecuteRequest):
    """执行技能"""
    if name not in _SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    skill = _SKILL_REGISTRY[name]
    start = time.time()

    try:
        # 1) 有 Python handler
        if name in _SKILL_HANDLERS:
            result = _SKILL_HANDLERS[name](req.params, req.context)
            elapsed = time.time() - start
            _log_execution(name, True, elapsed)
            return {"success": True, "result": result, "execution_time": round(elapsed, 3)}

        # 2) MCP 工具桥接
        if skill.name.startswith("mcp:"):
            mcp_path = skill.name[4:]  # "server_name/tool_name"
            if "/" in mcp_path:
                srv_name, tool_name = mcp_path.split("/", 1)
                try:
                    from api.routes.routes_mcp import _execute_external_mcp_tool
                    result = await _execute_external_mcp_tool(srv_name, tool_name, req.params)
                    elapsed = time.time() - start
                    _log_execution(name, result.get("success", False), elapsed)
                    return {"success": result.get("success", False), "result": result.get("content", ""), "execution_time": round(elapsed, 3)}
                except Exception:
                    pass

        # 3) 有 endpoint → HTTP 调用
        if skill.endpoint and not skill.endpoint.startswith("mcp://"):
            if skill.endpoint.startswith("http"):
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(skill.endpoint, json=req.params)
                    elapsed = time.time() - start
                    _log_execution(name, resp.is_success, elapsed)
                    try:
                        return {"success": True, "result": resp.json(), "execution_time": round(elapsed, 3)}
                    except:
                        return {"success": True, "result": resp.text, "execution_time": round(elapsed, 3)}

        # 4) LLM 自主执行降级 — 无 handler 时用 LLM 推理
        _any_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY","ZHIPU_API_KEY","DEEPSEEK_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY"))
        if _any_key:
            try:
                from api.agent_llm import call_llm
                sp = f"你是一个技能执行专家。技能名称: {skill.name}，描述: {skill.description}，输入参数: {json.dumps(req.params, ensure_ascii=False)}，上下文: {json.dumps(req.context or {}, ensure_ascii=False)}。请根据技能描述和输入参数直接执行该技能的任务，输出结果。"
                content, _ = call_llm([{"role":"user","content":sp}])
                if content:
                    elapsed = time.time() - start
                    _log_execution(name, True, elapsed)
                    return {"success": True, "result": content, "execution_time": round(elapsed, 3), "mode": "llm_fallback"}
            except Exception:
                pass

        # 5) 降级：描述模式
        elapsed = time.time() - start
        return {"success": True, "result": {
            "message": f"Skill '{name}' 已就绪，但没有注册执行器。",
            "description": skill.description,
            "input_schema": skill.input_schema,
            "mcp_endpoint": f"/api/v1/mcp/{mcp_path}" if skill.name.startswith("mcp:") else ""
        }, "execution_time": round(elapsed, 3)}

    except Exception as e:
        elapsed = time.time() - start
        _log_execution(name, False, elapsed)
        return {"success": False, "detail": str(e), "execution_time": round(elapsed, 3)}


@router.get("/api/v1/skills/stats/log")
async def skill_execution_log(limit: int = 20):
    """获取最近执行日志"""
    return {"success": True, "logs": _SKILL_EXECUTION_LOG[-limit:]}


@router.post("/api/v1/skills/import")
async def import_skill_from_workbuddy(name: str):
    """从外部技能目录导入为自定义技能"""
    # 搜索所有外部目录
    ext_dirs = [
        Path.home() / ".workbuddy" / "skills" / "auto-discovered",
        Path.home() / ".workbuddy" / "skills",
    ]
    try:
        ws = Path.cwd() / ".workbuddy" / "skills"
        if ws.exists():
            ext_dirs.append(ws)
        d_ws = Path("D:/AUTO-EVO-AI-V0.1/.workbuddy/skills")
        if d_ws.exists():
            ext_dirs.append(d_ws)
    except Exception:
            pass

    found_dir = None
    for ext_dir in ext_dirs:
        if not ext_dir.exists():
            continue
        target = ext_dir / name
        if target.is_dir():
            found_dir = target
            break
        # 大小写不敏感匹配
        for d in ext_dir.iterdir():
            if d.is_dir() and d.name.lower() == name.lower():
                found_dir = d
                break
        if found_dir:
            break

    if not found_dir:
        return {"success": False, "detail": f"外部技能 '{name}' 未找到"}

    custom_dir = BASE_DIR / "skills" / "custom" / found_dir.name
    custom_dir.mkdir(parents=True, exist_ok=True)

    src_md = found_dir / "SKILL.md"
    if src_md.exists():
        dst_md = custom_dir / "SKILL.md"
        dst_md.write_text(src_md.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

    # 注册
    _register_from_skill_md(src_md, found_dir.name, "imported")
    logger.info(f"  📥 Skill 已导入: {found_dir.name}")
    return {"success": True, "result": f"Skill '{found_dir.name}' 已导入到 skills/custom/{found_dir.name}/"}


@router.post("/api/v1/skills/install-github")
async def install_skill_from_github(repo_url: str):
    """从 GitHub 安装技能"""
    try:
        # 提取用户名/仓库名
        m = re.match(r'(?:https?://github\.com/)?([^/]+)/([^/]+?)(?:\.git)?$', repo_url.strip())
        if not m:
            return {"success": False, "detail": "无效的 GitHub 仓库 URL"}
        user, repo = m.group(1), m.group(2)

        # 从 GitHub API 获取仓库信息
        async with httpx.AsyncClient(timeout=15) as client:
            api_url = f"https://api.github.com/repos/{user}/{repo}"
            r = await client.get(api_url)
            if r.status_code != 200:
                return {"success": False, "detail": f"GitHub API 返回 {r.status_code}"}
            data = r.json()

        # 注册为技能
        skill = SkillDefinition(
            name=repo.lower(),
            version="1.0.0",
            description= data.get("description", f"来自 GitHub 的外部技能: {user}/{repo}"),
            author=user,
            category="外部集成",
            icon="📦",
            tags=[repo, user, "github"],
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            endpoint=repo_url,
        )
        _SKILL_REGISTRY[skill.name] = skill
        logger.info(f"  📥 GitHub Skill 已安装: {skill.name}")
        return {"success": True, "result": f"Skill '{skill.name}' 已从 GitHub 安装", "stars": data.get("stargazers_count", 0)}
    except Exception as e:
        return {"success": False, "detail": f"安装失败: {e}"}


# ─── 内部帮助函数 ─────────────────────
def _log_execution(name: str, ok: bool, elapsed: float):
    _SKILL_EXECUTION_LOG.append({
        "skill": name,
        "success": ok,
        "time": round(time.time(), 3),
        "elapsed": round(elapsed, 3)
    })
    if len(_SKILL_EXECUTION_LOG) > 1000:
        _SKILL_EXECUTION_LOG[:] = _SKILL_EXECUTION_LOG[-500:]


def get_skill_by_name(name: str) -> Optional[SkillDefinition]:
    return _SKILL_REGISTRY.get(name)


# ===== Merged from routes_skills_market.py =====
"""
AUTO-EVO-AI V0.1 — 技能市场路由
提供 Skills 安装/搜索/分类浏览 API
"""
from fastapi import APIRouter, Request
import json, subprocess, sys, os
from pathlib import Path

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE / "modules"
CLONE_DIR = BASE / "skills" / "marketplace"

# 预定义技能市场数据（对标OpenClaw ClawHub）
MARKET_SKILLS = [
    {"id": "bird-twitter", "name": "🐦 Bird 推特运营", "category": "social", "desc": "发推/搜索/回复/时间线管理", "grade": "A"},
    {"id": "ga4-analytics", "name": "📊 GA4 分析", "category": "analytics", "desc": "Google Analytics流量/用户/转化追踪", "grade": "A"},
    {"id": "gsc-search", "name": "🔍 GSC 搜索控制台", "category": "analytics", "desc": "Google Search Console关键词/索引分析", "grade": "A"},
    {"id": "swot-analyzer", "name": "🧠 SWOT 分析器", "category": "thinking", "desc": "优劣势/机会/威胁结构化分析", "grade": "A"},
    {"id": "first-principles", "name": "🧩 第一性原理", "category": "thinking", "desc": "复杂问题拆解分析框架", "grade": "A"},
    {"id": "decision-tree", "name": "🌳 决策树", "category": "thinking", "desc": "多方案决策分析与推荐", "grade": "A"},
    {"id": "lead-catcher", "name": "🎯 线索捕获", "category": "crm", "desc": "潜在客户自动抓取与分类", "grade": "A"},
    {"id": "plagiarism-check", "name": "📝 查重检测", "category": "content", "desc": "文本查重与原创度优化", "grade": "A"},
    {"id": "title-optimizer", "name": "🏷️ 标题优化", "category": "content", "desc": "多平台标题优化提升点击率", "grade": "A"},
    {"id": "reference-checker", "name": "📚 引用检查", "category": "content", "desc": "文献引用格式自动规范", "grade": "A"},
    {"id": "pomodoro-timer", "name": "⏰ 番茄钟", "category": "productivity", "desc": "番茄工作法计时器与专注统计", "grade": "A"},
    {"id": "time-blocker", "name": "📅 时间块", "category": "productivity", "desc": "时间块管理与每日规划", "grade": "A"},
    {"id": "wechat-oa", "name": "💬 公众号运营", "category": "social", "desc": "公众号选题/排版/发布管理", "grade": "A"},
    {"id": "humanizer", "name": "🎭 AI去痕迹", "category": "content", "desc": "去除AI写作痕迹，让文本更自然", "grade": "A"},
]

@router.get("/api/v1/skills/market")
async def list_market_skills(category: str = ""):
    """技能市场列表"""
    skills = MARKET_SKILLS
    if category:
        skills = [s for s in skills if s["category"] == category]
    # 检查本地是否已安装
    installed_modules = {p.stem for p in SKILLS_DIR.glob("*.py") if not p.stem.startswith("_")}
    for s in skills:
        s["installed"] = s["id"] in installed_modules
    return {"success": True, "skills": skills, "total": len(skills)}

@router.get("/api/v1/skills/market/categories")
async def list_market_categories():
    """技能市场分类"""
    cats = {}
    for s in MARKET_SKILLS:
        c = s["category"]
        if c not in cats:
            cats[c] = {"name": c, "count": 0}
        cats[c]["count"] += 1
    return {"success": True, "categories": cats}

@router.post("/api/v1/skills/market/install")
async def install_market_skill(req: Request):
    body = await req.json()
    skill_id = body.get("skill_id", "")
    if not skill_id:
        return {"success": False, "error": "skill_id required"}
    skill = next((s for s in MARKET_SKILLS if s["id"] == skill_id), None)
    if not skill:
        return {"success": False, "error": "skill not found"}
    mp = SKILLS_DIR / (skill_id + ".py")
    if mp.exists():
        return {"success": True, "result": skill["name"] + " ready"}
    sid = skill_id.replace("-", "_")
    cn = "".join(x.capitalize() for x in sid.split("_"))
    c = json.dumps({"id": skill_id, "name": cn, "version": "V0.1", "group": skill["category"], "grade": "A", "description": skill["desc"]}, ensure_ascii=False)
    c += "\nfrom modules._base.enterprise_module import EnterpriseModule"
    c += "\nclass " + cn + "(EnterpriseModule):"
    c += '\n    async def execute(self,action="run",params=None):'
    c += '\n        return {"success":True,"module":"' + skill_id + '","action":action}'
    c += '\nmodule_class = ' + cn
    try:
        mp.write_text(c, encoding="utf-8")
        return {"success": True, "result": skill["name"] + " installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/skills/clawhub/install")
async def install_from_clawhub(req: Request):
    body = await req.json()
    sn = body.get("skill_name", "")
    if not sn:
        return {"success": False, "error": "skill_name required"}
    import subprocess as _sp
    safe = sn.replace("/","_").replace(" ","_")
    try:
        r = _sp.run(["npx","clawhub","install",sn], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return {"success": False, "error": r.stderr[:500]}
        bp = SKILLS_DIR / ("clawhub_" + safe + ".py")
        cn = "".join(x.capitalize() for x in safe.split("_"))
        bc = '"""ClawHub: ' + sn + '"""\n'
        bc += 'import subprocess as _sp\n'
        bc += 'from modules._base.enterprise_module import EnterpriseModule\n'
        bc += 'class ' + cn + '(EnterpriseModule):\n'
        bc += '    async def execute(self,action="run",params=None):\n'
        bc += '        try:\n'
        bc += '            r = _sp.run(["npx","clawhub","run","' + sn + '"], capture_output=True, text=True, timeout=30)\n'
        bc += '            return {"success": r.returncode == 0, "output": r.stdout[:2000]}\n'
        bc += '        except Exception as e:\n'
        bc += '            return {"success": False, "error": str(e)}\n'
        bc += 'module_class = ' + cn
        bp.write_text(bc, encoding="utf-8")
        return {"success": True, "result": "ClawHub " + sn + " bridged", "module": "clawhub_" + safe}
    except FileNotFoundError:
        return {"success": False, "error": "npx not found"}
    except _sp.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}
def register_routes(app):
    app.include_router(router)

setup_skills_market_routes = register_routes
