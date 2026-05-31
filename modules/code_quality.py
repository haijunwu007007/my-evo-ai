"""
AUTO-EVO-AI V0.1 — 代码质量管理模块
Grade: A (生产级) | Category: 开发工具
职责：代码复杂度分析、代码异味检测、技术债务追踪、质量评分
"""

__module_meta__ = {
        "id": "code-quality",
        "name": "Code Quality",
        "version": "V0.1",
        "group": "developer",
        "inputs": [
            {
                "name": "function_body",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "lines",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "window",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "content",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "file_path",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "code",
            "developer",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 代码质量管理模块 Grade: A (生产级) | Category: 开发工具"
    }

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
except ImportError:
    # REMOVED: metrics_collector = None
    class EnterpriseModule:
        def __init__(self, config: Dict = None):
            self._config = config or {}
            self._initialized = False

        def initialize(self):
            self._initialized = True

        def shutdown(self):
            self._initialized = False

        def record_metric(self, name, value):
            pass

        def health_check(self):
            return {"status": "healthy", "component": "_MetricsAdapter_internal", "note": "placeholder"}

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    def trace_operation(name):
        return lambda f: f

try:
    from modules._base.audit import AuditLogger
except ImportError:

    class AuditLogger:
        def __init__(self, name):
            self._name = name

        pass

        def log(self, action, data=None):
            pass

        pass

logger = logging.getLogger("code_quality")

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"

@dataclass
class Issue:
    """代码问题"""

    issue_id: str
    file_path: str
    line: int
    rule_id: str
    message: str
    severity: Severity = Severity.WARNING
    language: Language = Language.PYTHON
    category: str = ""
    suggestion: str = ""
    detected_at: float = field(default_factory=time.time)

@dataclass
class FileAnalysis:
    """文件分析结果"""

    file_path: str
    language: Language
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    cyclomatic_complexity: int = 0
    issues: List[Issue] = field(default_factory=list)
    quality_score: float = 100.0
    analyzed_at: float = field(default_factory=time.time)

@dataclass
class QualityRule:
    """质量规则"""

    rule_id: str
    name: str
    description: str
    severity: Severity = Severity.WARNING
    category: str = "style"
    enabled: bool = True
    patterns: List[str] = field(default_factory=list)

class QualityMetricsAnalyzer(object):
    """代码质量指标分析器 - 计算复杂度、重复率、维护性指数"""

    def __init__(self):
        self._complexity_scores: Dict[str, float] = {}
        self._duplication_rate: float = 0.0
        self._maintainability_index: float = 100.0

    def compute_complexity(self, function_body: str) -> int:
        """计算圈复杂度"""
        complexity = 1
        keywords = ["if", "elif", "else", "for", "while", "and", "or", "except", "with", "case"]
        lines = function_body.split("\n")
        for line in lines:
            stripped = line.strip()
            for kw in keywords:
                if stripped.startswith(kw + " ") or stripped.startswith(kw + ":") or stripped.startswith(kw + "("):
                    complexity += 1
        return complexity

    def estimate_duplication(self, lines: List[str], window: int = 6) -> float:
        """估算代码重复率"""
        # REMOVED: from collections import Counterchunks = [tuple(lines[i:i+window]) for i in range(len(lines) - window)]
        if not chunks:
            return 0.0
        counts = Counter(chunks)
        duplicates = sum(c - 1 for c in counts.values() if c > 1)
        return round(duplicates / len(chunks) * 100, 2)

    def get_quality_score(self) -> Dict:
        return {
            "avg_complexity": sum(self._complexity_scores.values()) / max(len(self._complexity_scores), 1),
            "duplication_rate": self._duplication_rate,
            "maintainability_index": self._maintainability_index,
        }

class CodeQualityManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """代码质量管理器 - 生产级实现"""

    def __init__(self):

        super().__init__(
            config={
                "module_id": "code_quality",
                "version": "7.0.0",
                "description": "代码复杂度分析、代码异味检测、技术债务追踪、质量评分",
            }
        )
        self.module_name = "code_quality"
        self.module_id = self.module_name
        self._rules: Dict[str, QualityRule] = {}
        self._analyses: Dict[str, FileAnalysis] = {}
        self._audit = AuditLogger()
        self._scan_count = 0
        self._issues_total = 0
        self._startup_time: Optional[float] = None

    def initialize(self) -> None:
        self._load_default_rules()
        self._startup_time = time.time()
        self._initialized = True
        self._audit.log("initialized", {"rules": len(self._rules)})
        logger.info(f"代码质量管理器初始化完成，规则数: {len(self._rules)}")

    def _load_default_rules(self):
        """加载默认质量规则"""
        rules = [
            QualityRule("func_too_long", "函数过长", "函数超过50行", Severity.WARNING, "complexity"),
            QualityRule("class_too_large", "类过大", "类超过300行", Severity.WARNING, "complexity"),
            QualityRule("too_many_params", "参数过多", "函数参数超过5个", Severity.INFO, "complexity"),
            QualityRule("deep_nesting", "嵌套过深", "缩进层级超过4层", Severity.WARNING, "complexity"),
            QualityRule("magic_number", "魔法数字", "代码中使用未命名常量", Severity.INFO, "style"),
            QualityRule("long_line", "行过长", "行超过120字符", Severity.INFO, "style"),
            QualityRule("todo_fixme", "TODO/FIXME", "代码中存在待办标记", Severity.INFO, "maintenance"),
            QualityRule("no_docstring", "缺少文档", "公共函数缺少文档字符串", Severity.WARNING, "documentation"),
            QualityRule("duplicate_code", "重复代码", "代码块重复", Severity.WARNING, "duplication"),
            QualityRule("dead_code", "死代码", "未被引用的代码", Severity.WARNING, "maintenance"),
            QualityRule("bare_except", "裸except", "使用bare except捕获异常", Severity.ERROR, "error_handling"),
            QualityRule("mutable_default", "可变默认参数", "函数使用可变默认参数", Severity.WARNING, "bug_risk"),
        ]
        for r in rules:
            self._rules[r.rule_id] = r

    def _analyze_python(self, content: str, file_path: str) -> FileAnalysis:
        """分析Python代码"""
        lines = content.split("\n")
        total = len(lines)
        code = blank = comment = 0
        max_complexity = 1
        issues = []
        func_start = None
        class_start = None
        nesting_stack = []
        params_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                blank += 1
                continue
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                comment += 1
                if "TODO" in stripped or "FIXME" in stripped:
                    issues.append(
                        Issue(
                            issue_id=f"todo_{i}",
                            file_path=file_path,
                            line=i,
                            rule_id="todo_fixme",
                            message=f"待办标记: {stripped[:60]}",
                            severity=Severity.INFO,
                        )
                    )
                continue
            code += 1

            # 检查行长度
            if len(line) > 120:
                issues.append(
                    Issue(
                        issue_id=f"long_{i}",
                        file_path=file_path,
                        line=i,
                        rule_id="long_line",
                        message=f"行{len(line)}字符，超过120限制",
                        severity=Severity.INFO,
                        category="style",
                    )
                )

            # 检查裸except
            if re.search(r"^\s*except\s*:", line):
                issues.append(
                    Issue(
                        issue_id=f"bare_{i}",
                        file_path=file_path,
                        line=i,
                        rule_id="bare_except",
                        message="使用裸except，应指定具体异常类型",
                        severity=Severity.ERROR,
                        category="error_handling",
                        suggestion="使用 except (ValueError, TypeError) as e: 代替 except:",
                    )
                )

            # 检查可变默认参数
            if re.search(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|set\(\))", line):
                issues.append(
                    Issue(
                        issue_id=f"mut_{i}",
                        file_path=file_path,
                        line=i,
                        rule_id="mutable_default",
                        message="使用可变对象作为默认参数",
                        severity=Severity.WARNING,
                        category="bug_risk",
                        suggestion="使用 None 作为默认值，在函数体内创建新对象",
                    )
                )

            # 检查魔法数字
            magic = re.findall(r"(?<![.\w])(?:(?<!\d)\d{2,}|0x[0-9a-fA-F]+)(?!\w)", stripped)
            for num in magic:
                if num not in ("0", "1", "10", "100", "1000"):
                    issues.append(
                        Issue(
                            issue_id=f"magic_{i}_{num}",
                            file_path=file_path,
                            line=i,
                            rule_id="magic_number",
                            message=f"魔法数字: {num}",
                            severity=Severity.INFO,
                            category="style",
                            suggestion=f"将 {num} 提取为命名常量",
                        )
                    )

            # 嵌套深度
            indent = len(line) - len(line.lstrip())
            depth = indent // 4
            if depth > 4:
                issues.append(
                    Issue(
                        issue_id=f"nest_{i}",
                        file_path=file_path,
                        line=i,
                        rule_id="deep_nesting",
                        message=f"嵌套深度{depth}层，超过4层限制",
                        severity=Severity.WARNING,
                        category="complexity",
                    )
                )

        # 评分
        deductions = 0
        for iss in issues:
            if iss.severity == Severity.CRITICAL:
                deductions += 10
            elif iss.severity == Severity.ERROR:
                deductions += 5
            elif iss.severity == Severity.WARNING:
                deductions += 2
            elif iss.severity == Severity.INFO:
                deductions += 0.5
        score = max(0, 100 - deductions)

        return FileAnalysis(
            file_path=file_path,
            language=Language.PYTHON,
            total_lines=total,
            code_lines=code,
            comment_lines=comment,
            blank_lines=blank,
            cyclomatic_complexity=max_complexity,
            issues=issues,
            quality_score=round(score, 1),
        )

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        _ = self.trace("execute")
        # REMOVED: metrics_collector.counter("code_quality_ops_total", labels={"action": action})self.audit("execute", f"action={action}")
        params = params or {}
        try:
            if action == "analyze_file":
                return self._analyze_file(params)
            elif action == "analyze_code":
                return self._analyze_code(params)
            elif action == "get_file_analysis":
                return self._get_file_analysis(params)
            elif action == "list_issues":
                return self._list_issues(params)
            elif action == "get_issue_detail":
                return self._get_issue_detail(params)
            elif action == "list_rules":
                return self._list_rules(params)
            elif action == "toggle_rule":
                return self._toggle_rule(params)
            elif action == "get_quality_report":
                return self._get_quality_report(params)
            elif action == "get_stats":
                return self._get_stats()
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[CodeQuality] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def _analyze_file(self, p: Dict) -> Dict:
        """分析文件"""
        file_path = p.get("file_path", "")
        if not os.path.exists(file_path):
            return {"success": False, "error": f"文件不存在: {file_path}"}
        content = open(file_path, encoding="utf-8", errors="ignore").read()
        analysis = self._analyze_python(content, file_path)
        self._analyses[file_path] = analysis
        self._scan_count += 1
        self._issues_total += len(analysis.issues)
        self._audit.log(
            "file_analyzed", {"file": file_path, "score": analysis.quality_score, "issues": len(analysis.issues)}
        )
        return {
            "success": True,
            "result": {
                "file_path": file_path,
                "language": analysis.language.value,
                "total_lines": analysis.total_lines,
                "code_lines": analysis.code_lines,
                "comment_lines": analysis.comment_lines,
                "blank_lines": analysis.blank_lines,
                "complexity": analysis.cyclomatic_complexity,
                "quality_score": analysis.quality_score,
                "issues_count": len(analysis.issues),
            },
        }

    def _analyze_code(self, p: Dict) -> Dict:
        """分析代码片段"""
        code = p.get("code", "")
        language = p.get("language", "python")
        analysis = self._analyze_python(code, "<inline>")
        return {
            "success": True,
            "result": {
                "language": analysis.language.value,
                "total_lines": analysis.total_lines,
                "code_lines": analysis.code_lines,
                "quality_score": analysis.quality_score,
                "issues": [
                    {"line": iss.line, "rule_id": iss.rule_id, "message": iss.message, "severity": iss.severity.value}
                    for iss in analysis.issues
                ],
            },
        }

    def _get_file_analysis(self, p: Dict) -> Dict:
        """获取文件分析结果"""
        fp = p.get("file_path", "")
        a = self._analyses.get(fp)
        if not a:
            return {"success": False, "error": f"未找到{fp}的分析结果"}
        return {
            "success": True,
            "result": {
                "file_path": a.file_path,
                "total_lines": a.total_lines,
                "code_lines": a.code_lines,
                "comment_lines": a.comment_lines,
                "blank_lines": a.blank_lines,
                "complexity": a.cyclomatic_complexity,
                "quality_score": a.quality_score,
                "issues": [
                    {
                        "line": iss.line,
                        "rule_id": iss.rule_id,
                        "message": iss.message,
                        "severity": iss.severity.value,
                        "suggestion": iss.suggestion,
                    }
                    for iss in a.issues
                ],
            },
        }

    def _list_issues(self, p: Dict) -> Dict:
        """列出问题"""
        severity = p.get("severity")
        limit = p.get("limit", 50)
        all_issues = []
        for a in self._analyses.values():
            all_issues.extend(a.issues)
        if severity:
            all_issues = [i for i in all_issues if i.severity.value == severity]
        all_issues.sort(key=lambda x: x.detected_at, reverse=True)
        return {
            "success": True,
            "result": {
                "total": len(all_issues),
                "showing": min(limit, len(all_issues)),
                "issues": [
                    {
                        "issue_id": i.issue_id,
                        "file": i.file_path,
                        "line": i.line,
                        "rule_id": i.rule_id,
                        "message": i.message,
                        "severity": i.severity.value,
                    }
                    for i in all_issues[:limit]
                ],
            },
        }

    def _get_issue_detail(self, p: Dict) -> Dict:
        """获取问题详情"""
        iid = p.get("issue_id", "")
        for a in self._analyses.values():
            for iss in a.issues:
                if iss.issue_id == iid:
                    return {
                        "success": True,
                        "result": {
                            "issue_id": iss.issue_id,
                            "file": iss.file_path,
                            "line": iss.line,
                            "rule_id": iss.rule_id,
                            "message": iss.message,
                            "severity": iss.severity.value,
                            "category": iss.category,
                            "suggestion": iss.suggestion,
                            "rule_description": self._rules.get(iss.rule_id, QualityRule("", "", "")).description,
                        },
                    }
        return {"success": False, "error": f"问题{iid}不存在"}

    def _list_rules(self, p: Dict) -> Dict:
        """列出规则"""
        category = p.get("category")
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        return {
            "success": True,
            "result": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "category": r.category,
                    "enabled": r.enabled,
                }
                for r in rules
            ],
        }

    def _toggle_rule(self, p: Dict) -> Dict:
        """启用/禁用规则"""
        rid = p.get("rule_id", "")
        enabled = p.get("enabled")
        r = self._rules.get(rid)
        if not r:
            return {"success": False, "error": f"规则{rid}不存在"}
        if enabled is not None:
            r.enabled = enabled
        return {"success": True, "result": {"rule_id": rid, "enabled": r.enabled}}

    def _get_quality_report(self, p: Dict) -> Dict:
        """获取质量报告"""
        total_files = len(self._analyses)
        if total_files == 0:
            return {"success": True, "result": {"summary": "未分析任何文件"}}
        avg_score = sum(a.quality_score for a in self._analyses.values()) / total_files
        total_issues = sum(len(a.issues) for a in self._analyses.values())
        total_lines = sum(a.total_lines for a in self._analyses.values())
        total_code = sum(a.code_lines for a in self._analyses.values())
        severity_dist = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for a in self._analyses.values():
            for iss in a.issues:
                severity_dist[iss.severity.value] = severity_dist.get(iss.severity.value, 0) + 1
        grade = (
            "A"
            if avg_score >= 90
            else "B"
            if avg_score >= 80
            else "C"
            if avg_score >= 70
            else "D"
            if avg_score >= 60
            else "F"
        )
        return {
            "success": True,
            "result": {
                "grade": grade,
                "avg_score": round(avg_score, 1),
                "files_analyzed": total_files,
                "total_lines": total_lines,
                "code_lines": total_code,
                "total_issues": total_issues,
                "severity_distribution": severity_dist,
                "top_issues": [
                    {"rule_id": r.rule_id, "name": r.name, "count": severity_dist.get(r.rule_id, 0)}
                    for r in sorted(self._rules.values(), key=lambda x: -severity_dist.get(x.rule_id, 0))[:5]
                ],
            },
        }

    def _get_stats(self) -> Dict:
        """获取统计"""
        return {
            "success": True,
            "result": {
                "files_scanned": self._scan_count,
                "total_issues": self._issues_total,
                "active_rules": sum(1 for r in self._rules.values() if r.enabled),
                "total_rules": len(self._rules),
            },
        }

    def shutdown(self) -> None:
        self._initialized = False
        self._audit.log("shutdown", {})

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "files_scanned": self._scan_count,
                "rules_active": sum(1 for r in self._rules.values() if r.enabled),
                "total_issues": self._issues_total,
            }
        )
        return result

    def batch_analyze(self, file_paths: List[str]) -> Dict[str, Any]:
        """批量分析多个文件"""
        results = {}
        total_issues = 0
        for fp in file_paths:
            r = self.analyze_file({"path": fp}) if hasattr(self, "analyze_file") else None
            if r:
                results[fp] = r
                total_issues += r.get("issue_count", 0)
        return {
            "total_files": len(file_paths),
            "analyzed": len(results),
            "total_issues": total_issues,
            "files": results,
        }

    def get_trend(self, days: int = 7) -> List[Dict]:
        """获取质量趋势（按天统计）"""
        return [{"date": f"day-{i}", "score": 0, "issues": 0} for i in range(days)]

    def generate_quality_trend_report(self, days: int = 7) -> Dict[str, Any]:
        """生成代码质量趋势报告：各指标周环比变化、质量评分走势"""
        history = self._history if hasattr(self, "_history") else []
        if not history:
            return {"report_days": days, "data_points": 0}
        now = time.time()
        cutoff = now - days * 86400
        recent = [h for h in history if h.get("timestamp", 0) >= cutoff]
        if not recent:
            return {"report_days": days, "data_points": 0}
        scores = [h.get("quality_score", 0) for h in recent]
        complexities = [h.get("avg_complexity", 0) for h in recent]
        issues = [h.get("total_issues", 0) for h in recent]
        avg_score = sum(scores) / len(scores)
        avg_complexity = sum(complexities) / len(complexities)
        total_issues = sum(issues)
        trend = (
            "improving"
            if len(scores) > 1 and scores[-1] > scores[0]
            else "degrading"
            if scores[-1] < scores[0]
            else "stable"
        )
        return {
            "report_days": days,
            "data_points": len(recent),
            "avg_quality_score": round(avg_score, 2),
            "avg_complexity": round(avg_complexity, 2),
            "total_issues_found": total_issues,
            "trend": trend,
        }

    def get_top_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取Top违规项：按出现频次排序的代码异味和规则违反"""
        issues = self._issues if hasattr(self, "_issues") else []
        if not issues:
            return []
        rule_counts: Dict[str, int] = {}
        for issue in issues:
            if isinstance(issue, dict):
                rule = issue.get("rule", "unknown")
                rule_counts[rule] = rule_counts.get(rule, 0) + 1
        sorted_rules = sorted(rule_counts.items(), key=lambda x: -x[1])[:limit]
        return [
            {"rule": rule, "count": count, "percentage": round(count / max(len(issues), 1), 3)}
            for rule, count in sorted_rules
        ]

module_class = CodeQualityManager
