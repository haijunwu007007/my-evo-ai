"""
        Atom Code - Intelligent Code Generation and Refactoring Engine
Provides code generation from specifications, automated refactoring, code review,
snippet management, and multi-language code analysis.
"""

__module_meta__ = {
    "id": "atom-code",
    "name": "Atom Code",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "snippet_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "language", "type": "string", "required": True, "description": ""},
        {"name": "code", "type": "string", "required": True, "description": ""},
        {"name": "snippet_id", "type": "string", "required": True, "description": ""},
        {"name": "query", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "manager", "atom"],
    "grade": "C",
    "description": "Atom Code - Intelligent Code Generation and Refactoring Engine Provides code generation from specifications, automated refactoring, code review,",
}

import time
import json
import uuid
import hashlib
import re
import difflib
import ast
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from enum import Enum, auto
from dataclasses import dataclass, field

from modules._base.enterprise_module import EnterpriseModule

class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    SQL = "sql"
    SHELL = "shell"
    YAML = "yaml"
    JSON = "json"

class RefactorType(Enum):
    EXTRACT_FUNCTION = auto()
    INLINE_VARIABLE = auto()
    RENAME_SYMBOL = auto()
    EXTRACT_CLASS = auto()
    SIMPLIFY_CONDITIONAL = auto()
    ADD_TYPE_HINTS = auto()
    REMOVE_DEAD_CODE = auto()
    OPTIMIZE_IMPORTS = auto()
    CONVERT_TO_FSTRING = auto()
    ADD_DOCSTRING = auto()

class ReviewSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class CodeSnippet:
    snippet_id: str
    name: str
    language: str
    code: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    usage_count: int = 0

@dataclass
class RefactorResult:
    original: str
    refactored: str
    refactor_type: str
    changes: List[Dict] = field(default_factory=list)
    score_improvement: float = 0.0

@dataclass
class ReviewIssue:
    line: int
    column: int
    severity: str
    rule: str
    message: str
    suggestion: str = ""

@dataclass
class CodeMetrics:
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    maintainability_index: float = 0.0
    comment_ratio: float = 0.0
    duplicate_blocks: int = 0
    functions_count: int = 0
    classes_count: int = 0
    imports_count: int = 0

class SnippetManager:
    """Manages reusable code snippets with search and tagging."""

    def __init__(self):
        self._snippets: Dict[str, CodeSnippet] = {}
        self._tag_index: Dict[str, List[str]] = defaultdict(list)

    def add(
        self,
        snippet_id: str,
        name: str,
        language: str,
        code: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict:
        snippet = CodeSnippet(
            snippet_id=snippet_id,
            name=name,
            language=language,
            code=code,
            description=description,
            tags=tags or [],
            created_at=time.time(),
        )
        self._snippets[snippet_id] = snippet
        for t in snippet.tags:
            if snippet_id not in self._tag_index[t]:
                self._tag_index[t].append(snippet_id)
        return {"snippet_id": snippet_id, "name": name, "tags": snippet.tags}

    def get(self, snippet_id: str) -> Optional[Dict]:
        s = self._snippets.get(snippet_id)
        if not s:
            return None
        return {
            "snippet_id": s.snippet_id,
            "name": s.name,
            "language": s.language,
            "code": s.code,
            "description": s.description,
            "tags": s.tags,
            "created_at": s.created_at,
            "usage_count": s.usage_count,
        }

    def search(self, query: str, language: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict]:
        results = []
        for s in self._snippets.values():
            if language and s.language != language:
                continue
            if tags and not any(t in s.tags for t in tags):
                continue
            score = 0
            if query.lower() in s.name.lower():
                score += 10
            if query.lower() in s.description.lower():
                score += 5
            if query.lower() in s.code.lower():
                score += 2
            if score > 0:
                results.append(
                    {
                        "snippet_id": s.snippet_id,
                        "name": s.name,
                        "language": s.language,
                        "score": score,
                        "tags": s.tags,
                        "code_preview": s.code[:200],
                    }
                )
        results.sort(key=lambda x: -x["score"])
        return results

    def list_all(self, language: Optional[str] = None) -> List[Dict]:
        snippets = list(self._snippets.values())
        if language:
            snippets = [s for s in snippets if s.language == language]
        return [self.get(s.snippet_id) for s in snippets]

    def update(self, snippet_id: str, updates: Dict) -> Dict:
        s = self._snippets.get(snippet_id)
        if not s:
            return {"error": "snippet_not_found"}
        for k, v in updates.items():
            if k == "name":
                s.name = v
            elif k == "code":
                s.code = v
            elif k == "description":
                s.description = v
            elif k == "tags":
                for old_t in s.tags:
                    if snippet_id in self._tag_index.get(old_t, []):
                        self._tag_index[old_t].remove(snippet_id)
                s.tags = v
                for t in v:
                    if snippet_id not in self._tag_index[t]:
                        self._tag_index[t].append(snippet_id)
        return {"updated": snippet_id}

    def delete(self, snippet_id: str) -> bool:
        s = self._snippets.pop(snippet_id, None)
        if s:
            for t in s.tags:
                if snippet_id in self._tag_index.get(t, []):
                    self._tag_index[t].remove(snippet_id)
            return True
        return False

    def stats(self) -> Dict:
        by_lang = defaultdict(int)
        for s in self._snippets.values():
            by_lang[s.language] += 1
        return {"total_snippets": len(self._snippets), "by_language": dict(by_lang), "total_tags": len(self._tag_index)}

class CodeAnalyzer:
    """Analyzes code quality, complexity, and structure."""

    def __init__(self):
        self._analysis_cache: Dict[str, CodeMetrics] = {}

    def analyze(self, code: str, language: str = "python") -> CodeMetrics:
        cache_key = hashlib.md5(code.encode()).hexdigest()
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        lines = code.split("\n")
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        comment_lines = [l for l in lines if l.strip().startswith("#")]
        metrics = CodeMetrics()
        metrics.lines_of_code = len(code_lines)
        metrics.comment_ratio = len(comment_lines) / max(1, len(lines))
        if language == "python":
            self._analyze_python(code, metrics)
        else:
            self._estimate_complexity(code, metrics)
        metrics.maintainability_index = max(
            0,
            min(
                100,
                171
                - 5.2 * metrics.cyclomatic_complexity
                - 0.23 * metrics.lines_of_code
                - 16.2 * (1 - metrics.comment_ratio),
            ),
        )
        self._analysis_cache[cache_key] = metrics
        return metrics

    def _analyze_python(self, code: str, metrics: CodeMetrics):
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics.functions_count += 1
                    metrics.cyclomatic_complexity += self._function_complexity(node)
                elif isinstance(node, ast.ClassDef):
                    metrics.classes_count += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics.imports_count += 1
        except SyntaxError:
            self._estimate_complexity(code, metrics)

    def _function_complexity(self, node) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert, ast.comprehension)
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _estimate_complexity(self, code: str, metrics: CodeMetrics):
        metrics.cyclomatic_complexity = code.count(" if ") + code.count(" for ") + 1
        metrics.functions_count = len(re.findall(r"def |function |func ", code))
        metrics.classes_count = len(re.findall(r"class |struct |interface ", code))
        metrics.imports_count = len(re.findall(r"import |require |from ", code))

    def find_duplicates(self, code: str, min_lines: int = 4) -> List[Dict]:
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        blocks = {}
        duplicates = []
        for i in range(len(lines) - min_lines + 1):
            block = "\n".join(lines[i : i + min_lines])
            bh = hashlib.md5(block.encode()).hexdigest()
            if bh in blocks:
                duplicates.append({"start_line": blocks[bh], "duplicate_line": i + 1, "lines": min_lines, "hash": bh})
            else:
                blocks[bh] = i + 1
        return duplicates

    def to_dict(self, metrics: CodeMetrics) -> Dict:
        return {
            "lines_of_code": metrics.lines_of_code,
            "cyclomatic_complexity": metrics.cyclomatic_complexity,
            "cognitive_complexity": metrics.cognitive_complexity,
            "maintainability_index": round(metrics.maintainability_index, 2),
            "comment_ratio": round(metrics.comment_ratio, 4),
            "duplicate_blocks": metrics.duplicate_blocks,
            "functions_count": metrics.functions_count,
            "classes_count": metrics.classes_count,
            "imports_count": metrics.imports_count,
        }

class RefactorEngine:
    """Performs automated code refactoring operations."""

    def extract_function(self, code: str, name: str, start_line: int, end_line: int) -> RefactorResult:
        lines = code.split("\n")
        selected = lines[start_line - 1 : end_line]
        indent = len(selected[0]) - len(selected[0].lstrip())
        body = "\n".join("    " + l.lstrip() for l in selected)
        func = f"\ndef {name}():\n{body}\n    pass\n"
        new_lines = lines[: start_line - 1] + [func.rstrip(), f"{name}()"] + lines[end_line:]
        return RefactorResult(
            original=code,
            refactored="\n".join(new_lines),
            refactor_type="extract_function",
            changes=[{"type": "extracted", "name": name, "lines": f"{start_line}-{end_line}"}],
        )

    def simplify_conditional(self, code: str) -> RefactorResult:
        new_code = code
        new_code = re.sub(r"if x == True:", "if x:", new_code)
        new_code = re.sub(r"if x == False:", "if not x:", new_code)
        new_code = re.sub(r"if x != True:", "if not x:", new_code)
        new_code = re.sub(r"if x != False:", "if x:", new_code)
        new_code = re.sub(r"else:\s*\n\s*return True\nelse:\s*\n\s*return False", "", new_code)
        return RefactorResult(
            original=code,
            refactored=new_code,
            refactor_type="simplify_conditional",
            changes=[{"type": "simplified", "count": len(new_code) - len(code)}],
        )

    def optimize_imports(self, code: str, language: str = "python") -> RefactorResult:
        import_lines = []
        other_lines = []
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append(stripped)
            else:
                other_lines.append(line)
        seen = set()
        unique_imports = []
        for imp in import_lines:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)
        unique_imports.sort()
        new_code = "\n".join(unique_imports + [""] + other_lines)
        removed = len(import_lines) - len(unique_imports)
        return RefactorResult(
            original=code,
            refactored=new_code,
            refactor_type="optimize_imports",
            changes=[{"type": "removed_duplicates", "count": removed}],
        )

    def add_docstring(self, code: str, description: str = "") -> RefactorResult:
        lines = code.split("\n")
        result = []
        for i, line in enumerate(lines):
            result.append(line)
            stripped = line.strip()
            if (stripped.startswith("def ") or stripped.startswith("class ")) and ":" in line:
                indent = len(line) - len(line.lstrip())
                if i + 1 < len(lines) and lines[i + 1].strip().startswith(('"""', "'''")):
                    continue
                doc = f'{" " * (indent + 4)}"""{description or "Auto-generated docstring."}"""'
                result.append(doc)
        return RefactorResult(
            original=code,
            refactored="\n".join(result),
            refactor_type="add_docstring",
            changes=[{"type": "added_docstrings"}],
        )

    def rename_symbol(self, code: str, old_name: str, new_name: str) -> RefactorResult:
        pattern = re.compile(r"\b" + re.escape(old_name) + r"\b")
        count = len(pattern.findall(code))
        new_code = pattern.sub(new_name, code)
        return RefactorResult(
            original=code,
            refactored=new_code,
            refactor_type="rename_symbol",
            changes=[{"type": "renamed", "old": old_name, "new": new_name, "occurrences": count}],
        )

class ReviewEngine:
    """Performs automated code review with rule-based analysis."""

    def __init__(self):
        self._rules = self._default_rules()

    def _default_rules(self) -> List[Dict]:
        return [
            {
                "id": "E001",
                "severity": "error",
                "pattern": r"except\s*:",
                "message": "Bare except clause",
                "suggestion": "Use 'except Exception:'",
            },
            {
                "id": "E002",
                "severity": "error",
                "pattern": r"import \*",
                "message": "Wildcard import",
                "suggestion": "Import specific names",
            },
            {
                "id": "W001",
                "severity": "warning",
                "pattern": r"print\(",
                "message": "Print statement found",
                "suggestion": "Use logging module",
            },
            {
                "id": "W002",
                "severity": "warning",
                "pattern": r"eval\(",
                "message": "eval() usage",
                "suggestion": "Use ast.literal_eval() or safer alternatives",
            },
            {
                "id": "W003",
                "severity": "warning",
                "pattern": r"exec\(",
                "message": "exec() usage",
                "suggestion": "Avoid exec() for security reasons",
            },
            {
                "id": "I001",
                "severity": "info",
                "pattern": r"TODO|FIXME|HACK|XXX",
                "message": "TODO/FIXME comment found",
                "suggestion": "Track and resolve these items",
            },
            {
                "id": "C001",
                "severity": "warning",
                "pattern": r'password\s*=\s*["\'][^"\']+["\']',
                "message": "Hardcoded password",
                "suggestion": "Use environment variables or secret manager",
            },
            {
                "id": "C002",
                "severity": "critical",
                "pattern": r'(api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
                "message": "Hardcoded secret/key",
                "suggestion": "Use secret management",
            },
            {
                "id": "S001",
                "severity": "error",
                "pattern": r"subprocess\.call\(.*shell\s*=\s*True",
                "message": "shell=True with subprocess",
                "suggestion": "Avoid shell injection, use list arguments",
            },
            {
                "id": "P001",
                "severity": "warning",
                "pattern": r"def \w+\([^)]*\):\s*\n\s*return",
                "message": "Function with single return",
                "suggestion": "Consider if function adds value",
            },
            {
                "id": "P002",
                "severity": "info",
                "pattern": r"class \w+\([^)]*\):\s*\n\s*pass",
                "message": "Empty class",
                "suggestion": "Add implementation or use dataclass/namedtuple",
            },
            {
                "id": "P003",
                "severity": "warning",
                "pattern": r"len\([^)]+\)\s*(==|!=|>|<|>=|<=)\s*0",
                "message": "Compare length to zero",
                "suggestion": "Use implicit boolean: 'if seq:' vs 'if len(seq) > 0:'",
            },
        ]

    def review(self, code: str, language: str = "python") -> Dict:
        issues = []
        lines = code.split("\n")
        for rule in self._rules:
            for i, line in enumerate(lines):
                matches = list(re.finditer(rule["pattern"], line, re.IGNORECASE))
                for m in matches:
                    issues.append(
                        ReviewIssue(
                            line=i + 1,
                            column=m.start() + 1,
                            severity=rule["severity"],
                            rule=rule["id"],
                            message=rule["message"],
                            suggestion=rule["suggestion"],
                        )
                    )
        by_severity = defaultdict(int)
        for issue in issues:
            by_severity[issue.severity] += 1
        score = max(
            0,
            100
            - by_severity.get("critical", 0) * 20
            - by_severity.get("error", 0) * 5
            - by_severity.get("warning", 0) * 1,
        )
        return {
            "issues": [
                {
                    "line": i.line,
                    "column": i.column,
                    "severity": i.severity,
                    "rule": i.rule,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
            "summary": {
                "total_issues": len(issues),
                "by_severity": dict(by_severity),
                "score": score,
                "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
            },
        }

class CodeGenerator:
    """Generates code from specifications and patterns."""

    def __init__(self):
        self._templates = self._default_templates()

    def _default_templates(self) -> Dict:
        return {
            "python_class": 'class {name}:\n    """{description}"""\n\n    def __init__(self{params}):\n{init_body}\n',
            "python_function": 'def {name}({params}):\n    """{description}"""\n{body}\n',
            "python_api": "@app.route('/{path}', methods=['{method}'])\ndef {func_name}():\n    {body}\n",
            "python_test": 'def test_{name}():\n    """Test {description}"""\n    # Arrange\n    {arrange}\n    # Act\n    {act}\n    # Assert\n    {asserts}\n',
        }

    def generate(self, spec: Dict) -> Dict:
        template_name = spec.get("template", "python_class")
        template = self._templates.get(template_name)
        if not template:
            return {"error": f"template '{template_name}' not found", "available": list(self._templates.keys())}
        code = template.format(**spec)
        return {"code": code, "template": template_name, "language": spec.get("language", "python")}

    def list_templates(self) -> Dict:
        return {"templates": list(self._templates.keys())}

    def scaffold_project(self, name: str, language: str = "python", features: Optional[List[str]] = None) -> Dict:
        features = features or []
        files = {}
        if language == "python":
            files[f"{name}/__init__.py"] = f'"""{name} package."""\n\n__version__ = "0.1.0"\n'
            files[f"{name}/main.py"] = (
                f'"""Main entry point for {name}."""\n\ndef main():\n    print("{name} started")\n\nif __name__ == "__main__":\n    main()\n'
            )
            if "cli" in features:
                files[f"{name}/cli.py"] = (
                    f'"""CLI interface for {name}."""\nimport argparse\n\ndef parse_args():\n    parser = argparse.ArgumentParser(description="{name}")\n    return parser.parse_args()\n'
                )
            if "config" in features:
                files[f"{name}/config.py"] = (
                    f'"""Configuration for {name}."""\nCONFIG = {{\n    "debug": False,\n    "version": "0.1.0",\n}}\n'
                )
            if "tests" in features:
                files[f"{name}/test_main.py"] = (
                    f'"""Tests for {name}."""\nimport pytest\n\ndef test_main():\n    assert True\n'
                )
        return {
            "project_name": name,
            "language": language,
            "files": files,
            "file_count": len(files),
            "features": features,
        }

class AtomCode(EnterpriseModule):
    """
    AUTO-EVO-AI v6.39 - Atom Code
    Enterprise intelligent code generation and refactoring engine with
    multi-language support, automated review, snippet management, and project scaffolding.
    """

    MODULE_ID = "atom_code"
    MODULE_NAME = "AtomCode"
    VERSION = "1.0.0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._snippets = SnippetManager()
        self._analyzer = CodeAnalyzer()
        self._refactorer = RefactorEngine()
        self._reviewer = ReviewEngine()
        self._generator = CodeGenerator()
        self._operation_count = 0

    async def execute(self, action="status", params=None, **kwargs) -> dict:
        params = params or {}
        self.trace("atom_code.execute", "start", action=action)
        self.metrics_collector.counter("atom_code.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info"):
                result = self.health_check()
            elif action == "help":
                result = {"actions": ["status", "info", "help"], "module": "atom_code"}
            else:
                result = self._dispatch(action, params)
            return {"success": True, "data": result, "action": action}
        except Exception as e:
            return {"success": False, "error": str(e)}
module_class = AtomCode
