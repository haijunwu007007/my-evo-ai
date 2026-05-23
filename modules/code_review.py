"""
AUTO-EVO-AI v7.0 — 代码审查引擎
Grade: A (生产级) | Category: 工具链
职责：自动化代码审查、质量评分、安全扫描、最佳实践检测、变更分析
"""

__module_meta__ = {
    "id": "code-review",
    "name": "Code Review",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["code", "developer", "adapter"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 — 代码审查引擎 Grade: A (生产级) | Category: 工具链",
}

import asyncio
import time
import uuid
import re
import os
import ast
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("code_review")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class RuleCategory(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    BUG_RISK = "bug_risk"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"

@dataclass
class ReviewRule:
    """审查规则"""

    rule_id: str
    name: str
    category: RuleCategory
    severity: Severity
    description: str
    pattern: str = ""
    check_fn: Optional[str] = None
    auto_fix: bool = False

@dataclass
class ReviewIssue:
    """审查问题"""

    issue_id: str
    rule_id: str
    file_path: str
    line_number: int
    severity: Severity
    category: RuleCategory
    message: str
    code_snippet: str = ""
    suggestion: str = ""
    auto_fixable: bool = False

@dataclass
class ReviewResult:
    """审查结果"""

    review_id: str
    file_path: str
    language: str
    total_lines: int = 0
    issues: List[ReviewIssue] = field(default_factory=list)
    score: float = 100.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    reviewed_at: float = field(default_factory=time.time)

@dataclass
class CodeMetrics:
    """代码度量"""

    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    complexity: int = 0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    avg_function_length: float = 0.0
    max_function_length: int = 0
    duplication_ratio: float = 0.0

class ReviewPatternAnalyzer(object):
    """代码审查模式分析器 — 识别重复代码、复杂度热点、风格偏差"""

    def __init__(self):
        self._complexity_cache: Dict[str, int] = {}

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """分析代码复杂度：圈复杂度、嵌套深度、函数长度"""
        lines = code.split("\n")
        functions = self._extract_functions(lines)
        results = []
        for func_name, start, end in functions:
            func_lines = lines[start:end]
            body = "\n".join(func_lines)
            complexity = self._cyclomatic_complexity(body)
            max_nest = self._max_nesting_depth(func_lines)
            length = end - start
            grade = "A" if complexity <= 5 and max_nest <= 3 else "B" if complexity <= 10 and max_nest <= 4 else "C"
            results.append(
                {
                    "function": func_name,
                    "lines": length,
                    "complexity": complexity,
                    "max_nesting": max_nest,
                    "grade": grade,
                }
            )
        results.sort(key=lambda x: x["complexity"], reverse=True)
        return {
            "total_functions": len(results),
            "average_complexity": round(sum(r["complexity"] for r in results) / max(len(results), 1), 1),
            "hotspots": [r for r in results if r["grade"] == "C"],
            "functions": results,
        }

    def detect_code_smells(self, code: str) -> List[Dict[str, Any]]:
        """检测代码异味：过长函数、过深嵌套、魔法数字、重复代码"""
        smells = []
        lines = code.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 120:
                smells.append({"type": "long_line", "line": i + 1, "length": len(stripped), "severity": "warning"})
            magic = re.findall(r"\b\d{2,}\b", stripped)
            for num in magic:
                if num not in ("0", "1", "10", "100", "1000", "3600", "86400"):
                    smells.append({"type": "magic_number", "line": i + 1, "value": num, "severity": "info"})
                    break
        func_pairs = self._extract_functions(lines)
        for i in range(len(func_pairs)):
            for j in range(i + 1, len(func_pairs)):
                body_i = "\n".join(lines[func_pairs[i][1] : func_pairs[i][2]])
                body_j = "\n".join(lines[func_pairs[j][1] : func_pairs[j][2]])
                similarity = self._quick_similarity(body_i, body_j)
                if similarity > 0.7:
                    smells.append(
                        {
                            "type": "duplicate_code",
                            "functions": [func_pairs[i][0], func_pairs[j][0]],
                            "similarity": round(similarity, 3),
                            "severity": "warning",
                        }
                    )
        return smells

    def _extract_functions(self, lines):
        functions = []
        for i, line in enumerate(lines):
            if re.match(r"^\s*(async\s+)?def\s+(\w+)", line):
                name = re.match(r"^\s*(async\s+)?def\s+(\w+)", line).group(2)
                if name.startswith("_"):
                    continue
                end = i + 1
                while end < len(lines) and lines[end].strip() and not re.match(r"^\s*(async\s+)?def\s+", lines[end]):
                    end += 1
                functions.append((name, i, end))
        return functions

    def _cyclomatic_complexity(self, code: str) -> int:
        branches = len(re.findall(r"\bif\b|\belif\b|\bfor\b|\bwhile\b|\band\b|\bor\b|\bexcept\b", code))
        return branches + 1

    def _max_nesting_depth(self, lines):
        max_depth = 0
        current = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("if ", "elif ", "else:", "for ", "while ", "try:", "with ", "except ")):
                current += 1
                max_depth = max(max_depth, current)
            elif stripped and not stripped.startswith("#"):
                indent = len(line) - len(line.lstrip())
                spaces = indent // 4
                current = min(current, spaces)
        return max_depth

    def _quick_similarity(self, a: str, b: str) -> float:
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a and not set_b:
            return 1.0
        return len(set_a & set_b) / len(set_a | set_b)

class CodeReview(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """代码审查引擎"""

    def __init__(self):

        super().__init__(
            config={
                "module_id": "code_review",
                "version": "7.0.0",
                "description": "代码审查引擎，支持安全扫描/质量评分/最佳实践检测",
            }
        )
        self.module_name = "code_review"
        self.module_id = self.module_name
        self._rules: List[ReviewRule] = []
        self._results: List[ReviewResult] = []
        self._max_file_size = 500000
        self._supported_languages = {"python": ".py", "javascript": ".js", "typescript": ".ts"}

    def initialize(self) -> None:
        self._register_rules()
        logger.info(f"代码审查引擎初始化完成，{len(self._rules)} 条规则")

    def _register_rules(self) -> None:
        """注册审查规则"""
        self._rules = [
            # 安全规则
            ReviewRule(
                "sec_001",
                "硬编码密码",
                RuleCategory.SECURITY,
                Severity.CRITICAL,
                "检测硬编码密码、密钥或token",
                pattern=r"(password|passwd|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
            ),
            ReviewRule(
                "sec_002",
                "SQL注入风险",
                RuleCategory.SECURITY,
                Severity.CRITICAL,
                "检测字符串拼接SQL",
                pattern=r"(execute|cursor\.execute)\s*\(\s*['\"].*\+.*['\"]",
            ),
            ReviewRule(
                "sec_003",
                "eval使用",
                RuleCategory.SECURITY,
                Severity.ERROR,
                "检测eval/exec的使用",
                pattern=r"\b(eval|exec)\s*\(",
            ),
            ReviewRule(
                "sec_004",
                "pickle反序列化",
                RuleCategory.SECURITY,
                Severity.ERROR,
                "检测不安全的pickle使用",
                pattern=r"pickle\.loads?\s*\(",
            ),
            ReviewRule(
                "sec_005",
                "调试代码",
                RuleCategory.SECURITY,
                Severity.WARNING,
                "检测调试代码残留",
                pattern=r"(pdb\.set_trace|breakpoint\(\)|import pdb|print\(.{0,50}(password|token|secret))",
            ),
            ReviewRule(
                "sec_006",
                "弱加密",
                RuleCategory.SECURITY,
                Severity.ERROR,
                "检测弱加密算法",
                pattern=r"\b(md5|sha1)\s*\(",
            ),
            # 性能规则
            ReviewRule(
                "perf_001",
                "循环内数据库查询",
                RuleCategory.PERFORMANCE,
                Severity.WARNING,
                "检测循环内数据库操作",
                pattern=r"(for|while).{0,200}(execute|query|fetch|cursor)",
            ),
            ReviewRule(
                "perf_002",
                "全局变量",
                RuleCategory.PERFORMANCE,
                Severity.INFO,
                "检测过多全局变量",
                check_fn="check_globals",
            ),
            ReviewRule(
                "perf_003",
                "大列表推导",
                RuleCategory.PERFORMANCE,
                Severity.INFO,
                "检测可能消耗大量内存的列表推导",
                pattern=r"\[\s*\w+\s+for\s+\w+\s+in\s+range\(\d{5,}\)",
            ),
            ReviewRule(
                "perf_004",
                "未使用生成器",
                RuleCategory.PERFORMANCE,
                Severity.INFO,
                "检测可改为生成器的场景",
                check_fn="check_generator",
            ),
            # 最佳实践
            ReviewRule(
                "bp_001",
                "缺少类型注解",
                RuleCategory.BEST_PRACTICE,
                Severity.INFO,
                "函数缺少类型注解",
                check_fn="check_type_hints",
            ),
            ReviewRule(
                "bp_002",
                "缺少docstring",
                RuleCategory.BEST_PRACTICE,
                Severity.INFO,
                "类/函数缺少docstring",
                check_fn="check_docstrings",
            ),
            ReviewRule(
                "bp_003",
                "过于宽泛的except",
                RuleCategory.BEST_PRACTICE,
                Severity.WARNING,
                "使用裸except或过于宽泛的异常捕获",
                pattern=r"except\s*:\s*$|except\s+Exception\s*:\s*$",
            ),
            ReviewRule(
                "bp_004",
                "魔法数字",
                RuleCategory.BEST_PRACTICE,
                Severity.INFO,
                "使用魔法数字",
                check_fn="check_magic_numbers",
            ),
            ReviewRule(
                "bp_005",
                "过长函数",
                RuleCategory.MAINTAINABILITY,
                Severity.WARNING,
                "函数超过50行",
                check_fn="check_function_length",
            ),
            ReviewRule(
                "bp_006",
                "过长参数列表",
                RuleCategory.MAINTAINABILITY,
                Severity.WARNING,
                "函数参数超过5个",
                check_fn="check_param_count",
            ),
            # 风格规则
            ReviewRule(
                "style_001",
                "行过长",
                RuleCategory.STYLE,
                Severity.WARNING,
                "行超过120字符",
                check_fn="check_line_length",
            ),
            ReviewRule(
                "style_002",
                "尾随空格",
                RuleCategory.STYLE,
                Severity.INFO,
                "行尾有多余空格",
                check_fn="check_trailing_whitespace",
            ),
            ReviewRule(
                "style_003",
                "缺少模块文档",
                RuleCategory.DOCUMENTATION,
                Severity.INFO,
                "模块缺少顶部文档字符串",
                check_fn="check_module_docstring",
            ),
            # Bug风险
            ReviewRule(
                "bug_001",
                "可变默认参数",
                RuleCategory.BUG_RISK,
                Severity.ERROR,
                "使用可变对象作为默认参数",
                pattern=r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\[.*\]|\{.*\})",
            ),
            ReviewRule(
                "bug_002",
                "比较None",
                RuleCategory.BUG_RISK,
                Severity.WARNING,
                "使用 == 比较 None",
                pattern=r"[!=]=\s*None\s*$|[!=]=\s+None[^a-zA-Z]",
            ),
            ReviewRule(
                "bug_003",
                "未关闭资源",
                RuleCategory.BUG_RISK,
                Severity.WARNING,
                "文件操作未使用with语句",
                pattern=r"open\s*\([^)]+\)\s*(?!.*as\s)",
            ),
        ]

    def review_code(self, file_path: str, content: Optional[str] = None, language: str = "") -> Dict[str, Any]:
        """审查代码文件"""
        start = time.time()

        if content is None:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        ext = os.path.splitext(file_path)[1].lower()
        language = self._detect_language(ext)

        review = ReviewResult(
            review_id=f"rev_{uuid.uuid4().hex[:8]}",
            file_path=file_path,
            language=language,
            total_lines=len(content.split("\n")),
        )

        # 计算代码度量
        review.metrics = self._compute_metrics(content, language)

        # 应用规则检查
        lines = content.split("\n")
        for rule in self._rules:
            if rule.pattern:
                issues = self._check_pattern_rule(rule, lines, file_path)
                review.issues.extend(issues)

        # 结构化检查（Python）
        if language == "python":
            structural_issues = self._check_python_structure(content, file_path)
            review.issues.extend(structural_issues)

        # 计算评分
        review.score = self._calculate_score(review.issues, review.total_lines)
        review.duration_ms = (time.time() - start) * 1000

        self._results.append(review)
        if not hasattr(self, "_files_reviewed"):
            self._files_reviewed = 0
        self._files_reviewed += 1

        severity_counts = defaultdict(int)
        for issue in review.issues:
            severity_counts[issue.severity.value] += 1

        return {
            "review_id": review.review_id,
            "file_path": file_path,
            "language": language,
            "score": round(review.score, 1),
            "total_lines": review.total_lines,
            "issues_total": len(review.issues),
            "issues_by_severity": dict(severity_counts),
            "metrics": review.metrics,
            "top_issues": [
                {
                    "line": i.line_number,
                    "severity": i.severity.value,
                    "category": i.category.value,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in sorted(review.issues, key=lambda x: x.severity.value, reverse=True)[:10]
            ],
            "duration_ms": round(review.duration_ms, 2),
        }

    def _detect_language(self, ext: str) -> str:
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
        }
        return lang_map.get(ext, "unknown")

    def _compute_metrics(self, content: str, language: str) -> Dict[str, Any]:
        """计算代码度量"""
        lines = content.split("\n")
        total = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        in_multiline_string = False
        in_comment = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#") or stripped.startswith("//"):
                comment_lines += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
            elif in_multiline_string:
                comment_lines += 1
            else:
                code_lines += 1

        metrics = {
            "total_lines": total,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "comment_ratio": round(comment_lines / max(total, 1), 4),
            "code_ratio": round(code_lines / max(total, 1), 4),
        }

        if language == "python":
            try:
                tree = ast.parse(content)
                functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

                func_lengths = []
                for func in functions:
                    if hasattr(func, "end_lineno") and hasattr(func, "lineno"):
                        func_lengths.append(func.end_lineno - func.lineno)

                metrics.update(
                    {
                        "functions": len(functions),
                        "classes": len(classes),
                        "imports": len(imports),
                        "avg_function_length": round(sum(func_lengths) / max(len(func_lengths), 1), 1),
                        "max_function_length": max(func_lengths) if func_lengths else 0,
                        "complexity": self._estimate_complexity(functions),
                    }
                )
            except SyntaxError:
                pass

        return metrics

    def _estimate_complexity(self, functions) -> int:
        """估算圈复杂度"""
        complexity = 0
        for func in functions:
            for node in ast.walk(func):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
        return complexity

    def _check_pattern_rule(self, rule: ReviewRule, lines: List[str], file_path: str) -> List[ReviewIssue]:
        """基于正则的规则检查"""
        issues = []
        try:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
        except re.error:
            return issues

        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                issues.append(
                    ReviewIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        rule_id=rule.rule_id,
                        file_path=file_path,
                        line_number=i,
                        severity=rule.severity,
                        category=rule.category,
                        message=rule.description,
                        code_snippet=line.strip()[:200],
                        suggestion=self._get_suggestion(rule.rule_id),
                        auto_fixable=rule.auto_fix,
                    )
                )
        return issues

    def _check_python_structure(self, content: str, file_path: str) -> List[ReviewIssue]:
        """Python结构化检查"""
        issues = []
        try:
            tree = ast.parse(content)
            lines = content.split("\n")

            # 检查类型注解
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # 检查返回类型注解
                    if node.returns is None and not node.name.startswith("_"):
                        issues.append(
                            ReviewIssue(
                                issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                rule_id="bp_001",
                                file_path=file_path,
                                line_number=node.lineno,
                                severity=Severity.INFO,
                                category=RuleCategory.BEST_PRACTICE,
                                message=f"函数 '{node.name}' 缺少返回类型注解",
                                code_snippet=f"def {node.name}({self._get_params_preview(node)})",
                                suggestion="添加返回类型注解，例如 -> None 或 -> Dict[str, Any]",
                            )
                        )

                    # 检查docstring
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        issues.append(
                            ReviewIssue(
                                issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                rule_id="bp_002",
                                file_path=file_path,
                                line_number=node.lineno,
                                severity=Severity.INFO,
                                category=RuleCategory.DOCUMENTATION,
                                message=f"函数 '{node.name}' 缺少docstring",
                                suggestion="添加三引号文档字符串描述函数用途",
                            )
                        )

                    # 检查函数长度
                    if hasattr(node, "end_lineno"):
                        length = node.end_lineno - node.lineno
                        if length > 50:
                            issues.append(
                                ReviewIssue(
                                    issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                    rule_id="bp_005",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    severity=Severity.WARNING,
                                    category=RuleCategory.MAINTAINABILITY,
                                    message=f"函数 '{node.name}' 过长 ({length} 行, 建议 < 50)",
                                    suggestion="考虑拆分为更小的函数",
                                )
                            )

                        # 检查参数数量
                        args = list(node.args.args) + list(node.args.kwonlyargs)
                        if node.args.vararg:
                            args.append(node.args.vararg)
                        if node.args.kwarg:
                            args.append(node.args.kwarg)
                        if len(args) > 5:
                            issues.append(
                                ReviewIssue(
                                    issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                    rule_id="bp_006",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    severity=Severity.WARNING,
                                    category=RuleCategory.MAINTAINABILITY,
                                    message=f"函数 '{node.name}' 参数过多 ({len(args)} 个, 建议 <= 5)",
                                    suggestion="考虑使用dataclass或配置字典封装参数",
                                )
                            )

                # 检查类docstring
                elif isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        issues.append(
                            ReviewIssue(
                                issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                rule_id="bp_002",
                                file_path=file_path,
                                line_number=node.lineno,
                                severity=Severity.INFO,
                                category=RuleCategory.DOCUMENTATION,
                                message=f"类 '{node.name}' 缺少docstring",
                            )
                        )

        except SyntaxError:
            pass

        # 行长度检查
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(
                    ReviewIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        rule_id="style_001",
                        file_path=file_path,
                        line_number=i,
                        severity=Severity.WARNING,
                        category=RuleCategory.STYLE,
                        message=f"行过长 ({len(line)} 字符, 建议 <= 120)",
                    )
                )
            if line != line.rstrip() and line.strip():
                issues.append(
                    ReviewIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        rule_id="style_002",
                        file_path=file_path,
                        line_number=i,
                        severity=Severity.INFO,
                        category=RuleCategory.STYLE,
                        message="行尾有多余空格",
                        auto_fixable=True,
                    )
                )

        # 模块docstring
        if lines and not lines[0].strip().startswith(('"""', "'''", "#")):
            issues.append(
                ReviewIssue(
                    issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                    rule_id="style_003",
                    file_path=file_path,
                    line_number=1,
                    severity=Severity.INFO,
                    category=RuleCategory.DOCUMENTATION,
                    message="模块缺少顶部文档字符串",
                )
            )

        return issues

    def _get_params_preview(self, node) -> str:
        """获取函数参数预览"""
        params = [a.arg for a in node.args.args[:3]]
        suffix = ", ..." if len(node.args.args) > 3 else ""
        return ", ".join(params) + suffix

    def _get_suggestion(self, rule_id: str) -> str:
        suggestions = {
            "sec_001": "使用环境变量或配置管理器存储敏感信息",
            "sec_002": "使用参数化查询替代字符串拼接",
            "sec_003": "避免使用eval/exec，考虑使用ast.literal_eval或JSON",
            "sec_004": "使用更安全的序列化方式如json",
            "sec_005": "移除调试代码后提交",
            "sec_006": "使用sha256或更强的哈希算法",
            "bp_003": "捕获具体异常类型，如 ValueError, KeyError",
            "bug_001": "使用None代替可变默认参数，在函数体内初始化",
            "bug_002": "使用 is None / is not None 比较None",
            "bug_003": "使用with语句自动管理资源",
        }
        return suggestions.get(rule_id, "")

    def _calculate_score(self, issues: List[ReviewIssue], total_lines: int) -> float:
        """计算审查评分"""
        if not issues:
            return 100.0

        deductions = {
            Severity.CRITICAL: 10,
            Severity.ERROR: 5,
            Severity.WARNING: 2,
            Severity.INFO: 0.5,
        }
        total_deduction = sum(deductions.get(i.severity, 0) for i in issues)
        score = max(0, 100 - total_deduction)
        return score

    def batch_review(self, file_paths: List[str]) -> Dict[str, Any]:
        """批量审查"""
        results = []
        for path in file_paths:
            try:
                result = self.review_code(path)
                results.append(result)
            except Exception as e:
                results.append({"file_path": path, "error": str(e)})

        total_issues = sum(r.get("issues_total", 0) for r in results)
        avg_score = sum(r.get("score", 0) for r in results) / max(len(results), 1)

        critical = sum(1 for r in results for i in r.get("top_issues", []) if i.get("severity") == "critical")

        return {
            "total_files": len(results),
            "total_issues": total_issues,
            "critical_issues": critical,
            "avg_score": round(avg_score, 1),
            "files_below_threshold": sum(1 for r in results if r.get("score", 0) < 70),
            "results": results,
        }

    def get_review_history(self, limit: int = 50) -> List[Dict]:
        return [
            {
                "review_id": r.review_id,
                "file_path": r.file_path,
                "score": round(r.score, 1),
                "issues": len(r.issues),
                "lines": r.total_lines,
                "reviewed_at": datetime.fromtimestamp(r.reviewed_at).isoformat(),
            }
            for r in reversed(self._results[-limit:])
        ]

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif base and not isinstance(base, dict):
            base = {}
        base = base or {}
        avg_score = 0
        if self._results:
            avg_score = sum(r.score for r in self._results) / len(self._results)
        result = dict(base)
        result.update(
            {
                "status": "ok",
                "files_reviewed": len(self._results),
                "rules_loaded": len(self._rules),
                "avg_score": round(avg_score, 1),
                "total_issues": sum(len(r.issues) for r in self._results),
            }
        )
        return result

    def shutdown(self) -> None:
        self._initialized = False
        logger.info(f"关闭代码审查引擎，共审查 {len(self._results)} 个文件")

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        _ = self.trace("execute")
        metrics_collector.counter("code_review_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        try:
            if action == "review":
                result = self.review_code(
                    file_path=params.get("file_path", ""),
                    content=params.get("content", ""),
                    language=params.get("language", ""),
                )
                return {"success": True, "result": result}
            elif action == "batch_review":
                result = self.batch_review(params.get("files", []))
                return {"success": True, "result": result}
            elif action == "history":
                results = self.get_review_history(limit=params.get("limit", 20))
                return {"success": True, "result": results}
            elif action == "list_rules":
                return {
                    "success": True,
                    "result": [
                        {
                            "rule_id": r.rule_id,
                            "name": r.name,
                            "category": r.category.value,
                            "severity": r.severity.value,
                        }
                        for r in self._rules
                    ],
                }
            elif action == "get_stats":
                hc = self.health_check()
                return {"success": True, "result": hc}
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[CodeReview] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

module_class = CodeReview
