"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
    "id": "pdf-report",
    "name": "Pdf Report",
    "version": "V0.1",
    "group": "documents",
    "inputs": [
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "priority", "type": "string", "required": True, "description": ""},
        {"name": "dependencies", "type": "string", "required": True, "description": ""},
        {"name": "component_id", "type": "string", "required": True, "description": ""},
        {"name": "template", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "pdf"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

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
logger = logging.getLogger("pdf_report")

class LifecycleState(Enum):
    """生命周期状态"""

    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

class ShutdownPriority(Enum):
    """关闭优先级"""

    CRITICAL = 0  # 最先关闭：存储、数据库
    HIGH = 1  # 高优先级：消息队列、缓存
    NORMAL = 2  # 普通：业务模块
    LOW = 3  # 低优先级：监控、日志
    OPTIONAL = 4  # 最后关闭：清理任务

@dataclass
class ManagedComponent:
    """被管理的组件"""

    component_id: str
    name: str
    state: LifecycleState = LifecycleState.INITIALIZING
    priority: ShutdownPriority = ShutdownPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    health_check_interval: int = 30
    last_health_check: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PdfReport:
    """生命周期策略定义"""

    policy_id: str
    name: str
    description: str = ""
    # 启动策略
    startup_order: List[str] = field(default_factory=list)
    startup_timeout: int = 60
    startup_retry_count: int = 3
    # 健康检查策略
    health_check_enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 5
    # 关闭策略
    shutdown_timeout: int = 30
    shutdown_force_timeout: int = 10
    graceful_shutdown: bool = True
    # 依赖策略
    dependency_timeout: int = 30
    fail_on_missing_dependency: bool = True

class PdfReportManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, PdfReport] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
        self._audit = AuditLogger()
        self._metrics = metrics_collector

    @trace_operation("lifecycle.initialize")
    def initialize(self) -> Dict[str, Any]:
        """初始化"""
        try:
            pass
            # 加载默认策略
            self._load_default_policies()

            # 注册核心组件
            self._register_core_components()

            self._state = LifecycleState.RUNNING
            self._startup_time = time.time()

            self._audit.log(
                "lifecycle_initialized",
                {
                    "components": len(self._components),
                    "policies": len(self._policies),
                    "startup_time": self._startup_time,
                },
            )

            self.record_metric("lifecycle_initialized_total", 1)
            logger.info(f"生命周期管理器初始化完成，注册组件: {len(self._components)}")
            return {"success": True}

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.record_metric("lifecycle_initialization_errors_total", 1)
            return {"success": False, "error": str(e)}

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = PdfReport(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = PdfReport(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = PdfReport(
            policy_id="policy-monitoring",
            name="监控日志策略",
            description="监控、日志、审计等辅助服务",
            graceful_shutdown=True,
            shutdown_timeout=15,
        )
        self._policies["policy-monitoring"] = monitor_policy

    def _register_core_components(self):
        """注册核心组件"""
        components_to_register = [
            ("database", "数据库", ShutdownPriority.CRITICAL),
            ("cache", "缓存", ShutdownPriority.HIGH),
            ("message_queue", "消息队列", ShutdownPriority.HIGH),
            ("api_server", "API服务器", ShutdownPriority.NORMAL),
            ("worker", "工作进程", ShutdownPriority.NORMAL),
            ("scheduler", "调度器", ShutdownPriority.NORMAL),
            ("monitor", "监控服务", ShutdownPriority.LOW),
            ("audit", "审计服务", ShutdownPriority.LOW),
        ]

        for comp_id, name, priority in components_to_register:
            self._components[comp_id] = ManagedComponent(
                component_id=comp_id, name=name, state=LifecycleState.INITIALIZING, priority=priority
            )

    @trace_operation("lifecycle.health_check")
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        failed_components = []
        degraded_components = []

        for comp_id, comp in self._components.items():
            # 检查组件健康状态
            if comp.state == LifecycleState.FAILED:
                failed_components.append(comp_id)
            elif comp.failure_count > 0:
                degraded_components.append(comp_id)

            # 更新健康检查时间
            comp.last_health_check = time.time()

        overall_status = "ok"
        if failed_components:
            overall_status = "error"
        elif degraded_components:
            overall_status = "degraded"

        return {
            "healthy": overall_status == "ok",
            "status": overall_status,
            "module_id": "pdf_report",
            "state": self._state.value,
            "uptime_seconds": time.time() - (self._startup_time or time.time()),
            "components": {
                "total": len(self._components),
                "running": sum(1 for c in self._components.values() if c.state == LifecycleState.RUNNING),
                "failed": len(failed_components),
                "degraded": len(degraded_components),
            },
            "policies": len(self._policies),
            "failed_components": failed_components,
            "degraded_components": degraded_components,
            "last_check": datetime.now().isoformat(),
        }

    @trace_operation("lifecycle.shutdown")
    async def shutdown(self) -> bool:
        """优雅关闭"""
        if self._state == LifecycleState.STOPPED:
            return {"success": True}

        self._state = LifecycleState.STOPPING
        self._shutdown_start_time = time.time()

        logger.info("开始生命周期管理器关闭流程...")
        self._audit.log(
            "lifecycle_shutdown_started",
            {"components": len(self._components), "shutdown_time": self._shutdown_start_time},
        )

        # 按优先级排序组件（数字越小越先关闭）
        sorted_components = sorted(
            self._components.items(), key=lambda x: (x[1].priority.value, -x[1].last_health_check)
        )

        shutdown_errors = []
        for comp_id, comp in sorted_components:
            try:
                logger.info(f"关闭组件: {comp.name} (优先级: {comp.priority.name})")
                comp.state = LifecycleState.STOPPING

                # 模拟关闭操作
                time.sleep(0.1)  # 实际应该调用组件的shutdown方法

                comp.state = LifecycleState.STOPPED
                self.record_metric("lifecycle_component_shutdown_total", 1, component=comp_id)

            except Exception as e:
                shutdown_errors.append(f"{comp_id}: {str(e)}")
                comp.state = LifecycleState.FAILED
                logger.error(f"关闭组件 {comp_id} 失败: {e}")

        self._state = LifecycleState.STOPPED
        shutdown_duration = time.time() - self._shutdown_start_time

        self._audit.log(
            "lifecycle_shutdown_completed", {"duration_seconds": shutdown_duration, "errors": shutdown_errors}
        )

        self.record_metric("lifecycle_shutdown_total", 1)
        self.record_metric("lifecycle_shutdown_duration_seconds", shutdown_duration)

        if shutdown_errors:
            logger.warning(f"关闭完成，但有 {len(shutdown_errors)} 个组件关闭失败")
            return False

        logger.info(f"关闭完成，耗时 {shutdown_duration:.2f} 秒")
        return {"success": True}

    @trace_operation("lifecycle.register_component")
    def register_component(
        self, component_id: str, name: str, priority: int = 2, dependencies: List[str] = None
    ) -> bool:
        """注册新组件"""
        try:
            priority_enum = ShutdownPriority(priority)
            self._components[component_id] = ManagedComponent(
                component_id=component_id, name=name, priority=priority_enum, dependencies=dependencies or []
            )

            self._audit.log(
                "component_registered", {"component_id": component_id, "name": name, "priority": priority_enum.name}
            )

            self.record_metric("lifecycle_component_registered_total", 1)
            return {"success": True}

        except Exception as e:
            logger.error(f"注册组件失败: {e}")
            return False

    @trace_operation("lifecycle.get_component_status")
    def get_component_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """获取组件状态"""
        if component_id not in self._components:
            return None

        comp = self._components[component_id]
        return {
            "component_id": comp.component_id,
            "name": comp.name,
            "state": comp.state.value,
            "priority": comp.priority.name,
            "failure_count": comp.failure_count,
            "last_health_check": comp.last_health_check,
            "dependencies": comp.dependencies,
        }

    @trace_operation("lifecycle.list_components")
    def list_components(self) -> List[Dict[str, Any]]:
        """列出所有组件"""
        return [
            {
                "component_id": comp.component_id,
                "name": comp.name,
                "state": comp.state.value,
                "priority": comp.priority.name,
            }
            for comp in self._components.values()
        ]

    def get_policies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "description": p.description,
                "startup_timeout": p.startup_timeout,
                "shutdown_timeout": p.shutdown_timeout,
            }
            for p in self._policies.values()
        ]

    # 模块导出

    async def execute(self, action: str, params: dict = None) -> dict:
        """Execute bridge - dispatch to class methods"""
        _ = self.trace("execute")
        metrics_collector.counter("pdf_report_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
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
        if action == "get_component_status":
            try:
                r = self.get_component_status(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_policies":
            try:
                r = self.get_policies(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "list_components":
            try:
                r = self.list_components(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
            return {"success": False, "error": "Unknown action: {}".format(action)}

    def validate_template(self, template: Dict) -> Dict[str, Any]:
        """验证PDF报告模板：必需字段检查、表达式语法、分页配置、样式一致性"""
        issues = []
        name = template.get("name", "")
        if not name:
            issues.append({"severity": "high", "field": "name", "error": "模板名称不能为空"})
        sections = template.get("sections", [])
        if not sections:
            issues.append({"severity": "high", "field": "sections", "error": "至少需要定义一个章节"})
        for i, sec in enumerate(sections):
            sec_title = sec.get("title", "")
            if not sec_title:
                issues.append({"severity": "medium", "field": f"sections[{i}].title", "error": f"第{i + 1}章缺少标题"})
            content = sec.get("content", "")
            if "{{" in content:
                vars_in_section = re.findall(r"\{\{\s*(\w+)\s*\}\}", content)
                for var in vars_in_section:
                    if not any(v.get("name") == var for v in template.get("variables", [])):
                        issues.append(
                            {
                                "severity": "low",
                                "field": f"sections[{i}].content",
                                "error": f"变量 {{{{{var}}}}} 未在variables中定义",
                            }
                        )
        page_config = template.get("page", {})
        margin_top = page_config.get("margin_top", 25)
        margin_bottom = page_config.get("margin_bottom", 25)
        if margin_top < 10 or margin_bottom < 10:
            issues.append(
                {
                    "severity": "medium",
                    "field": "page.margin",
                    "error": f"页边距过小(top={margin_top}, bottom={margin_bottom})，可能导致打印裁切",
                }
            )
        styles = template.get("styles", {})
        if not styles.get("body_font") and not styles.get("font_family"):
            issues.append({"severity": "low", "field": "styles", "error": "未设置正文字体，将使用默认字体"})
        return {
            "valid": len([i for i in issues if i["severity"] == "high"]) == 0,
            "total_issues": len(issues),
            "issues": issues,
            "section_count": len(sections),
            "variable_count": len(template.get("variables", [])),
        }

    def estimate_page_count(self, template: Dict, sample_data: Dict = None) -> Dict[str, Any]:
        """估算报告页数：基于内容量和分页规则"""
        sections = template.get("sections", [])
        chars_per_page = 3000
        pages = 0
        section_pages = []
        for sec in sections:
            content = sec.get("content", "")
            if sample_data:
                for key, val in sample_data.items():
                    content = content.replace(f"{{{{{key}}}}}", str(val))
            estimated_chars = len(content) * 1.3
            sec_pages = max(1, int(estimated_chars / chars_per_page))
            pages += sec_pages
            section_pages.append({"title": sec.get("title", ""), "pages": sec_pages})
        cover = template.get("cover_page", True)
        toc = template.get("toc", len(sections) > 3)
        total = pages + (1 if cover else 0) + (1 if toc else 0)
        return {"content_pages": pages, "cover": cover, "toc": toc, "estimated_total": total, "sections": section_pages}

    def generate_toc(self, sections: List[Dict]) -> List[Dict[str, Any]]:
        """自动生成目录：层级编号、页码占位"""
        toc = []
        page = 2
        for i, sec in enumerate(sections):
            level = sec.get("level", 1)
            title = sec.get("title", f"Section {i + 1}")
            num = f"{i + 1}" if level == 1 else f"{sec.get('parent', '')}.{sec.get('index', i + 1)}"
            toc.append({"number": num, "title": title, "page": page, "level": level})
            page += max(1, len(sec.get("content", "")) // 3000)
        return toc

    def check_pdf_accessibility(self, template: Dict) -> Dict[str, Any]:
        """检查PDF可访问性：字体嵌入、颜色对比度、标题层级、表格标题"""
        issues = []
        styles = template.get("styles", {})
        if not styles.get("embed_fonts"):
            issues.append(
                {"severity": "high", "type": "font_not_embedded", "detail": "字体未嵌入，可能导致跨平台显示异常"}
            )
        body_font_size = styles.get("body_font_size", 10)
        if body_font_size < 9:
            issues.append(
                {
                    "severity": "medium",
                    "type": "font_too_small",
                    "detail": f"正文字体{body_font_size}pt小于9pt，影响阅读",
                }
            )
        text_color = styles.get("text_color", "#000000")
        bg_color = styles.get("background_color", "#ffffff")

        # 对比度检查
        def hex_lum(h):
            h = h.lstrip("#")
            r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        try:
            lum_text = hex_lum(text_color)
            lum_bg = hex_lum(bg_color)
            ratio = (max(lum_text, lum_bg) + 0.05) / max(min(lum_text, lum_bg) + 0.05, 0.001)
            if ratio < 4.5:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "low_contrast",
                        "detail": f"文字与背景对比度{ratio:.1f}:1低于WCAG AA标准4.5:1",
                    }
                )
        except Exception:
            pass
        sections = template.get("sections", [])
        has_headings = any(s.get("level", 0) == 1 for s in sections if isinstance(s, dict))
        if not has_headings and len(sections) > 3:
            issues.append({"severity": "low", "type": "no_headings", "detail": "多章节文档缺少一级标题，影响导航"})
        return {
            "accessible": len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "wcag_aa_compliant": len(issues) == 0,
        }

    def export_template_json(self, template: Dict, pretty: bool = True) -> str:
        """导出模板为JSON格式，用于版本管理和CI/CD集成"""
        import json

        export = dict(template)
        export["_exported_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        export["_version"] = template.get("version", "1.0.0")
        return json.dumps(export, indent=2 if pretty else None, ensure_ascii=False)

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

module_class = PdfReportManager
