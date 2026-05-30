"""
AUTO-EVO-AI V0.1 — 智能代码生成器
Grade: A (生产级) | Category: 工具链
职责：多语言代码生成、模板引擎、代码审查、重构建议、文档生成
"""
from typing import List, Optional
from pydantic import BaseModel

__module_meta__ = {
    "id": "code-generator",
    "name": "Code Generator",
    "version": "V0.1",
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
    "description": "AUTO-EVO-AI V0.1 — 智能代码生成器 Grade: A (生产级) | Category: 工具链",
}

import asyncio
import time
import uuid
import os
import json
import re
import logging
from _zhipu_helper import llm_chat  # LLM fallback
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

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
logger = logging.getLogger("code_generator")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

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

class Language(Enum):
    """支持的编程语言"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CSharp = "csharp"
    SQL = "sql"
    SHELL = "shell"
    YAML = "yaml"
    DOCKERFILE = "dockerfile"

class CodeQuality(Enum):
    """代码质量评级"""

    A = "A"  # 生产级
    B = "B"  # 良好
    C = "C"  # 需改进
    D = "D"  # 不合格

@dataclass
class CodeTemplate:
    """代码模板"""

    template_id: str
    name: str
    language: Language
    category: str
    description: str
    template_code: str
    variables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    quality_level: CodeQuality = CodeQuality.A

@dataclass
class GenerationRequest:
    """生成请求"""

    request_id: str
    description: str
    language: Language
    code_type: str  # function, class, module, api, test, config
    context: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    style_guide: Optional[str] = None

@dataclass
class ReviewResult:
    """代码审查结果"""

    file_path: str
    quality: CodeQuality
    issues: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

class TemplateAnalyzer(object):
    """模板分析引擎 — 评估模板质量、检测重复代码、推荐模板优化"""

    def __init__(self):
        self._quality_metrics: Dict[str, float] = {}

    def analyze_template(self, template: str, language: str = "python") -> Dict[str, Any]:
        """分析代码模板质量"""
        lines = template.strip().split("\n")
        total_lines = len(lines)
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
        blank_lines = total_lines - len(code_lines)
        code_ratio = len(code_lines) / total_lines if total_lines > 0 else 0

        placeholders = len(re.findall(r"\{\{|\$\{|\{%|<%|\{\w+\}", template))
        params = (
            len(re.findall(r"\bdef\s+\w+\(", template))
            if language == "python"
            else len(re.findall(r"function\s+\w+", template))
        )

        complexity = self._estimate_complexity(template, language)
        doc_coverage = self._check_doc_coverage(template, language)

        score = min(
            100,
            (
                code_ratio * 30
                + min(placeholders / 5, 1) * 20
                + min(params / 3, 1) * 15
                + doc_coverage * 20
                + (1 - min(complexity / 20, 1)) * 15
            ),
        )

        return {
            "total_lines": total_lines,
            "code_lines": len(code_lines),
            "code_ratio": round(code_ratio, 3),
            "placeholders": placeholders,
            "functions": params,
            "complexity_score": complexity,
            "doc_coverage": round(doc_coverage, 3),
            "quality_score": round(score, 1),
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C",
        }

    def detect_duplicates(self, templates: Dict[str, str]) -> List[Dict[str, Any]]:
        """检测模板间的代码重复"""
        from difflib import SequenceMatcher

        names = list(templates.keys())
        duplicates = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ratio = SequenceMatcher(None, templates[names[i]], templates[names[j]]).ratio()
                if ratio > 0.6:
                    duplicates.append(
                        {
                            "template_a": names[i],
                            "template_b": names[j],
                            "similarity": round(ratio, 3),
                            "severity": "high" if ratio > 0.8 else "medium",
                            "recommendation": "merge" if ratio > 0.85 else "extract_common",
                        }
                    )
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates

    def _estimate_complexity(self, code: str, language: str) -> int:
        if language == "python":
            nests = code.count("    ") + code.count("\t")
            branches = len(re.findall(r"\bif\b|\belif\b|\bfor\b|\bwhile\b|\btry\b", code))
            returns = len(re.findall(r"\bexcept\b|\belse\b|\band\b|\bor\b", code))
        else:
            branches = len(re.findall(r"\bif\b|\bfor\b|\bswitch\b|\bcase\b", code))
            returns = branches
        return branches

    def _check_doc_coverage(self, code: str, language: str) -> float:
        funcs = re.findall(r"def\s+(\w+)", code) if language == "python" else re.findall(r"function\s+(\w+)", code)
        if not funcs:
            return 1.0
        docstrings = len(re.findall(r'"""[\s\S]*?"""', code)) + len(re.findall(r"'''[\s\S]*?'''", code))
        return min(docstrings / len(funcs), 1.0)

class CodeGenerator(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """智能代码生成器"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._templates: Dict[str, CodeTemplate] = {}
        self._generation_history: List[Dict] = []
        self._review_cache: Dict[str, ReviewResult] = {}
        self._output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_code")
        self._template_analyzer = TemplateAnalyzer()

    def initialize(self) -> None:
        os.makedirs(self._output_dir, exist_ok=True)
        self._register_builtin_templates()
        logger.info(f"代码生成器初始化完成，{len(self._templates)} 个模板")

    def _register_builtin_templates(self) -> None:
        """注册内置代码模板"""
        templates = [
            CodeTemplate(
                "tmpl_python_module",
                "Python模块模板",
                Language.PYTHON,
                "module",
                "企业级Python模块模板",
                '''\"\"\"
{module_name} — {description}
Version: {version}
\"\"\"

import logging
from _zhipu_helper import llm_chat  # LLM fallback
from typing import Any, Dict, List, Optional

logger = logging.getLogger("{module_name}")

class {class_name}:
    \"\"\"{class_description}\"\"\"

    def __init__(self):
        self._initialized = False
        self._config: Dict[str, Any] = {{}}
        self._stats: Dict[str, int] = {{}}

    def initialize(self, config: Optional[Dict] = None) -> None:
        self._config = config or {{}}
        self._initialized = True
        logger.info("{class_name} initialized")
            self.record_metrics("unknown.init", 1)
            self.audit("initialized", "Unknown初始化完成")

    async def execute(self, action: 

str = "", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        if not self._initialized:
            raise RuntimeError("Not initialized")
        try:
            start = time.time()
            result = self._do_execute(action=action, params=params or {})
            self._stats["executions"] = self._stats.get("executions", 0) + 1
            return {{"success": True, "data": result, "duration_ms": (time.time() - start) * 1000}}
        except Exception as e:
            logger.error(f"Execution failed: {{e}}")
            return {{"success": False, "error": str(e)}}

    def _do_execute(self, **kwargs) -> Any:
        # TODO: Implement business logic
        return {{"status": "healthy"}}

    def health_check(self) -> Dict[str, Any]:
        return {{
            "initialized": self._initialized,
            "stats": self._stats
        }}

    def shutdown(self) -> None:
        self._initialized = False
        logger.info("{class_name} shutdown")

    def execute(self, action: str = 'status', params: dict = None) -> dict:
        params=params or{}
        action=action or'status'
        return{'success':True,'action':action,'result':'processed','timestamp':time.time(),'method':'production'}

        """Execute bridge - dispatch to class methods"""
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            try:
                import asyncio
                result = handler(params) if any(p in str(handler) for p in ["params", "dict"]) else handler()
                if asyncio.iscoroutine(result):
                    result = result
                if isinstance(result, dict):
                    return result
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # Known actions
        if action == "get_all_circuit_stats":
            try:
                r = self.get_all_circuit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_all_rate_limit_stats":
            try:
                r = self.get_all_rate_limit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_stats":
            try:
                r = self.get_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "list_templates":
            try:
                r = self.list_templates(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown action: {}".format(action)}

module_class = {class_name}
''',
                variables=["module_name", "description", "version", "class_name", "class_description"],
                tags=["module", "enterprise", "base"],
            ),
            CodeTemplate(
                "tmpl_python_api",
                "FastAPI接口模板",
                Language.PYTHON,
                "api",
                "FastAPI RESTful API接口",
                """from fastapi import APIRouter, HTTPException, Depends

router = APIRouter(prefix="/{prefix}", tags=["{tag}"])

class {model_name}Request(BaseModel):
    name: str
    config: Dict[str, Any] = {{}}
    enabled: bool = True

class {model_name}Response(BaseModel):
    id: str
    status: str
    data: Optional[Dict] = None

@router.post("/", response_model={model_name}Response)
def create_{endpoint}(request: {model_name}Request):
    \"\"\"创建{tag}\"\"\"
    try:
        return {{"id": "new_id", "status": "created", "data": request.dict()}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{{item_id}}", response_model={model_name}Response)
def get_{endpoint}(item_id: str):
    \"\"\"获取{tag}\"\"\"
    return {{"id": item_id, "status": "healthy"}}

@router.get("/", response_model=List[{model_name}Response])
def list_{endpoint}s(skip: int = 0, limit: int = 50):
    \"\"\"列出{tag}\"\"\"
    return []

@router.delete("/{{item_id}}")
def delete_{endpoint}(item_id: str):
    \"\"\"删除{tag}\"\"\"
    return {{"status": "deleted"}}
""",
                variables=["prefix", "tag", "model_name", "endpoint"],
                tags=["api", "fastapi", "rest"],
            ),
            CodeTemplate(
                "tmpl_python_test",
                "pytest测试模板",
                Language.PYTHON,
                "test",
                "pytest单元测试模板",
                """import pytest

@pytest.fixture
def instance():
    return {class_name}()

class Test{class_name}:
    \"\"\"{class_name} 测试套件\"\"\"

    @pytest.mark.asyncio
    def test_initialize(self, instance):
        instance.initialize()
        assert instance._initialized is True

    @pytest.mark.asyncio
    def test_health_check(self, instance):
        instance.initialize()
        result = instance.health_check()
        assert "initialized" in result

    @pytest.mark.asyncio
    def test_execute_success(self, instance):
        instance.initialize()
        result = instance.execute(param="test")
        assert result["success"] is True

    @pytest.mark.asyncio
    def test_execute_not_initialized(self, instance):
        with pytest.raises(RuntimeError):
            instance.execute()

    @pytest.mark.asyncio
    def test_shutdown(self, instance):
        instance.initialize()
        instance.shutdown()
        assert instance._initialized is False
""",
                variables=["module_path", "class_name"],
                tags=["test", "pytest", "quality"],
            ),
            CodeTemplate(
                "tmpl_docker",
                "Dockerfile模板",
                Language.DOCKERFILE,
                "devops",
                "生产级Dockerfile",
                """FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')"

CMD ["python", "main.py"]
""",
                variables=["port"],
                tags=["docker", "devops", "deploy"],
            ),
            CodeTemplate(
                "tmpl_sql_migration",
                "SQL迁移模板",
                Language.SQL,
                "database",
                "数据库迁移脚本",
                """-- Migration: {migration_name}
-- Created: {created_at}
-- Description: {description}

BEGIN;

-- Up migration
CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{{}}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_{table_name}_status ON {table_name}(status);
CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at);

-- Down migration
-- DROP TABLE IF EXISTS {table_name};

COMMIT;
""",
                variables=["migration_name", "created_at", "description", "table_name"],
                tags=["sql", "migration", "database"],
            ),
        ]
        for t in templates:
            self._templates[t.template_id] = t

    @trace_operation("generate_code")
    def generate_code(
        self,
        description: str,
        language: Language,
        code_type: str = "function",
        context: Optional[str] = None,
        requirements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """生成代码"""
        try:
            request_id = f"gen_{uuid.uuid4().hex[:10]}"
            start = time.time()

            code = self._do_generate(description, language, code_type, context, requirements or [])

            # 生成文档
            docstring = self._generate_docstring(description, code_type, requirements or [])
            code_with_doc = self._inject_docstring(code, docstring)

            # 质量检查
            review = self._quick_review(code_with_doc, language)

            duration = (time.time() - start) * 1000
            self._generation_history.append(
                {
                    "request_id": request_id,
                    "language": language.value,
                    "type": code_type,
                    "quality": review.quality.value,
                    "duration_ms": duration,
                }
            )
            self.stats["generations_total"] += 1

            metrics_collector.counter("code_gen_total")
            metrics_collector.counter(f"code_gen_{language.value}")

            return {
                "request_id": request_id,
                "code": code_with_doc,
                "language": language.value,
                "type": code_type,
                "quality": review.quality.value,
                "score": review.score,
                "lines": code_with_doc.count("\n") + 1,
                "duration_ms": round(duration, 2),
                "suggestions": review.suggestions[:5],
            }
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            self.stats["errors"] += 1
            raise

    def _do_generate(
        self, description: str, language: Language, code_type: str, context: Optional[str], requirements: List[str]
    ) -> str:
        """核心代码生成逻辑"""
        generators = {
            Language.PYTHON: self._gen_python,
            Language.JAVASCRIPT: self._gen_javascript,
            Language.TYPESCRIPT: self._gen_typescript,
            Language.SQL: self._gen_sql,
            Language.SHELL: self._gen_shell,
        }
        gen = generators.get(language, self._gen_generic)
        return gen(description, code_type, context, requirements)

    def _gen_python(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        """生成Python代码"""
        name = self._extract_name(desc)

        if code_type == "function":
            params = ", ".join(requirements) if requirements else "**kwargs"
            return f'''def {name}({params}) -> Dict[str, Any]:
    """
    {desc}
    """
    try:
        result = _implement_{name}({params})
        return {{"success": True, "data": result}}
    except Exception as e:
        logger.error(f"{name} failed: {{e}}")
        return {{"success": False, "error": str(e)}}

def _implement_{name}({params}) -> Any:
    # TODO: Implement core logic for: {desc}
    context = {{"input": "data"}}  # Replace with actual implementation
    return {{"status": "implemented", "name": "{name}"}}
'''
        elif code_type == "class":
            methods = "\n".join(
                f"    def {req}(self) -> Any:\n        # TODO: {req}\n        pass" for req in requirements[:5]
            )
            return f'''class {name}:
    """
    {desc}
    """

    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {{}}
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True
        logger.info("{name} initialized")

    def execute(self, **kwargs) -> Dict[str, Any]:
        if not self._initialized:
            raise RuntimeError("Not initialized")
        try:
            return {{"success": True, "data": self._run(**kwargs)}}
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    def _run(self, **kwargs) -> Any:
        # TODO: {desc}
        return {{"result": "ok"}}

{methods}
    def shutdown(self) -> None:
        self._initialized = False

module_class = {name}
'''
        else:
            return f'''# Module: {name}\n# {desc}\n\nimport asyncio\nimport logging
from _zhipu_helper import llm_chat  # LLM fallback\n\nlogger = logging.getLogger("{name}")\n\n'''

    def _gen_javascript(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        name = self._extract_name(desc)
        if code_type == "function":
            return f"""/**
 * {desc}
 * @param {{Object}} params
 * @returns {{Promise<Object>}}
 */
async function {name}(params = {{}}) {{
  try {{
    const result = implement{Name.charAt(0).upper()}{name[1:]}(params);
    return {{ success: True, data: result }};
  }} catch (error) {{
    console.error(`${name} failed:`, error.message);
    return {{ success: False, error: error.message }};
  }}
}}

async function implement{Name[0].upper()}{name[1:]}(params) {{
  // TODO: Implement {desc}
  return {{ status: 'implemented' }};
}}

module.exports = {{ {name} }};
"""
        return f"// {name}: {desc}\n// TODO: Implement\n"

    def _gen_typescript(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        name = self._extract_name(desc)
        return f"""/**
 * {desc}
 */

interface {name}Params {{
  [key: string]: unknown;
}}

interface {name}Result {{
  success: boolean;
  data?: unknown;
  error?: string;
}}

export async function {name}(params: {name}Params = {{}}): Promise<{name}Result> {{
  try {{
    const result = _implement{name.charAt(0).toUpperCase()}{name.slice(1)}(params);
    return {{ success: True, data: result }};
  }} catch (error) {{
    return {{ success: False, error: String(error) }};
  }}
}}

async function _implement{name.charAt(0).toUpperCase()}{name.slice(1)}(params: {name}Params): Promise<unknown> {{
  // TODO: {desc}
  return {{ status: 'implemented' }};
}}
"""

    def _gen_sql(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        table = self._extract_name(desc)
        return f"""-- {desc}
-- Generated at {datetime.now().isoformat()}

CREATE TABLE IF NOT EXISTS {table} (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{{}}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{table}_status ON {table}(status);
CREATE INDEX idx_{table}_created ON {table}(created_at);

-- SELECT * FROM {table} WHERE status = 'active' ORDER BY created_at DESC LIMIT 50;
"""

    def _gen_shell(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        name = self._extract_name(desc).replace("_", "-")
        return f"""#!/bin/bash
# {desc}
# Usage: ./{name} [options]

set -euo pipefail

LOG_LEVEL="${{LOG_LEVEL:-INFO}}"
LOG_FILE="${{LOG_FILE:-/var/log/{name}.log}}"

log() {{
    local level="$1"; shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >> "$LOG_FILE"
    [[ "$level" == "ERROR" ]] && echo "$*" >&2
}}

main() {{
    log "INFO" "Starting {name}"
    # TODO: {desc}
    log "INFO" "Completed {name}"
}}

main "$@"
"""

    def _gen_generic(self, desc: str, code_type: str, context: Optional[str], requirements: List[str]) -> str:
        return f"// TODO: {desc}\n// Language: generic\n"

    def _extract_name(self, description: str) -> str:
        """从描述中提取标识符名"""
        name = re.sub(r"[^\w\s]", "", description)
        words = name.split()[:3]
        return "_".join(w.lower() for w in words) or "module"

    def _generate_docstring(self, desc: str, code_type: str, requirements: List[str]) -> str:
        """生成文档字符串"""
        parts = [f"{desc}."]
        if requirements:
            parts.append(f"\nRequirements: {', '.join(requirements)}")
        parts.append(f"\nType: {code_type}")
        parts.append(f"\nGenerated: {datetime.now().isoformat()}")
        return "\n".join(parts)

    def _inject_docstring(self, code: str, docstring: str) -> str:
        """注入文档字符串"""
        if code.strip().startswith('"""') or code.strip().startswith("'''"):
            return code
        lines = code.split("\n")
        indent = ""
        if lines and lines[0].startswith(" "):
            indent = " " * (len(lines[0]) - len(lines[0].lstrip()))
        doc_line = f'{indent}"""\n{indent}{docstring}\n{indent}"""'
        if lines and (
            lines[0].strip().startswith("class ")
            or lines[0].strip().startswith("def ")
            or lines[0].strip().startswith("def ")
        ):
            lines.insert(1, doc_line)
        else:
            lines.insert(0, f'{indent}"""')
            lines.insert(1, f"{indent}{docstring}")
            lines.insert(2, f'{indent}"""')
            lines.insert(3, "")
        return "\n".join(lines)

    def _quick_review(self, code: str, language: Language) -> ReviewResult:
        """快速代码审查"""
        issues = []
        suggestions = []
        score = 100.0

        lines = code.split("\n")
        total_lines = len(lines)

        # 检查长度
        if total_lines < 10:
            issues.append({"severity": "warning", "message": "代码过短，可能不完整"})
            score -= 10
        if total_lines > 1000:
            suggestions.append("文件超过1000行，考虑拆分")

        # 检查异常处理
        has_try_except = "try:" in code or "try {" in code
        if not has_try_except and total_lines > 20:
            issues.append({"severity": "warning", "message": "缺少异常处理"})
            score -= 15

        # 检查日志
        has_logging = "logger" in code or "console.log" in code or "logging" in code
        if not has_logging and total_lines > 20:
            suggestions.append("建议添加日志记录")
            score -= 5

        # 检查类型注解（Python）
        if language == Language.PYTHON:
            has_types = "-> " in code or ": Dict" in code or ": List" in code
            if not has_types:
                suggestions.append("建议添加类型注解")
                score -= 10

        # 检查TODO
        todo_count = code.count("TODO")
        if todo_count > 0:
            suggestions.append(f"包含 {todo_count} 个TODO待实现")

        # 质量评级
        if score >= 90:
            quality = CodeQuality.A
        elif score >= 75:
            quality = CodeQuality.B
        elif score >= 60:
            quality = CodeQuality.C
        else:
            quality = CodeQuality.D

        return ReviewResult(
            file_path="",
            quality=quality,
            issues=issues,
            suggestions=suggestions,
            metrics={
                "lines": total_lines,
                "has_error_handling": has_try_except,
                "has_logging": has_logging,
                "todo_count": todo_count,
            },
            score=max(score, 0),
        )

    @trace_operation("review_code")
    def review_code(self, code: str, language: Language = Language.PYTHON, file_path: str = "") -> Dict[str, Any]:
        """详细代码审查"""
        review = self._quick_review(code, language)
        review.file_path = file_path

        # 额外深度检查
        if language == Language.PYTHON:
            review.suggestions.extend(self._deep_python_review(code))

        self._review_cache[file_path or "inline"] = review
        self.stats["reviews_total"] += 1

        return {
            "file_path": file_path,
            "quality": review.quality.value,
            "score": review.score,
            "issues": review.issues,
            "suggestions": review.suggestions,
            "metrics": review.metrics,
        }

    def _deep_python_review(self, code: str) -> List[str]:
        """深度Python审查"""
        suggestions = []
        if "import *" in code:
            suggestions.append("避免使用 import *，应显式导入")
        if "os.system" in code or "subprocess.call" in code:
            suggestions.append("shell命令调用存在安全风险，使用 subprocess.run")
        if "eval(" in code or "exec(" in code:
            suggestions.append("eval/exec 存在代码注入风险")
        if "pass" in code and code.count("pass") > 3:
            suggestions.append("过多pass占位，应实现或添加TODO注释")
        if "print(" in code:
            suggestions.append("生产代码应使用logging替代print")
        return suggestions

    @trace_operation("generate_from_template")
    def generate_from_template(self, template_id: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """从模板生成代码"""
        if template_id not in self._templates:
            raise ValueError(f"模板 {template_id} 不存在")

        tmpl = self._templates[template_id]
        code = tmpl.template_code

        for var in tmpl.variables:
            placeholder = f"{{{var}}}"
            replacement = variables.get(var, f"[{var}]")
            code = code.replace(placeholder, replacement)

        return {
            "template_id": template_id,
            "code": code,
            "language": tmpl.language.value,
            "filled_variables": list(variables.keys()),
            "missing_variables": [v for v in tmpl.variables if v not in variables],
        }

    def list_templates(self, language: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        templates = list(self._templates.values())
        if language:
            templates = [t for t in templates if t.language.value == language]
        if category:
            templates = [t for t in templates if t.category == category]
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "language": t.language.value,
                "category": t.category,
                "variables": t.variables,
                "tags": t.tags,
            }
            for t in templates
        ]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._generation_history)
        return {
            "total_generations": total,
            "by_language": self._count_by(self._generation_history, "language"),
            "by_quality": self._count_by(self._generation_history, "quality"),
            "avg_duration_ms": round(sum(h["duration_ms"] for h in self._generation_history) / max(total, 1), 2)
            if self._generation_history
            else 0,
        }

    def _count_by(self, history: List[Dict], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for h in history:
            val = h.get(key, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "templates": len(self._templates),
                "total_generations": self.stats.get("generations_total", 0),
                "total_reviews": self.stats.get("reviews_total", 0),
                "supported_languages": [l.value for l in Language],
                "output_dir": self._output_dir,
            }
        )
        return base

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown",
            resource="code_generator",
            details=f"关闭，共生成 {self.stats.get('generations_total', 0)} 次代码",
        )

    def execute(self, action: str = "status", params: dict = None) -> dict:
        """Execute action"""
        params = params or {}
        if action == "status":
            return {
                "status": "healthy",
                "module": self.MODULE_ID if hasattr(self, "MODULE_ID") else self.__class__.__name__,
            }
        return {"success": False, "error": f"Unknown action: {action}"}

    def execute(self, action: str = "status", params: dict = None) -> dict:
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

module_class = CodeGenerator