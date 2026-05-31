"""AUTO-EVO-AI V0.1 — 模块质量分析器（修正版）"""
import os, ast, logging
from core.logging_config import get_logger
from pathlib import Path
from typing import Dict, List

logger = get_logger("evo.module_quality")
MODULES_DIR = Path(__file__).parent.parent / "modules"
EXECUTE_LIKE = {'execute', 'run', 'process', 'handle', 'analyze', 'search', 'query',
                'get_status', 'generate', 'create', 'transform', 'validate', 'dispatch',
                'evolve', 'learn', 'optimize', 'sync', 'backup', 'restore', 'deploy'}


def analyze_module(filepath: Path) -> Dict:
    """分析单个模块文件的质量"""
    result = {
        "name": filepath.stem, "path": str(filepath.relative_to(MODULES_DIR.parent)),
        "size_bytes": filepath.stat().st_size, "lines": 0,
        "has_class": False, "has_execute": False, "has_module_meta": False,
        "has_actions": False, "class_count": 0, "method_count": 0, "import_count": 0,
        "real_method_count": 0, "grade": "D", "issues": [],
    }
    try:
        content = filepath.read_text(encoding="utf-8")
        result["lines"] = len(content.splitlines())
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result["has_class"] = True
                result["class_count"] += 1
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        result["method_count"] += 1
                        if item.name in EXECUTE_LIKE:
                            result["has_execute"] = True
                            result["real_method_count"] += 1
                        elif not item.name.startswith('_'):
                            result["real_method_count"] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                result["import_count"] += 1
        if "__module_meta__" in content:
            result["has_module_meta"] = True
        # Grade: has real class with methods = A or B
        if result["class_count"] > 0 and result["real_method_count"] >= 2:
            result["grade"] = "A"
        elif result["class_count"] > 0 and result["method_count"] > 0:
            result["grade"] = "B"
        elif result["lines"] > 10 or result["has_module_meta"]:
            result["grade"] = "C"
        else:
            result["grade"] = "D"
        if result["lines"] < 5:
            result["issues"].append("极短文件")
    except SyntaxError as e:
        result["issues"].append(f"语法错误: {e.msg}")
        result["grade"] = "D"
    except Exception as e:
        result["issues"].append(f"分析失败: {e}")
        result["grade"] = "D"
    return result


def scan_all() -> Dict:
    """扫描所有模块并返回分级统计"""
    if not MODULES_DIR.exists():
        return {"error": f"模块目录不存在: {MODULES_DIR}"}
    modules = []
    for f in sorted(MODULES_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        modules.append(analyze_module(f))
    grades = {"A": 0, "B": 0, "C": 0, "D": 0}
    for m in modules:
        grades[m["grade"]] += 1
    top_modules = [m["name"] for m in modules if m["grade"] == "A"][:30]
    c_modules = [m for m in modules if m["grade"] == "C"]
    d_modules = [m for m in modules if m["grade"] == "D"]
    return {
        "total": len(modules), "grades": grades,
        "production_ready": grades.get("A", 0) + grades.get("B", 0),
        "top_modules": top_modules,
        "c_modules": [{"name": m["name"], "lines": m["lines"], "grade": m["grade"],
                       "issues": m["issues"]} for m in c_modules],
        "d_modules": [{"name": m["name"], "lines": m["lines"], "grade": m["grade"],
                       "issues": m["issues"]} for m in d_modules],
    }
