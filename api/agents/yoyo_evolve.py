"""YoYo-Evolve 自进化系统 — 持续自我优化：分析→建议→优化→验证→学习"""

import os, json, time, re, random, sqlite3, threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# 自进化数据库
_EVOLVE_DB: Optional[sqlite3.Connection] = None
_EVOLVE_LOCK = threading.Lock()
BASE_DIR = Path(__file__).parent.parent

def _get_db():
    global _EVOLVE_DB
    if _EVOLVE_DB is None:
        db_path = BASE_DIR / "core" / "yoyo_evolve.db"
        db_path.parent.mkdir(exist_ok=True)
        _EVOLVE_DB = sqlite3.connect(str(db_path), check_same_thread=False)
        _EVOLVE_DB.execute("""CREATE TABLE IF NOT EXISTS evolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, target TEXT, analysis TEXT,
            suggestion TEXT, status TEXT, result TEXT,
            score REAL
        )""")
        _EVOLVE_DB.commit()
    return _EVOLVE_DB

def _log_evolution(target, analysis, suggestion, status="pending", result="", score=0.0):
    db = _get_db()
    db.execute("INSERT INTO evolutions (timestamp, target, analysis, suggestion, status, result, score) VALUES (?,?,?,?,?,?,?)",
               (time.time(), target[:100], analysis[:500], suggestion[:500], status, result[:500], score))
    db.commit()

def analyze_code(file_path: str) -> dict:
    """分析单个代码文件，返回改进建议"""
    try:
        fp = Path(file_path)
        if not fp.exists() or fp.suffix not in ('.py', '.js', '.ts', '.html'):
            return {"file": file_path, "issues": [], "quality": "skip"}
        
        code = fp.read_text(encoding='utf-8')
        issues = []
        
        # 检查常见问题
        lines = code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'except:' in stripped and 'Exception' not in stripped and i > 0 and '#' not in lines[i-1]:
                issues.append({"line": i+1, "type": "bare_except", "msg": "裸except"})
            if 'print(' in stripped and i > 5:
                issues.append({"line": i+1, "type": "debug_print", "msg": "调试print残留"})
            if len(stripped) > 200:
                issues.append({"line": i+1, "type": "long_line", "msg": f"超长行({len(stripped)}字符)"})
        
        # 计算质量分
        score = 100.0 - len(issues) * 5
        score = max(score, 0)
        
        return {
            "file": file_path,
            "lines": len(lines),
            "size": fp.stat().st_size,
            "issues": issues,
            "issue_count": len(issues),
            "quality": "good" if score >= 80 else "needs_improvement" if score >= 50 else "poor",
            "score": round(score, 1)
        }
    except Exception as e:
        return {"file": file_path, "issues": [{"type": "error", "msg": str(e)[:100]}], "quality": "error"}

def auto_scan(base_dir: Path = None) -> dict:
    """自动扫描所有代码，生成进化建议"""
    if base_dir is None:
        base_dir = BASE_DIR
    
    scan_dirs = [
        base_dir / "api",
        base_dir / "api" / "agents",
        base_dir / "api" / "routes",
        base_dir / "core",
    ]
    
    results = []
    total_issues = 0
    
    for sd in scan_dirs:
        if not sd.exists(): continue
        for f in sorted(sd.glob("*.py")):
            r = analyze_code(str(f))
            if r.get("issue_count", 0) > 0:
                total_issues += r["issue_count"]
                results.append(r)
    
    return {
        "scanned": len([p for sd in scan_dirs if sd.exists() for p in sd.glob("*.py")]),
        "files_with_issues": len(results),
        "total_issues": total_issues,
        "details": results[:20],  # 只返回前20个
        "timestamp": datetime.now().isoformat()
    }

def auto_evolve(base_dir=None, memos=None) -> dict:
    """自进化总入口：扫描→分析→建议→记录"""
    try:
        scan = auto_scan(base_dir)
        if scan["total_issues"] == 0:
            return {"status": "clean", "message": "无需要优化的代码"}
        
        analysis = f"扫描{scan['scanned']}个文件，发现{scan['total_issues']}个问题，分布在{scan['files_with_issues']}个文件中"
        suggestion = f"建议修复{scan['total_issues']}个问题：bare_except改用精确异常、删除调试print、缩短超长行"
        
        _log_evolution("auto_scan", analysis, suggestion, "pending")
        
        if memos:
            try: memos.save_experience("自进化扫描", analysis[:100])
            except: pass
        
        return {
            "status": "pending",
            "analysis": analysis,
            "suggestion": suggestion,
            "details": scan["details"][:5]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}

def get_evolution_history(limit: int = 20) -> list:
    """获取自进化历史"""
    db = _get_db()
    rows = db.execute("SELECT * FROM evolutions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [{
        "id": r[0], "time": datetime.fromtimestamp(r[1]).isoformat(),
        "target": r[2], "analysis": r[3][:100],
        "suggestion": r[4][:100], "status": r[5]
    } for r in rows]

# 开机自动触发一次扫描
_thread_started = False

def start_background_evolve():
    global _thread_started
    if _thread_started: return
    _thread_started = True
    
    def _loop():
        import time as _t
        _t.sleep(30)  # 开机后30秒开始
        while True:
            try:
                auto_evolve()
            except: pass
            _t.sleep(3600)  # 每小时一次
    
    threading.Thread(target=_loop, daemon=True).start()

def get_status() -> dict:
    """获取自进化系统状态"""
    db = _get_db()
    count = db.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0]
    last = db.execute("SELECT timestamp, status FROM evolutions ORDER BY timestamp DESC LIMIT 1").fetchone()
    return {
        "status": "running" if _thread_started else "idle",
        "total_evolutions": count,
        "last_run": datetime.fromtimestamp(last[0]).isoformat() if last else None,
        "last_status": last[1] if last else None,
        "db_path": str(BASE_DIR / "core" / "yoyo_evolve.db")
    }

# 模块加载时自动启动
start_background_evolve()
