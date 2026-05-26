"""
AUTO-EVO-AI V0.1 - Bytecode Studio Module (Grade: A Production)
字节码工作室：Python字节码分析、安全审计、优化建议、反编译辅助
"""

__module_meta__ = {
    "id": "bytecodestudio",
    "name": "Bytecodestudio",
    "version": "V0.1",
    "group": "developer",
    "inputs": [
        {"name": "code_obj", "type": "string", "required": True, "description": ""},
        {"name": "instr", "type": "string", "required": True, "description": ""},
        {"name": "module_name", "type": "string", "required": True, "description": ""},
        {"name": "operation", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["bytecodestudio", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Bytecode Studio Module (Grade: A Production) 字节码工作室：Python字节码分析、安全审计、优化建议、反编译辅助",
}

import os
import sys
import asyncio
import time
import logging
import uuid
import hashlib
import dis
import types
import struct
import importlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger
except ImportError:

    class EnterpriseModule:
        def __init__(self):
            self._initialized = False
            self.logger = logging.getLogger(__name__)

        def initialize(self):
            self._initialized = True

        def shutdown(self):
            self._initialized = False

        def health_check(self):
            return {"status": "ok"}

    class CircuitBreakerMixin:
        _circuit_breaker = None

    class RateLimiterMixin:
        _rate_limiter = None

    trace_operation = lambda x: lambda f: f
    prometheus_timer = lambda x: lambda f: f
    metrics_collector = None

    class AuditLogger:
        def log(self, *a, **k):
            pass

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityFinding:
    finding_id: str = field(default_factory=lambda: f"sec_{uuid.uuid4().hex[:8]}")
    risk_level: RiskLevel = RiskLevel.INFO
    category: str = ""
    description: str = ""
    location: str = ""
    recommendation: str = ""

@dataclass
class OptimizationSuggestion:
    suggestion_id: str = field(default_factory=lambda: f"opt_{uuid.uuid4().hex[:8]}")
    category: str = ""
    impact: str = "low"
    description: str = ""
    estimated_saving: str = ""

@dataclass
class AnalysisSession:
    session_id: str = field(default_factory=lambda: f"ses_{uuid.uuid4().hex[:8]}")
    target: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    function_count: int = 0
    total_instructions: int = 0
    call_count: int = 0
    jump_count: int = 0
    security_findings: List[SecurityFinding] = field(default_factory=list)
    optimizations: List[OptimizationSuggestion] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top_operations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

class BytecodeSecurityAnalyzer(object):
    """字节码安全分析器 - 检测潜在安全风险模式"""

    # 高风险操作码和模式
    DANGEROUS_OPS = frozenset(["LOAD_ATTR", "CALL_FUNCTION", "CALL_METHOD", "EXEC_STMT", "IMPORT_NAME", "IMPORT_FROM"])
    RISKY_BUILTINS = frozenset(
        ["exec", "eval", "compile", "open", "__import__", "getattr", "setattr", "delattr", "globals", "locals"]
    )

    def __init__(self):
        self._scan_count: int = 0
        self._findings_total: int = 0

    def scan_bytecode(self, code_obj: types.CodeType) -> List[Dict]:
        """扫描字节码中的安全风险"""
        self._scan_count += 1
        findings = []
        try:
            instructions = list(dis.get_instructions(code_obj))
        except Exception:
            return findings
        for instr in instructions:
            risk = self._assess_instruction(instr)
            if risk:
                findings.append(risk)
                self._findings_total += 1
        return findings

    def _assess_instruction(self, instr: dis.Instruction) -> Optional[Dict]:
        """评估单条指令的风险"""
        if instr.opname in self.DANGEROUS_OPS:
            if instr.argval and isinstance(instr.argval, str) and instr.argval in self.RISKY_BUILTINS:
                return {
                    "type": "dangerous_builtin",
                    "opname": instr.opname,
                    "target": instr.argval,
                    "offset": instr.offset,
                    "risk": "HIGH",
                    "description": f"使用危险内建函数: {instr.argval}",
                }
            if instr.opname == "IMPORT_NAME" and instr.argval:
                return {
                    "type": "dynamic_import",
                    "target": instr.argval,
                    "offset": instr.offset,
                    "risk": "MEDIUM",
                    "description": f"动态导入模块: {instr.argval}",
                }
        return None

    def scan_module(self, module_name: str) -> Dict:
        """扫描整个模块的所有函数"""
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            return {"error": f"module {module_name} not found"}
        total_findings = []
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name)
            if isinstance(obj, types.FunctionType):
                findings = self.scan_bytecode(obj.__code__)
                for f in findings:
                    f["function"] = attr_name
                total_findings.extend(findings)
            elif isinstance(obj, type):
                for method_name in dir(obj):
                    try:
                        method = getattr(obj, method_name)
                        if isinstance(method, types.FunctionType):
                            findings = self.scan_bytecode(method.__code__)
                            for f in findings:
                                f["class"] = attr_name
                                f["method"] = method_name
                            total_findings.extend(findings)
                    except Exception:
                        pass
        risk_counts = defaultdict(int)
        for f in total_findings:
            risk_counts[f["risk"]] += 1
        return {
            "module": module_name,
            "total_findings": len(total_findings),
            "risk_distribution": dict(risk_counts),
            "findings": sorted(total_findings, key=lambda x: x.get("risk", ""), reverse=True),
        }

    def get_stats(self) -> Dict:
        return {"total_scans": self._scan_count, "total_findings": self._findings_total}

class BytecodeStudioManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self):
        self._initialized = False

    """字节码工作室管理器"""

    def __init__(self):

        super().__init__()
        self.module_name = "bytecodestudio"
        self.module_id = self.module_name
        self.module_version = "7.0.0"
        self._sessions: Dict[str, AnalysisSession] = {}
        self._audit = AuditLogger()
        self._analysis_count = 0
        self._total_functions_analyzed = 0
        self._total_security_findings = 0

    def initialize(self):
        logger.info("bytecodestudio initialized")

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("bytecodestudio_ops_total", labels={"action": operation})
        self.audit("execute", f"action={action}")

        params = params or {}
        if operation == "analyze_code":
            return self._analyze_code(params)
        elif operation == "analyze_module":
            return self._analyze_module(params)
        elif operation == "disassemble":
            return self._disassemble(params)
        elif operation == "security_audit":
            return self._security_audit(params)
        elif operation == "optimize_suggestions":
            return self._optimize_suggestions(params)
        elif operation == "get_session":
            return self._get_session(params)
        elif operation == "list_sessions":
            return self._list_sessions(params)
        elif operation == "complexity_estimate":
            return self._complexity_estimate(params)
        elif operation == "instruction_stats":
            return self._instruction_stats(params)
        elif operation == "compare_functions":
            return self._compare_functions(params)
        else:
            return {
                "success": False,
                "error": f"unknown op: {operation}",
                "available": [
                    "analyze_code",
                    "analyze_module",
                    "disassemble",
                    "security_audit",
                    "optimize_suggestions",
                    "get_session",
                    "list_sessions",
                    "complexity_estimate",
                    "instruction_stats",
                    "compare_functions",
                ],
            }

    def _analyze_code(self, p: Dict) -> Dict:
        code_src = p.get("code", "")
        name = p.get("session_name", "inline")
        if not code_src:
            return {"success": False, "error": "missing code"}
        try:
            co = compile(code_src, "<string>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": f"syntax error: {e}"}
        session = AnalysisSession(target=name)
        self._walk_code(co, session)
        self._check_security(co, session)
        self._gen_opts(session)
        self._sessions[session.session_id] = session
        self._analysis_count += 1
        self._total_functions_analyzed += session.function_count
        self._total_security_findings += len(session.security_findings)
        return {
            "success": True,
            "result": {
                "session_id": session.session_id,
                "target": name,
                "functions": session.function_count,
                "total_instructions": session.total_instructions,
                "call_count": session.call_count,
                "jump_count": session.jump_count,
                "security_findings": len(session.security_findings),
                "optimizations": len(session.optimizations),
            },
        }

    def _analyze_module(self, p: Dict) -> Dict:
        mod_name = p.get("module", "")
        if not mod_name:
            return {"success": False, "error": "missing module"}
        try:
            mod = importlib.import_module(mod_name)
            if not hasattr(mod, "__file__") or mod.__file__ is None:
                return {"success": False, "error": "no file for module"}
            with open(mod.__file__, encoding="utf-8", errors="ignore") as f:
                src = f.read()
            co = compile(src, mod.__file__, "exec")
        except ImportError:
            return {"success": False, "error": f"cannot import: {mod_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        session = AnalysisSession(target=mod_name)
        self._walk_code(co, session)
        self._check_security(co, session)
        self._gen_opts(session)
        self._sessions[session.session_id] = session
        self._analysis_count += 1
        return {
            "success": True,
            "result": {
                "session_id": session.session_id,
                "target": mod_name,
                "functions": session.function_count,
                "total_instructions": session.total_instructions,
                "security_findings": len(session.security_findings),
                "optimizations": len(session.optimizations),
            },
        }

    def _walk_code(self, co, session: AnalysisSession):
        """递归遍历代码对象收集指令统计"""
        try:
            consts = co.co_consts or []
        except AttributeError:
            return
        for c in consts:
            if isinstance(c, types.CodeType):
                session.function_count += 1
                self._walk_code(c, session)
        try:
            for instr in dis.get_instructions(co):
                session.total_instructions += 1
                op = instr.opname
                if op.startswith(("CALL_", "PRECALL")):
                    session.call_count += 1
                    session.category_counts["call"] += 1
                elif op.startswith(("JUMP_", "FOR_ITER")):
                    session.jump_count += 1
                    session.category_counts["jump"] += 1
                elif op.startswith("LOAD_"):
                    session.category_counts["load"] += 1
                elif op.startswith("STORE_"):
                    session.category_counts["store"] += 1
                elif op.startswith(("BINARY_", "COMPARE", "IS_OP", "CONTAINS_OP", "UNARY_", "GET_ITER")):
                    session.category_counts["operator"] += 1
                elif op.startswith(("BUILD_", "LIST_", "SET_", "MAP_")):
                    session.category_counts["build"] += 1
                elif op.startswith("RETURN_"):
                    session.category_counts["return"] += 1
                else:
                    session.category_counts["other"] += 1
                session.top_operations[op] += 1
        except Exception:
            pass

    def _check_security(self, co, session: AnalysisSession):
        dangerous = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "getattr",
            "open",
            "os.system",
            "subprocess",
            "pickle.loads",
            "marshal.loads",
            "ctypes",
        }
        findings = []
        try:
            for instr in dis.get_instructions(co):
                val = str(instr.argval or "")
                for d in dangerous:
                    if d in val:
                        findings.append(
                            SecurityFinding(
                                risk_level=RiskLevel.HIGH,
                                category="dangerous_call",
                                description=f"dangerous call detected: {val}",
                                location=f"offset {instr.offset}",
                                recommendation="ensure not on user-controlled path",
                            )
                        )
                if instr.opname == "LOAD_CONST" and instr.argval is not None:
                    s = str(instr.argval)
                    if any(kw in s.lower() for kw in ["password", "secret", "api_key", "token"]):
                        findings.append(
                            SecurityFinding(
                                risk_level=RiskLevel.MEDIUM,
                                category="hardcoded_secret",
                                description=f"possible hardcoded secret: {s[:30]}",
                                recommendation="move to env vars or secrets manager",
                            )
                        )
        except Exception:
            pass
        session.security_findings = findings

    def _gen_opts(self, session: AnalysisSession):
        opts = []
        top = sorted(session.top_operations.items(), key=lambda x: x[1], reverse=True)[:3]
        for op_name, count in top:
            if count > 10:
                opts.append(
                    OptimizationSuggestion(
                        category="hot_instruction",
                        impact="medium",
                        description=f"'{op_name}' used {count} times",
                        estimated_saving="review for optimization opportunities",
                    )
                )
        if session.total_instructions > 0 and session.jump_count > session.total_instructions * 0.3:
            ratio = round(session.jump_count / session.total_instructions * 100, 1)
            opts.append(
                OptimizationSuggestion(
                    category="branch_heavy",
                    impact="high",
                    description=f"branch ratio {ratio}% is high",
                    estimated_saving="consider simplifying control flow",
                )
            )
        if session.call_count > session.total_instructions * 0.4:
            opts.append(
                OptimizationSuggestion(
                    category="call_heavy",
                    impact="medium",
                    description=f"high call density {session.call_count}/{session.total_instructions}",
                    estimated_saving="consider inlining or caching",
                )
            )
        session.optimizations = opts

    def _disassemble(self, p: Dict) -> Dict:
        code_src = p.get("code", "")
        if not code_src:
            return {"success": False, "error": "missing code"}
        try:
            co = compile(code_src, "<string>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": str(e)}
        instrs = []
        for i in dis.get_instructions(co):
            argval_str = str(i.argval)[:80] if i.argval is not None else None
            instrs.append(
                {
                    "offset": i.offset,
                    "opname": i.opname,
                    "opcode": i.opcode,
                    "arg": i.arg,
                    "argval": argval_str,
                    "line": i.starts_line,
                    "is_target": i.is_jump_target,
                }
            )
        return {
            "success": True,
            "result": {"name": getattr(co, "co_name", "<module>"), "instructions": instrs, "count": len(instrs)},
        }

    def _security_audit(self, p: Dict) -> Dict:
        sid = p.get("session_id")
        if not sid or sid not in self._sessions:
            return {"success": False, "error": "session not found"}
        s = self._sessions[sid]
        findings = [
            {
                "id": f.finding_id,
                "risk": f.risk_level.value,
                "category": f.category,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in s.security_findings
        ]
        critical = [f for f in findings if f["risk"] in ("critical", "high")]
        return {
            "success": True,
            "result": {
                "total": len(findings),
                "critical_high": len(critical),
                "findings": findings,
                "pass": len(critical) == 0,
            },
        }

    def _optimize_suggestions(self, p: Dict) -> Dict:
        sid = p.get("session_id")
        if not sid or sid not in self._sessions:
            return {"success": False, "error": "session not found"}
        s = self._sessions[sid]
        opts = [
            {
                "id": o.suggestion_id,
                "category": o.category,
                "impact": o.impact,
                "description": o.description,
                "saving": o.estimated_saving,
            }
            for o in s.optimizations
        ]
        return {
            "success": True,
            "result": {
                "total": len(opts),
                "high_impact": len([o for o in opts if o["impact"] == "high"]),
                "suggestions": opts,
            },
        }

    def _get_session(self, p: Dict) -> Dict:
        sid = p.get("session_id")
        if not sid or sid not in self._sessions:
            return {"success": False, "error": "session not found"}
        s = self._sessions[sid]
        return {
            "success": True,
            "result": {
                "session_id": s.session_id,
                "target": s.target,
                "created_at": s.created_at.isoformat(),
                "functions": s.function_count,
                "total_instructions": s.total_instructions,
                "call_count": s.call_count,
                "jump_count": s.jump_count,
                "security_findings": len(s.security_findings),
                "optimizations": len(s.optimizations),
            },
        }

    def _list_sessions(self, p: Dict) -> Dict:
        limit = p.get("limit", 20)
        sessions = list(self._sessions.values())[-limit:]
        return {
            "success": True,
            "result": [
                {
                    "session_id": s.session_id,
                    "target": s.target,
                    "created_at": s.created_at.isoformat(),
                    "functions": s.function_count,
                    "instructions": s.total_instructions,
                }
                for s in sessions
            ],
            "total": len(self._sessions),
        }

    def _complexity_estimate(self, p: Dict) -> Dict:
        code_src = p.get("code", "")
        if not code_src:
            return {"success": False, "error": "missing code"}
        try:
            co = compile(code_src, "<string>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": str(e)}
        results = []
        self._collect_complexity(co, results)
        return {"success": True, "result": results}

    def _collect_complexity(self, co, results: List):
        try:
            consts = co.co_consts or []
        except AttributeError:
            return
        for c in consts:
            if isinstance(c, types.CodeType):
                try:
                    instrs = list(dis.get_instructions(c))
                    branches = sum(1 for i in instrs if i.opname.startswith(("JUMP_", "FOR_ITER")))
                    calls = sum(1 for i in instrs if i.opname.startswith("CALL_"))
                    cx = branches + calls + 1
                    results.append(
                        {
                            "name": c.co_name,
                            "instructions": len(instrs),
                            "branches": branches,
                            "calls": calls,
                            "complexity": cx,
                            "risk": "low" if cx < 10 else "medium" if cx < 20 else "high",
                        }
                    )
                except Exception:
                    pass
                self._collect_complexity(c, results)

    def _instruction_stats(self, p: Dict) -> Dict:
        sid = p.get("session_id")
        if not sid or sid not in self._sessions:
            return {"success": False, "error": "session not found"}
        s = self._sessions[sid]
        top = sorted(s.top_operations.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "success": True,
            "result": {
                "total": s.total_instructions,
                "by_category": dict(s.category_counts),
                "top_operations": [{"opname": op, "count": cnt} for op, cnt in top],
            },
        }

    def _compare_functions(self, p: Dict) -> Dict:
        code_a = p.get("code_a", "")
        code_b = p.get("code_b", "")
        if not code_a or not code_b:
            return {"success": False, "error": "missing code_a or code_b"}
        try:
            co_a = compile(code_a, "<a>", "exec")
            co_b = compile(code_b, "<b>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": str(e)}
        instr_a = list(dis.get_instructions(co_a))
        instr_b = list(dis.get_instructions(co_b))
        smaller = "code_b" if len(instr_b) < len(instr_a) else "code_a" if len(instr_a) < len(instr_b) else "equal"
        return {
            "success": True,
            "result": {
                "code_a": {"instructions": len(instr_a)},
                "code_b": {"instructions": len(instr_b)},
                "difference": abs(len(instr_a) - len(instr_b)),
                "smaller": smaller,
            },
        }

    def shutdown(self):
        self._initialized = False
        self._audit.log("shutdown", "bytecodestudio shutdown")

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy" if self._initialized else "not_initialized",
                "sessions": len(self._sessions),
                "total_analyses": self._analysis_count,
                "functions_analyzed": self._total_functions_analyzed,
                "security_findings": self._total_security_findings,
            }
        )
        return result

module_class = BytecodeStudioManager
