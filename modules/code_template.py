"""
AUTO-EVO-AI V0.1 — 代码模板管理器
Grade: A (生产级) | Category: 开发工具
职责：代码模板管理、项目脚手架、代码片段库、模板变量渲染
"""

__module_meta__ = {
    "id": "code-template",
    "name": "Code Template",
    "version": "1.0.0",
    "group": "developer",
    "inputs": [
        {"name": "content", "type": "string", "required": True, "description": ""},
        {"name": "variables", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
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
    "description": "AUTO-EVO-AI V0.1 — 代码模板管理器 Grade: A (生产级) | Category: 开发工具",
}

import os
import json
import time
import uuid
import re
import shutil
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

@dataclass
class TemplateVariable:
    """模板变量定义"""

    name: str
    var_type: str = "string"  # string, int, bool, list, choice
    default: Any = ""
    description: str = ""
    required: bool = False
    choices: List[str] = field(default_factory=list)
    pattern: str = ""  # 正则验证

@dataclass
class CodeTemplate:
    """代码模板"""

    template_id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    language: str = "python"
    content: str = ""
    variables: List[TemplateVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    usage_count: int = 0
    author: str = "system"

@dataclass
class GeneratedProject:
    """生成的项目"""

    project_id: str = ""
    template_id: str = ""
    name: str = ""
    path: str = ""
    files: List[str] = field(default_factory=list)
    variables_used: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

@dataclass
class CodeSnippet:
    """代码片段"""

    snippet_id: str = ""
    name: str = ""
    description: str = ""
    language: str = "python"
    code: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    usage_count: int = 0

class CodeTemplateManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """代码模板管理器 - 生产级实现"""

    MODULE_ID = "code_template"
    MODULE_NAME = "code_template"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "code_template",
                "version": "7.0.0",
                "description": "代码模板管理器，支持脚手架生成、代码片段库、模板变量渲染",
            }
        )
        self._templates: Dict[str, CodeTemplate] = {}
        self._snippets: Dict[str, CodeSnippet] = {}
        self._projects: Dict[str, GeneratedProject] = {}
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._load_builtin_templates()
        self._load_builtin_snippets()
        self._initialized = True

    def _load_builtin_templates(self):
        """加载内置模板"""
        builtins = [
            {
                "template_id": "tpl_python_module",
                "name": "Python模块模板",
                "description": "标准Python模块骨架，含类定义、方法、文档字符串",
                "category": "python",
                "language": "python",
                "tags": ["python", "module", "class"],
                "content": '''"""
{{description}}
Author: {{author}}
Created: {{date}}
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class {{class_name}}:
    """{{description}}"""

    def __init__(self):
        self._initialized = False

    def initialize(self) -> None:
        """初始化"""
        self._initialized = True
        logger.info("{{class_name}} 初始化完成")

    async def execute(self, action: 

str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行操作"""
        _ = self.trace("execute")
        metrics_collector.counter("code_template_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        return {"success": True, "result": {"action": action}}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "module": "{{class_name}}"}

    def shutdown(self) -> None:
        self._initialized = False
''',
                "variables": [
                    TemplateVariable(name="class_name", var_type="string", required=True, description="类名"),
                    TemplateVariable(name="description", var_type="string", default="模块描述", description="模块描述"),
                    TemplateVariable(name="author", var_type="string", default="BGOS", description="作者"),
                    TemplateVariable(name="date", var_type="string", default="{{_now}}", description="创建日期"),
                ],
            },
            {
                "template_id": "tpl_api_endpoint",
                "name": "API端点模板",
                "description": "RESTful API端点，含请求验证、错误处理、日志",
                "category": "api",
                "language": "python",
                "tags": ["api", "rest", "endpoint"],
                "content": '''"""{{description}} API端点"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/{{version}}/{{resource}}", tags=["{{resource}}"])

class {{resource|capitalize}}Create(BaseModel):
    name: str
    description: Optional[str] = None

class {{resource|capitalize}}Response(BaseModel):
    id: str
    name: str
    created_at: str

@router.post("/", response_model={{resource|capitalize}}Response, status_code=201)
def create_{{resource}}(data: {{resource|capitalize}}Create):
    """创建{{resource}}"""
    return {"id": "{{_uuid}}", "name": data.name, "created_at": "{{_now}}"}

@router.get("/", response_model=List[{{resource|capitalize}}Response])
def list_{{resource}}s(skip: int = 0, limit: int = 20):
    """获取{{resource}}列表"""
    return []

@router.get("/{item_id}", response_model={{resource|capitalize}}Response)
def get_{{resource}}(item_id: str):
    """获取单个{{resource}}"""
    return {"id": item_id, "name": "", "created_at": "{{_now}}"}
''',
                "variables": [
                    TemplateVariable(name="resource", var_type="string", required=True, description="资源名称"),
                    TemplateVariable(name="version", var_type="string", default="v1", description="API版本"),
                    TemplateVariable(name="description", var_type="string", default="", description="描述"),
                ],
            },
            {
                "template_id": "tpl_dockerfile",
                "name": "Dockerfile模板",
                "description": "多阶段Docker构建模板",
                "category": "docker",
                "language": "dockerfile",
                "tags": ["docker", "container", "devops"],
                "content": """# {{description}}
FROM {{base_image}} AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM {{runtime_image}}
WORKDIR /app
COPY --from=builder /usr/local/lib/python{{python_version}}/site-packages /usr/local/lib/python{{python_version}}/site-packages
COPY . .
EXPOSE {{port}}
CMD ["{{cmd}}"]
""",
                "variables": [
                    TemplateVariable(
                        name="base_image", var_type="string", default="python:3.12-slim", description="基础镜像"
                    ),
                    TemplateVariable(
                        name="runtime_image", var_type="string", default="python:3.12-slim", description="运行镜像"
                    ),
                    TemplateVariable(
                        name="python_version", var_type="string", default="3.12", description="Python版本"
                    ),
                    TemplateVariable(name="port", var_type="string", default="8000", description="端口"),
                    TemplateVariable(name="cmd", var_type="string", default="python main.py", description="启动命令"),
                ],
            },
            {
                "template_id": "tpl_test_suite",
                "name": "测试套件模板",
                "description": "pytest测试套件，含fixtures、参数化测试、mock",
                "category": "testing",
                "language": "python",
                "tags": ["test", "pytest", "testing"],
                "content": '''"""{{description}}"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

@pytest.fixture
def sample_data():
    return {"key": "value"}

class Test{{class_name}}:
    """{{class_name}} 测试套件"""

    @pytest.mark.asyncio
    def test_initialize(self):
        """测试初始化"""
        assert True

    @pytest.mark.asyncio
    def test_execute(self, sample_data):
        """测试执行"""
        assert "key" in sample_data

    @pytest.mark.parametrize("input_val,expected", [
        (1, 1),
        (10, 10),
        (100, 100),
    ])
    def test_parameterized(self, input_val, expected):
        """参数化测试"""
        assert input_val == expected

    @pytest.mark.asyncio
    def test_error_handling(self):
        """测试错误处理"""
        with pytest.raises(ValueError):
            raise ValueError("test error")
''',
                "variables": [
                    TemplateVariable(name="class_name", var_type="string", required=True, description="测试目标类名"),
                    TemplateVariable(name="description", var_type="string", default="测试套件", description="描述"),
                ],
            },
        ]

        for tpl_data in builtins:
            tpl = CodeTemplate(
                template_id=tpl_data["template_id"],
                name=tpl_data["name"],
                description=tpl_data["description"],
                category=tpl_data.get("category", "general"),
                language=tpl_data.get("language", "python"),
                content=tpl_data["content"],
                variables=tpl_data.get("variables", []),
                tags=tpl_data.get("tags", []),
                created_at=time.time(),
                updated_at=time.time(),
            )
            self._templates[tpl.template_id] = tpl

    def _load_builtin_snippets(self):
        """加载内置代码片段"""
        snippets = [
            {
                "snippet_id": "snip_retry",
                "name": "重试装饰器",
                "description": "指数退避重试装饰器",
                "language": "python",
                "tags": ["retry", "decorator", "resilience"],
                "code": '''import time
import functools
import logging

logger = logging.getLogger(__name__)

def retry(max_retries=3, base_delay=1.0, max_delay=30.0, backoff=2.0):
    """指数退避重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    delay = min(base_delay * (backoff ** attempt), max_delay)
                    logger.warning(f"重试 {attempt+1}/{max_retries}: {e}, 等待 {delay}s")
                    import time; time.sleep(delay)
            raise last_error
        return wrapper
    return decorator
''',
            },
            {
                "snippet_id": "snip_singleton",
                "name": "单例模式",
                "description": "线程安全单例模式",
                "language": "python",
                "tags": ["pattern", "singleton", "design"],
                "code": '''import threading

class Singleton(type):
    """线程安全单例元类"""
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class MyClass(metaclass=Singleton):
    pass
''',
            },
            {
                "snippet_id": "snip_rate_limit",
                "name": "令牌桶限流",
                "description": "令牌桶限流器",
                "language": "python",
                "tags": ["rate_limit", "token_bucket", "throttle"],
                "code": '''import time
import threading

class TokenBucket:
    """令牌桶限流器"""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self):
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now
''',
            },
        ]

        for s in snippets:
            snippet = CodeSnippet(
                snippet_id=s["snippet_id"],
                name=s["name"],
                description=s["description"],
                language=s.get("language", "python"),
                code=s["code"],
                tags=s.get("tags", []),
                created_at=time.time(),
            )
            self._snippets[snippet.snippet_id] = snippet

    def _render_template(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染模板变量，支持 {{var}} 语法"""
        result = content
        # 内置变量
        builtins = {
            "_now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_date": datetime.now().strftime("%Y-%m-%d"),
            "_uuid": str(uuid.uuid4())[:8],
            "_timestamp": str(int(time.time())),
        }
        all_vars = {**builtins, **variables}

        # 处理 {{_now}} 等内置变量默认值
        for k, v in all_vars.items():
            result = result.replace("{{" + k + "}}", str(v))

        # 处理过滤器: {{var|filter}}
        def apply_filter(match):
            expr = match.group(1)
            if "|" in expr:
                var_name, filt = expr.split("|", 1)
                filt = filt.strip()
                val = all_vars.get(var_name.strip(), "")
                if filt == "capitalize":
                    return str(val).capitalize()
                elif filt == "upper":
                    return str(val).upper()
                elif filt == "lower":
                    return str(val).lower()
                elif filt == "title":
                    return str(val).title()
                return str(val)
            return str(all_vars.get(expr.strip(), ""))

        result = re.sub(r"\{\{(.+?)\}\}", apply_filter, result)
        return result

    def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一execute入口"""
        params = params or {}
        try:
            if action == "list_templates":
                category = params.get("category")
                language = params.get("language")
                results = list(self._templates.values())
                if category:
                    results = [t for t in results if t.category == category]
                if language:
                    results = [t for t in results if t.language == language]
                return {
                    "success": True,
                    "result": [
                        {
                            "template_id": t.template_id,
                            "name": t.name,
                            "description": t.description,
                            "category": t.category,
                            "language": t.language,
                            "tags": t.tags,
                            "variables": len(t.variables),
                            "usage_count": t.usage_count,
                        }
                        for t in results
                    ],
                }

            elif action == "get_template":
                tid = params.get("template_id", "")
                tpl = self._templates.get(tid)
                if not tpl:
                    return {"success": False, "error": f"模板 {tid} 不存在"}
                return {
                    "success": True,
                    "result": {
                        "template_id": tpl.template_id,
                        "name": tpl.name,
                        "description": tpl.description,
                        "category": tpl.category,
                        "language": tpl.language,
                        "content": tpl.content,
                        "variables": [
                            {
                                "name": v.name,
                                "type": v.var_type,
                                "default": v.default,
                                "required": v.required,
                                "choices": v.choices,
                                "description": v.description,
                            }
                            for v in tpl.variables
                        ],
                        "tags": tpl.tags,
                        "usage_count": tpl.usage_count,
                    },
                }

            elif action == "create_template":
                tpl_id = params.get("template_id", f"tpl_{uuid.uuid4().hex[:8]}")
                variables = []
                for v in params.get("variables", []):
                    variables.append(
                        TemplateVariable(
                            name=v.get("name", ""),
                            var_type=v.get("type", "string"),
                            default=v.get("default", ""),
                            description=v.get("description", ""),
                            required=v.get("required", False),
                            choices=v.get("choices", []),
                        )
                    )
                tpl = CodeTemplate(
                    template_id=tpl_id,
                    name=params.get("name", ""),
                    description=params.get("description", ""),
                    category=params.get("category", "general"),
                    language=params.get("language", "python"),
                    content=params.get("content", ""),
                    variables=variables,
                    tags=params.get("tags", []),
                    created_at=time.time(),
                    updated_at=time.time(),
                    author=params.get("author", "user"),
                )
                self._templates[tpl_id] = tpl
                return {"success": True, "result": {"template_id": tpl_id}}

            elif action == "render":
                tid = params.get("template_id", "")
                tpl = self._templates.get(tid)
                if not tpl:
                    return {"success": False, "error": f"模板 {tid} 不存在"}
                variables = params.get("variables", {})
                # 验证必填变量
                missing = [v.name for v in tpl.variables if v.required and v.name not in variables and not v.default]
                if missing:
                    return {"success": False, "error": f"缺少必填变量: {', '.join(missing)}"}
                rendered = self._render_template(tpl.content, variables)
                tpl.usage_count += 1
                return {"success": True, "result": {"rendered": rendered, "variables_used": variables}}

            elif action == "delete_template":
                tid = params.get("template_id", "")
                if tid not in self._templates:
                    return {"success": False, "error": f"模板 {tid} 不存在"}
                del self._templates[tid]
                return {"success": True, "result": {"deleted": tid}}

            elif action == "list_snippets":
                lang = params.get("language")
                results = list(self._snippets.values())
                if lang:
                    results = [s for s in results if s.language == lang]
                return {
                    "success": True,
                    "result": [
                        {
                            "snippet_id": s.snippet_id,
                            "name": s.name,
                            "description": s.description,
                            "language": s.language,
                            "tags": s.tags,
                            "usage_count": s.usage_count,
                        }
                        for s in results
                    ],
                }

            elif action == "get_snippet":
                sid = params.get("snippet_id", "")
                snip = self._snippets.get(sid)
                if not snip:
                    return {"success": False, "error": f"代码片段 {sid} 不存在"}
                snip.usage_count += 1
                return {
                    "success": True,
                    "result": {
                        "snippet_id": snip.snippet_id,
                        "name": snip.name,
                        "description": snip.description,
                        "language": snip.language,
                        "code": snip.code,
                        "tags": snip.tags,
                    },
                }

            elif action == "create_snippet":
                sid = params.get("snippet_id", f"snip_{uuid.uuid4().hex[:8]}")
                snip = CodeSnippet(
                    snippet_id=sid,
                    name=params.get("name", ""),
                    description=params.get("description", ""),
                    language=params.get("language", "python"),
                    code=params.get("code", ""),
                    tags=params.get("tags", []),
                    created_at=time.time(),
                )
                self._snippets[sid] = snip
                return {"success": True, "result": {"snippet_id": sid}}

            elif action == "search":
                query = params.get("query", "").lower()
                target = params.get("target", "all")  # all, templates, snippets
                results = []
                if target in ("all", "templates"):
                    for t in self._templates.values():
                        if (
                            query in t.name.lower()
                            or query in t.description.lower()
                            or query in " ".join(t.tags).lower()
                        ):
                            results.append(
                                {"type": "template", "id": t.template_id, "name": t.name, "description": t.description}
                            )
                if target in ("all", "snippets"):
                    for s in self._snippets.values():
                        if (
                            query in s.name.lower()
                            or query in s.description.lower()
                            or query in " ".join(s.tags).lower()
                        ):
                            results.append(
                                {"type": "snippet", "id": s.snippet_id, "name": s.name, "description": s.description}
                            )
                return {"success": True, "result": results}

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "templates_total": len(self._templates),
                        "snippets_total": len(self._snippets),
                        "categories": list(set(t.category for t in self._templates.values())),
                        "languages": list(set(t.language for t in self._templates.values())),
                        "total_usage": sum(t.usage_count for t in self._templates.values())
                        + sum(s.usage_count for s in self._snippets.values()),
                    },
                }

            elif action == "list_categories":
                cats = defaultdict(list)
                for t in self._templates.values():
                    cats[t.category].append({"id": t.template_id, "name": t.name})
                return {"success": True, "result": dict(cats)}

            else:
                return {"success": False, "error": f"未知操作: {action}"}

        except Exception as e:
            logger.error(f"[CodeTemplate] execute异常: {action}, {e}")
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
                "templates": len(self._templates),
                "snippets": len(self._snippets),
            }
        )
        return base

    def shutdown(self) -> None:
        self._initialized = False
        logger.info(f"关闭代码模板管理器，模板数: {len(self._templates)}")

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

module_class = CodeTemplateManager
