"""YoYo-Evolve 自进化系统 V2 — 记忆+进化+自动修复+技能发现的完整闭环"""
import logging
logger = logging.getLogger("evo.yoyo_evolve")

import os, json, time, re, random, sqlite3, threading, shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# ════════════════════════════════════════════════════════════
# 核心模块
# ════════════════════════════════════════════════════════════
_EVOLVE_DB: Optional[sqlite3.Connection] = None
_EVOLVE_LOCK = threading.Lock()
BASE_DIR = Path(__file__).parent.parent
EVO_DB_PATH = BASE_DIR / "core" / "yoyo_evolve.db"

# 尝试加载 AdaptiveEngine
_ADAPTIVE = None
try:
    from core.evolution_engine import AdaptiveEngine
    _ADAPTIVE = AdaptiveEngine()
except Exception as _e:
    logger.warning(f"error: {_e}")


def _get_db():
    global _EVOLVE_DB
    if _EVOLVE_DB is None:
        _EVOLVE_DB = sqlite3.connect(str(EVO_DB_PATH), check_same_thread=False)
        _EVOLVE_DB.execute("""CREATE TABLE IF NOT EXISTS evolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, target TEXT, analysis TEXT,
            suggestion TEXT, status TEXT, result TEXT,
            score REAL, phase TEXT
        )""")
        _EVOLVE_DB.execute("""CREATE TABLE IF NOT EXISTS autofixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, file_path TEXT, backup_path TEXT,
            fix_type TEXT, status TEXT, result TEXT
        )""")
        _EVOLVE_DB.commit()
    return _EVOLVE_DB


def _log_evolution(target, analysis, suggestion, status="pending", result="", score=0.0, phase="scan"):
    db = _get_db()
    db.execute("INSERT INTO evolutions (timestamp, target, analysis, suggestion, status, result, score, phase) VALUES (?,?,?,?,?,?,?,?)",
               (time.time(), target[:100], analysis[:500], suggestion[:500], status, result[:500], score, phase))
    db.commit()
    # 同时记录到 AdaptiveEngine
    if _ADAPTIVE:
        try:
            _ADAPTIVE.record(module=target[:50], action=f"evolve_{phase}",
                             success=status == "completed", latency_ms=0,
                             context={"suggestion": suggestion[:200]})
        except Exception as _e:
            logger.warning(f"error: {_e}")


# ════════════════════════════════════════════════════════════
# Phase 1: 代码扫描 + 记忆回馈
# ════════════════════════════════════════════════════════════
def analyze_code(file_path: str) -> dict:
    """分析单个代码文件，返回改进建议"""
    try:
        fp = Path(file_path)
        if not fp.exists() or fp.suffix not in ('.py', '.js', '.ts', '.html'):
            return {"file": file_path, "issues": [], "quality": "skip"}
        code = fp.read_text(encoding='utf-8')
        issues = []
        lines = code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'except:' in stripped and 'Exception' not in stripped and i > 0 and '#' not in lines[i-1]:
                issues.append({"line": i+1, "type": "bare_except", "msg": "裸except"})
            if 'print(' in stripped and i > 5:
                issues.append({"line": i+1, "type": "debug_print", "msg": "调试print残留"})
            if len(stripped) > 200:
                issues.append({"line": i+1, "type": "long_line", "msg": f"超长行({len(stripped)}字符)"})
        score = max(100.0 - len(issues) * 5, 0)
        return {"file": file_path, "lines": len(lines), "size": fp.stat().st_size,
                "issues": issues, "issue_count": len(issues),
                "quality": "good" if score >= 80 else "needs_improvement" if score >= 50 else "poor",
                "score": round(score, 1)}
    except Exception as e:
        return {"file": file_path, "issues": [{"type": "error", "msg": str(e)[:100]}], "quality": "error"}


def auto_scan(base_dir: Path = None) -> dict:
    """自动扫描所有代码，结合记忆系统评分"""
    if base_dir is None:
        base_dir = BASE_DIR
    scan_dirs = [base_dir / "api", base_dir / "api" / "agents", base_dir / "api" / "routes", base_dir / "core"]
    results = []
    total_issues = 0
    for sd in scan_dirs:
        if not sd.exists(): continue
        for f in sorted(sd.glob("*.py")):
            r = analyze_code(str(f))
            if r.get("issue_count", 0) > 0:
                total_issues += r["issue_count"]
                results.append(r)
    # 记忆回馈：从 memos 获取历史经验
    memos_exp = ""
    try:
        from api.agents.agent_memos import get_memory
        m = get_memory()
        if m:
            exp = m.search_long("代码质量改进", top_k=3)
            if exp:
                memos_exp = " | ".join(f"{e['pattern']}:{e['solution'][:60]}" for e in exp)
    except Exception as _e:
        logger.warning(f"error: {_e}")
    return {"scanned": len([p for sd in scan_dirs if sd.exists() for p in sd.glob("*.py")]),
            "files_with_issues": len(results), "total_issues": total_issues,
            "details": results[:20], "timestamp": datetime.now().isoformat(),
            "memory_hints": memos_exp}


# ════════════════════════════════════════════════════════════
# Phase 2: 自进化代码改写 — LLM 生成补丁 → 备份 → apply → 测试 → 回滚
# ════════════════════════════════════════════════════════════
BACKUP_DIR = BASE_DIR / ".evo_backups"
BACKUP_DIR.mkdir(exist_ok=True)


def _auto_fix_code(file_path: str, issue: dict) -> dict:
    """用LLM修复单个代码问题：备份→修复→验证→回滚"""
    fp = Path(file_path)
    if not fp.exists():
        return {"status": "error", "error": "文件不存在"}
    
    # 备份
    backup_name = f"{fp.stem}_{int(time.time())}.bak"
    backup_path = BACKUP_DIR / backup_name
    try:
        shutil.copy2(str(fp), str(backup_path))
    except Exception as e:
        return {"status": "error", "error": f"备份失败: {e}"}
    
    # 读取代码
    try:
        code = fp.read_text(encoding='utf-8')
    except Exception as e:
        return {"status": "error", "error": f"读取失败: {e}"}
    
    # 用 LLM 生成修复
    fix_prompt = (
        f"修复以下Python代码的{issue['type']}问题（第{issue['line']}行）：{issue['msg']}\n\n"
        f"文件: {fp.name}\n代码:\n```python\n{code}\n```\n"
        f"只输出修复后的完整代码，不要解释。"
    )
    fixed_code = None
    try:
        from api.agent_llm import call_llm
        content, _ = call_llm([{"role": "user", "content": fix_prompt}], timeout=30)
        if content:
            # 提取代码块
            m = re.search(r'```(?:python)?\s*(.*?)\s*```', content, re.DOTALL)
            if m:
                fixed_code = m.group(1)
            elif len(content) > 50:
                fixed_code = content
    except Exception as _e:
        logger.warning(f"error: {_e}")
    
    if not fixed_code or len(fixed_code) < 10:
        return {"status": "failed", "error": "LLM未生成有效修复", "backup": str(backup_path)}
    
    # 写入修复
    try:
        fp.write_text(fixed_code, encoding='utf-8')
    except Exception as e:
        shutil.copy2(str(backup_path), str(fp))  # 回滚
        return {"status": "rollback", "error": f"写入失败已回滚: {e}", "backup": str(backup_path)}
    
    # 验证：编译检查
    compile_ok = False
    if fp.suffix == '.py':
        try:
            compile(fixed_code, str(fp), 'exec')
            compile_ok = True
        except SyntaxError as e:
            compile_ok = False
    
    if compile_ok:
        db = _get_db()
        db.execute("INSERT INTO autofixes (timestamp, file_path, backup_path, fix_type, status, result) VALUES (?,?,?,?,?,?)",
                   (time.time(), str(fp), str(backup_path), issue['type'], "completed", "编译通过"))
        db.commit()
        return {"status": "completed", "backup": str(backup_path), "type": issue['type']}
    else:
        # 回滚
        shutil.copy2(str(backup_path), str(fp))
        return {"status": "rollback", "error": "编译失败已回滚", "backup": str(backup_path)}


def auto_fix_all(base_dir: Path = None) -> dict:
    """自动修复所有可修复的问题"""
    scan = auto_scan(base_dir)
    fixes = []
    for detail in scan.get("details", []):
        for issue in detail.get("issues", []):
            if issue.get("type") in ("bare_except", "debug_print"):
                result = _auto_fix_code(detail["file"], issue)
                fixes.append({"file": detail["file"], "issue": issue["type"], "result": result})
                _log_evolution(detail["file"], f"修复{issue['type']}", result.get("error", ""),
                               status=result["status"], phase="autofix")
    return {"scanned": scan["scanned"], "total_fixes": len(fixes),
            "success": sum(1 for f in fixes if f["result"].get("status") == "completed"),
            "failed": sum(1 for f in fixes if f["result"].get("status") in ("failed", "rollback")),
            "fixes": fixes}


# ════════════════════════════════════════════════════════════
# Phase 3: 技能自动发现
# ════════════════════════════════════════════════════════════
def auto_discover_skills(base_dir: Path = None) -> dict:
    """自动扫描 modules/ 新 .py 文件注册为技能"""
    if base_dir is None:
        base_dir = BASE_DIR
    modules_dir = base_dir / "modules"
    if not modules_dir.exists():
        return {"status": "error", "error": "modules目录不存在"}
    
    discovered = []
    try:
        from api.routes.routes_skills import register_skill
    except ImportError:
        register_skill = None
    
    for f in sorted(modules_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        name = f.stem
        # 检查是否已有对应 skill
        skill_path = base_dir / "skills" / "builtin" / f"{name}.py"
        if skill_path.exists():
            continue  # 已注册
        discovered.append(name)
        # 创建简单的 skill 桩
        try:
            skill_content = f'"""自动发现的技能: {name}"""\nfrom modules.{name} import *\n'
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_content, encoding='utf-8')
        except Exception as _e:
            logger.warning(f"error: {_e}")
    
    if discovered:
        _log_evolution("skill_discovery", f"发现{len(discovered)}个新技能", str(discovered[:10]),
                       status="completed", phase="skill_discovery")
    return {"status": "completed", "discovered": len(discovered), "skills": discovered[:20]}


# ════════════════════════════════════════════════════════════
# Phase 4: 全栈进化闭环入口
# ════════════════════════════════════════════════════════════
def auto_evolve(base_dir=None, memos=None) -> dict:
    """全栈自进化入口：扫描→修复→发现→记录"""
    try:
        results = {}
        
        # Step 1: 扫描
        scan = auto_scan(base_dir)
        analysis = f"扫描{scan['scanned']}个文件，发现{scan['total_issues']}个问题"
        _log_evolution("auto_scan", analysis, "扫码完成", status="completed" if scan['total_issues']==0 else "pending", phase="scan")
        results["scan"] = {"files": scan["scanned"], "issues": scan["total_issues"]}
        
        # 记录到 memos
        if memos:
            try: memos.save_experience("自进化扫描", analysis[:200])
            except: pass
        
        # Step 2: 自动修复（只在有问题时）
        if scan["total_issues"] > 0:
            fix_result = auto_fix_all(base_dir)
            results["fix"] = {"total": fix_result["total_fixes"], "ok": fix_result["success"]}
            # 记忆回馈
            if memos and fix_result["success"] > 0:
                try: memos.save_experience("自动修复", f"成功修复{fix_result['success']}个问题")
                except: pass
        
        # Step 3: 技能发现
        skill_result = auto_discover_skills(base_dir)
        results["skills"] = {"new": skill_result["discovered"]}
        
        # Step 4: 自适应引擎评分更新
        if _ADAPTIVE:
            try:
                _ADAPTIVE.record(module="yoyo_evolve", action="full_cycle",
                                 success=True, latency_ms=0,
                                 context={"scan": scan["total_issues"], "fix": results.get("fix", {})})
            except Exception as _e:
                logger.warning(f"error: {_e}")
        
        return {"status": "completed", "results": results,
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


def get_evolution_history(limit: int = 20) -> list:
    """获取自进化历史"""
    db = _get_db()
    rows = db.execute("SELECT * FROM evolutions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r[0], "time": datetime.fromtimestamp(r[1]).isoformat(),
             "target": r[2], "analysis": r[3][:100], "suggestion": r[4][:100],
             "status": r[5], "score": r[7], "phase": r[8] if len(r) > 8 else ""} for r in rows]


def get_autofix_history(limit: int = 20) -> list:
    """获取自动修复历史"""
    db = _get_db()
    rows = db.execute("SELECT * FROM autofixes ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r[0], "time": datetime.fromtimestamp(r[1]).isoformat(),
             "file": r[2], "backup": r[3], "type": r[4], "status": r[5]} for r in rows]


# ════════════════════════════════════════════════════════════
# 后台循环
# ════════════════════════════════════════════════════════════
_thread_started = False


def start_background_evolve():
    global _thread_started
    if _thread_started: return
    _thread_started = True
    
    def _loop():
        import time as _t
        _t.sleep(30)
        while True:
            try:
                auto_evolve()
            except Exception as _e:
                logger.warning(f"error: {_e}")
            _t.sleep(3600)
    
    threading.Thread(target=_loop, daemon=True).start()


def get_status() -> dict:
    """获取系统状态"""
    db = _get_db()
    count = db.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0]
    fix_count = db.execute("SELECT COUNT(*) FROM autofixes").fetchone()[0]
    last = db.execute("SELECT timestamp, status FROM evolutions ORDER BY timestamp DESC LIMIT 1").fetchone()
    backups = len(list(BACKUP_DIR.glob("*.bak")))
    return {"status": "running" if _thread_started else "idle",
            "total_evolutions": count, "total_autofixes": fix_count,
            "backups_available": backups,
            "last_run": datetime.fromtimestamp(last[0]).isoformat() if last else None,
            "last_status": last[1] if last else None,
            "adaptive_engine": _ADAPTIVE is not None,
            "db_path": str(EVO_DB_PATH)}


start_background_evolve()
