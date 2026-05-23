"""
AUTO-EVO-AI V0.1 — 代码理解引擎
Grade: A (生产级) | Category: 开发工具
职责：代码AST分析、依赖关系图、代码搜索、架构理解、复杂度计算
"""

__module_meta__ = {
    "id": "code-understand",
    "name": "Code Understand",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "file_path", "type": "string", "required": True, "description": ""},
        {"name": "node", "type": "string", "required": True, "description": ""},
        {"name": "node", "type": "string", "required": True, "description": ""},
        {"name": "node", "type": "string", "required": True, "description": ""},
        {"name": "node", "type": "string", "required": True, "description": ""},
        {"name": "is_async", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["code", "developer", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 代码理解引擎 Grade: A (生产级) | Category: 开发工具",
}

import os
import ast
import json
import time
import uuid
import re
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

@dataclass
class FunctionInfo:
    """函数/方法信息"""

    name: str
    node_type: str = "function"  # function, method, async_function, async_method
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    params: List[str] = field(default_factory=list)
    return_type: str = ""
    decorators: List[str] = field(default_factory=list)
    docstring: str = ""
    complexity: int = 1
    calls: List[str] = field(default_factory=list)
    parent_class: str = ""

@dataclass
class ClassInfo:
    """类信息"""

    name: str
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    class_vars: Dict[str, str] = field(default_factory=dict)
    docstring: str = ""
    decorators: List[str] = field(default_factory=list)
    is_abstract: bool = False

@dataclass
class ImportInfo:
    """导入信息"""

    module: str
    names: List[str] = field(default_factory=list)
    is_from_import: bool = False
    is_relative: bool = False
    line: int = 0
    alias: str = ""

@dataclass
class FileAnalysis:
    """文件分析结果"""

    file_path: str
    language: str = "python"
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    avg_complexity: float = 0.0
    max_complexity: int = 1
    hash_md5: str = ""
    analyzed_at: float = 0.0

@dataclass
class DependencyNode:
    """依赖图节点"""

    module_name: str
    file_path: str = ""
    imports_from: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    complexity: int = 0
    functions_count: int = 0
    classes_count: int = 0

class CodeAnalyzer(ast.NodeVisitor):
    """AST代码分析器"""

    def __init__(self, file_path: str = ""):
        self.file_path = file_path
        self.classes: List[ClassInfo] = []
        self.functions: List[FunctionInfo] = []
        self.imports: List[ImportInfo] = []
        self.calls: Dict[str, List[str]] = defaultdict(list)
        self._current_class = ""
        self._current_function = ""

    def visit_ClassDef(self, node):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))

        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("decorator")

        class_info = ClassInfo(
            name=node.name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            docstring=ast.get_docstring(node) or "",
            decorators=decorators,
        )

        # 检查是否是抽象类
        for dec in decorators:
            if "abstract" in dec.lower():
                class_info.is_abstract = True

        # 类变量
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info.class_vars[target.id] = "class_var"

        self.classes.append(class_info)
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = ""

    def visit_FunctionDef(self, node):
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node):
        self._process_function(node, is_async=True)

    def _process_function(self, node, is_async: bool):
        params = [arg.arg for arg in node.args.args if arg.arg != "self" and arg.arg != "cls"]
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("decorator")

        return_annotation = ""
        if node.returns:
            try:
                return_annotation = ast.unparse(node.returns)
            except Exception:
                return_annotation = "unknown"

        # 计算圈复杂度
        complexity = self._calc_complexity(node)

        # 收集函数调用
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(ast.unparse(child.func))

        func_type = (
            "async_method"
            if is_async and self._current_class
            else "method"
            if self._current_class
            else "async_function"
            if is_async
            else "function"
        )

        func_info = FunctionInfo(
            name=node.name,
            node_type=func_type,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            params=params,
            return_type=return_annotation,
            decorators=decorators,
            docstring=ast.get_docstring(node) or "",
            complexity=complexity,
            calls=calls,
            parent_class=self._current_class,
        )

        self.functions.append(func_info)
        if self._current_class:
            for cls in self.classes:
                if cls.name == self._current_class:
                    cls.methods.append(node.name)
                    break
        self.generic_visit(node)

    def _calc_complexity(self, node) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            # elif用于elif分支
            if isinstance(child, ast.If) and hasattr(child, "orelse") and child.orelse:
                if len(child.orelse) == 1 and isinstance(child.orelse[0], ast.If):
                    pass  # elif, 不额外计数
        return complexity

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    names=[alias.name],
                    is_from_import=False,
                    is_relative=alias.name.startswith("."),
                    line=node.lineno,
                    alias=alias.asname or "",
                )
            )

    def visit_ImportFrom(self, node):
        module = node.module or ""
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportInfo(
                module=module,
                names=names,
                is_from_import=True,
                is_relative=(node.level or 0) > 0,
                line=node.lineno,
            )
        )

class CodeUnderstandManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """代码理解引擎 - 生产级实现"""

    MODULE_ID = "code_understand"
    MODULE_NAME = "code_understand"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "code_understand",
                "version": "7.0.0",
                "description": "代码理解引擎，支持AST分析、依赖图、复杂度计算、代码搜索",
            }
        )
        self._files: Dict[str, FileAnalysis] = {}
        self._dependency_graph: Dict[str, DependencyNode] = {}
        self._analyzer_cache: Dict[str, CodeAnalyzer] = {}
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

    def _analyze_code(self, code: str, file_path: str = "") -> CodeAnalyzer:
        """分析Python代码"""
        cache_key = hashlib.md5(code.encode()).hexdigest()
        if cache_key in self._analyzer_cache:
            return self._analyzer_cache[cache_key]

        try:
            tree = ast.parse(code)
            analyzer = CodeAnalyzer(file_path)
            analyzer.visit(tree)
            self._analyzer_cache[cache_key] = analyzer
            return analyzer
        except SyntaxError as e:
            logger.error(f"[CodeUnderstand] 语法错误 {file_path}: {e}")
            return CodeAnalyzer(file_path)

    def _count_lines(self, code: str) -> Tuple[int, int, int, int]:
        """统计行数: total, code, comment, blank"""
        total = len(code.split("\n"))
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        in_docstring = False
        for line in code.split("\n"):
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif in_docstring:
                comment_lines += 1
                if '"""' in stripped or "'''" in stripped:
                    cnt = stripped.count('"""') + stripped.count("'''")
                    if cnt >= 2:
                        in_docstring = False
            elif stripped.startswith("#"):
                comment_lines += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
                cnt = stripped.count('"""') + stripped.count("'''")
                if cnt == 1:
                    in_docstring = True
            else:
                code_lines += 1
        return total, code_lines, comment_lines, blank_lines

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("code_understand.execute.calls", 1)
        self.audit("code_analysis", {"action": action})
        params = params or {}
        try:
            if action == "analyze":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                total, code_l, comment_l, blank_l = self._count_lines(code)
                complexities = [f.complexity for f in analyzer.functions]
                avg_c = sum(complexities) / len(complexities) if complexities else 0
                max_c = max(complexities) if complexities else 1

                analysis = FileAnalysis(
                    file_path=file_path,
                    language="python",
                    total_lines=total,
                    code_lines=code_l,
                    comment_lines=comment_l,
                    blank_lines=blank_l,
                    classes=[c.name for c in analyzer.classes],
                    functions=[f.name for f in analyzer.functions],
                    imports=[
                        f"{i.module}.{n}" if i.is_from_import else i.module
                        for i in analyzer.imports
                        for n in [i.names[0] if i.names else ""]
                    ],
                    avg_complexity=round(avg_c, 1),
                    max_complexity=max_c,
                    hash_md5=hashlib.md5(code.encode()).hexdigest(),
                    analyzed_at=time.time(),
                )
                self._files[file_path or hashlib.md5(code.encode()).hexdigest()[:8]] = analysis
                return {
                    "success": True,
                    "result": {
                        "total_lines": analysis.total_lines,
                        "code_lines": analysis.code_lines,
                        "comment_lines": analysis.comment_lines,
                        "blank_lines": analysis.blank_lines,
                        "classes": len(analyzer.classes),
                        "functions": len(analyzer.functions),
                        "imports": len(analyzer.imports),
                        "avg_complexity": analysis.avg_complexity,
                        "max_complexity": analysis.max_complexity,
                        "hash_md5": analysis.hash_md5,
                    },
                }

            elif action == "get_classes":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                return {
                    "success": True,
                    "result": [
                        {
                            "name": c.name,
                            "bases": c.bases,
                            "methods": c.methods,
                            "class_vars": c.class_vars,
                            "docstring": c.docstring[:100] if c.docstring else "",
                            "line": c.line_start,
                            "is_abstract": c.is_abstract,
                            "decorators": c.decorators,
                        }
                        for c in analyzer.classes
                    ],
                }

            elif action == "get_functions":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                return {
                    "success": True,
                    "result": [
                        {
                            "name": f.name,
                            "type": f.node_type,
                            "params": f.params,
                            "return_type": f.return_type,
                            "complexity": f.complexity,
                            "line": f.line_start,
                            "end_line": f.line_end,
                            "docstring": f.docstring[:100] if f.docstring else "",
                            "calls": f.calls[:10],
                            "parent_class": f.parent_class,
                            "decorators": f.decorators,
                        }
                        for f in analyzer.functions
                    ],
                }

            elif action == "get_imports":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                return {
                    "success": True,
                    "result": [
                        {
                            "module": i.module,
                            "names": i.names,
                            "is_from": i.is_from_import,
                            "is_relative": i.is_relative,
                            "line": i.line,
                        }
                        for i in analyzer.imports
                    ],
                }

            elif action == "search_symbol":
                code = params.get("content", "")
                symbol = params.get("symbol", "").strip()
                if not code or not symbol:
                    return {"success": False, "error": "代码和符号不能为空"}
                analyzer = self._analyze_code(code)
                results = []
                # 搜索类
                for c in analyzer.classes:
                    if symbol.lower() in c.name.lower():
                        results.append({"type": "class", "name": c.name, "line": c.line_start})
                # 搜索函数
                for f in analyzer.functions:
                    if symbol.lower() in f.name.lower():
                        results.append(
                            {"type": f.node_type, "name": f.name, "line": f.line_start, "class": f.parent_class or None}
                        )
                # 搜索导入
                for i in analyzer.imports:
                    if symbol.lower() in i.module.lower():
                        results.append({"type": "import", "name": i.module, "line": i.line})
                return {"success": True, "result": results}

            elif action == "complexity_report":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                functions = sorted(analyzer.functions, key=lambda f: f.complexity, reverse=True)
                total_complexity = sum(f.complexity for f in functions)
                high = [f for f in functions if f.complexity > 10]
                medium = [f for f in functions if 5 < f.complexity <= 10]
                low = [f for f in functions if f.complexity <= 5]

                return {
                    "success": True,
                    "result": {
                        "total_complexity": total_complexity,
                        "avg_complexity": round(total_complexity / len(functions), 1) if functions else 0,
                        "functions_total": len(functions),
                        "high_complexity": len(high),
                        "medium_complexity": len(medium),
                        "low_complexity": len(low),
                        "top_complex": [
                            {"name": f.name, "complexity": f.complexity, "line": f.line_start} for f in functions[:5]
                        ],
                    },
                }

            elif action == "build_dependency_graph":
                code = params.get("content", "")
                file_path = params.get("file_path", "")
                if not code:
                    return {"success": False, "error": "代码内容不能为空"}
                analyzer = self._analyze_code(code, file_path)
                module_name = os.path.splitext(os.path.basename(file_path or "module.py"))[0]
                node = DependencyNode(
                    module_name=module_name,
                    file_path=file_path,
                    imports_from=[i.module for i in analyzer.imports if not i.is_relative],
                    complexity=sum(f.complexity for f in analyzer.functions),
                    functions_count=len(analyzer.functions),
                    classes_count=len(analyzer.classes),
                )
                self._dependency_graph[module_name] = node

                # 更新反向依赖
                for imp in node.imports_from:
                    if imp in self._dependency_graph:
                        self._dependency_graph[imp].imported_by.append(module_name)

                return {
                    "success": True,
                    "result": {
                        "module": module_name,
                        "imports": node.imports_from,
                        "imported_by": node.imported_by,
                        "complexity": node.complexity,
                        "graph_size": len(self._dependency_graph),
                    },
                }

            elif action == "get_dependency_graph":
                return {
                    "success": True,
                    "result": {
                        "nodes": len(self._dependency_graph),
                        "modules": [
                            {
                                "name": n.module_name,
                                "imports": n.imports_from,
                                "imported_by": n.imported_by,
                                "complexity": n.complexity,
                            }
                            for n in self._dependency_graph.values()
                        ],
                    },
                }

            elif action == "get_stats":
                total_files = len(self._files)
                total_functions = sum(len([f for f in self._analyzer_cache.values() for _ in f.functions]))
                return {
                    "success": True,
                    "result": {
                        "files_analyzed": total_files,
                        "graph_nodes": len(self._dependency_graph),
                        "cache_entries": len(self._analyzer_cache),
                    },
                }

            elif action == "clear_cache":
                self._analyzer_cache.clear()
                self._dependency_graph.clear()
                self._files.clear()
                return {"success": True, "result": {"cleared": True}}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[CodeUnderstand] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy" if self._initialized else "stopped",
                "files_analyzed": len(self._files),
                "graph_nodes": len(self._dependency_graph),
                "cache_entries": len(self._analyzer_cache),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False
        self._analyzer_cache.clear()
        logger.info("关闭代码理解引擎")

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = CodeUnderstandManager
