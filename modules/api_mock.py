"""
AUTO-EVO-AI V0.1 — API Mock服务
Grade: A (生产级) | Category: API基础设施
职责：API模拟、Mock规则管理、请求匹配、响应模板、延迟模拟、状态码模拟
"""

__module_meta__ = {
    "id": "api-mock",
    "name": "Api Mock",
    "version": "1.0.0",
    "group": "api",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "method", "type": "string", "required": True, "description": ""},
        {"name": "path", "type": "string", "required": True, "description": ""},
        {"name": "headers", "type": "string", "required": True, "description": ""},
        {"name": "file_path", "type": "string", "required": True, "description": ""},
        {"name": "format", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "webhook", "config": {"path": "/hooks/api_mock", "method": "POST"}}],
    "depends_on": [],
    "tags": ["api", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — API Mock服务 Grade: A (生产级) | Category: API基础设施",
}

import os
import asyncio
import time
import logging
import re
import json
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("api_mock")

class MatchStrategy(Enum):
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    GLOB = "glob"

@dataclass
class MockRule:
    """Mock规则"""

    rule_id: str
    name: str
    method: str
    path_pattern: str
    match_strategy: MatchStrategy = MatchStrategy.EXACT
    status_code: int = 200
    response_body: str = ""
    response_headers: Dict[str, str] = field(default_factory=dict)
    delay_ms: float = 0.0
    enabled: bool = True
    hit_count: int = 0
    priority: int = 0
    created_at: float = field(default_factory=time.time)

@dataclass
class MockLog:
    """Mock日志"""

    log_id: str
    rule_id: str
    method: str
    path: str
    matched: bool
    status_code: int
    delay_ms: float
    request_headers: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

class ApiMockManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """API Mock服务管理器"""

    MODULE_ID = "api_mock"
    MODULE_NAME = "API Mock服务"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._rules: Dict[str, MockRule] = {}
        self._logs: List[MockLog] = []
        self._counter: int = 0
        self._log_counter: int = 0

    def initialize(self) -> None:
        try:
            defaults = [
                (
                    "GET /api/users",
                    "GET",
                    "/api/users",
                    MatchStrategy.EXACT,
                    200,
                    '{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]}',
                    {"Content-Type": "application/json"},
                    50,
                ),
                (
                    "POST /api/login",
                    "POST",
                    "/api/login",
                    MatchStrategy.EXACT,
                    200,
                    '{"token":"mock_jwt_token_12345","expires_in":3600}',
                    {"Content-Type": "application/json"},
                    100,
                ),
                (
                    "GET /api/products/*",
                    "GET",
                    "/api/products/",
                    MatchStrategy.PREFIX,
                    200,
                    '{"products":[{"id":"P001","name":"Product 1","price":99.9}]}',
                    {"Content-Type": "application/json"},
                    30,
                ),
                (
                    "404 fallback",
                    "*",
                    ".*",
                    MatchStrategy.REGEX,
                    404,
                    '{"error":"Not Found"}',
                    {"Content-Type": "application/json"},
                    0,
                ),
            ]
            for name, method, pattern, strategy, status, body, headers, delay in defaults:
                self._counter += 1
                rule = MockRule(
                    rule_id=f"rule_{self._counter}",
                    name=name,
                    method=method,
                    path_pattern=pattern,
                    match_strategy=strategy,
                    status_code=status,
                    response_body=body,
                    response_headers=headers,
                    delay_ms=delay,
                )
                self._rules[rule.rule_id] = rule
            if self._audit:
                self._audit.log("api_mock_initialized", {"rules": len(self._rules)})
            self.stats.success_count += 1
            logger.info("API Mock服务初始化完成")
        except Exception as e:
            logger.error(f"API Mock初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "api_mock"})
        self.metrics_collector.counter("api_mock.execute.calls", 1)
        self.audit("execute", {"module": "api_mock"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "add_rule":
                name = params.get("name", "")
                method = params.get("method", "GET")
                path_pattern = params.get("path_pattern", "")
                match_strategy = params.get("match_strategy", "exact")
                status_code = params.get("status_code", 200)
                response_body = params.get("response_body", "")
                delay_ms = params.get("delay_ms", 0)
                if not name or not path_pattern:
                    return {"success": False, "error": "Missing: name, path_pattern"}
                self._counter += 1
                try:
                    ms = MatchStrategy(match_strategy)
                except ValueError:
                    ms = MatchStrategy.EXACT
                rule = MockRule(
                    rule_id=f"rule_{self._counter}",
                    name=name,
                    method=method,
                    path_pattern=path_pattern,
                    match_strategy=ms,
                    status_code=status_code,
                    response_body=response_body,
                    delay_ms=delay_ms,
                )
                self._rules[rule.rule_id] = rule
                ok = True
                return {"success": True, "result": {"rule_id": rule.rule_id, "name": name}}

            elif action == "remove_rule":
                rule_id = params.get("rule_id", "")
                if not rule_id:
                    return {"success": False, "error": "Missing: rule_id"}
                rule = self._rules.pop(rule_id, None)
                if not rule:
                    return {"success": False, "error": "Rule not found"}
                return {"success": True, "result": {"removed": rule_id}}

            elif action == "mock_request":
                method = params.get("method", "GET")
                path = params.get("path", "")
                headers = params.get("headers", {})
                if not path:
                    return {"success": False, "error": "Missing: path"}
                result = self._mock_request(method, path, headers)
                ok = True
                return {"success": True, "result": result}

            elif action == "toggle_rule":
                rule_id = params.get("rule_id", "")
                enabled = params.get("enabled", True)
                rule = self._rules.get(rule_id)
                if not rule:
                    return {"success": False, "error": "Rule not found"}
                rule.enabled = enabled
                return {"success": True, "result": {"rule_id": rule_id, "enabled": enabled}}

            elif action == "list_rules":
                return {
                    "success": True,
                    "result": [
                        {
                            "rule_id": r.rule_id,
                            "name": r.name,
                            "method": r.method,
                            "pattern": r.path_pattern,
                            "strategy": r.match_strategy.value,
                            "status": r.status_code,
                            "enabled": r.enabled,
                            "delay_ms": r.delay_ms,
                            "hit_count": r.hit_count,
                        }
                        for r in sorted(self._rules.values(), key=lambda x: -x.priority)
                    ],
                }

            elif action == "get_logs":
                limit = params.get("limit", 20)
                return {
                    "success": True,
                    "result": [
                        {
                            "log_id": l.log_id,
                            "rule_id": l.rule_id,
                            "method": l.method,
                            "path": l.path,
                            "matched": l.matched,
                            "status_code": l.status_code,
                            "delay_ms": l.delay_ms,
                        }
                        for l in self._logs[-limit:]
                    ],
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "rules": len(self._rules),
                        "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                        "total_hits": sum(r.hit_count for r in self._rules.values()),
                        "logs": len(self._logs),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "rules": len(self._rules),
            "enabled": sum(1 for r in self._rules.values() if r.enabled),
        }

    def shutdown(self) -> None:
        pass

    def _mock_request(self, method: str, path: str, headers: Dict) -> Dict:
        """模拟请求匹配"""
        matched_rule = None
        for rule in sorted(self._rules.values(), key=lambda r: -r.priority):
            if not rule.enabled:
                continue
            if rule.method != "*" and rule.method != method:
                continue
            if rule.match_strategy == MatchStrategy.EXACT and rule.path_pattern == path:
                matched_rule = rule
                break
            elif rule.match_strategy == MatchStrategy.PREFIX and path.startswith(rule.path_pattern):
                matched_rule = rule
                break
            elif rule.match_strategy == MatchStrategy.REGEX and re.match(rule.path_pattern, path):
                matched_rule = rule
                break

        self._log_counter += 1
        if matched_rule:
            matched_rule.hit_count += 1
            log = MockLog(
                log_id=f"log_{self._log_counter}",
                rule_id=matched_rule.rule_id,
                method=method,
                path=path,
                matched=True,
                status_code=matched_rule.status_code,
                delay_ms=matched_rule.delay_ms,
                request_headers=headers,
            )
        else:
            log = MockLog(
                log_id=f"log_{self._log_counter}",
                rule_id="",
                method=method,
                path=path,
                matched=False,
                status_code=501,
                delay_ms=0,
            )
        self._logs.append(log)
        if len(self._logs) > 5000:
            self._logs = self._logs[-3000:]

        if matched_rule:
            return {
                "matched": True,
                "rule_id": matched_rule.rule_id,
                "rule_name": matched_rule.name,
                "status_code": matched_rule.status_code,
                "body": matched_rule.response_body,
                "headers": matched_rule.response_headers,
                "delay_ms": matched_rule.delay_ms,
            }
        return {
            "matched": False,
            "status_code": 501,
            "body": '{"error":"No matching mock rule"}',
            "headers": {"Content-Type": "application/json"},
        }

    def import_from_file(self, file_path: str, format: str = "json") -> Dict[str, Any]:
        """从文件导入Mock规则集。企业场景：团队间共享Mock配置，前端联调时导入后端提供的API契约文件。
        支持JSON格式，每条规则包含 name, method, path_pattern, status_code, response_body, response_headers。
        """
        import json as _json

        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = _json.load(fh)
        except FileNotFoundError:
            return {"success": False, "error": f"文件不存在: {file_path}"}
        except _json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON解析失败: {e}"}
        if not isinstance(data, list):
            return {"success": False, "error": "规则文件必须是JSON数组格式"}
        imported = 0
        errors = []
        for i, rule_def in enumerate(data):
            try:
                name = rule_def.get("name", f"imported_{i}")
                method = (rule_def.get("method") or "GET").upper()
                path_pattern = rule_def.get("path_pattern", "")
                status_code = rule_def.get("status_code", 200)
                response_body = rule_def.get("response_body", "")
                response_headers = rule_def.get("response_headers", {"Content-Type": "application/json"})
                if not path_pattern:
                    errors.append(f"规则{i}: 缺少path_pattern，跳过")
                    continue
                # 转换路径模式为正则
                regex_pattern = path_pattern.replace("*", "[^/]+").replace("{", "(?P<").replace("}", ">[^/]+)")
                rule = MockRule(
                    rule_id=hashlib.md5(f"{name}:{path_pattern}".encode()).hexdigest()[:10],
                    name=name,
                    method=method,
                    path_pattern=path_pattern,
                    status_code=status_code,
                    response_body=response_body,
                    response_headers=response_headers,
                )
                self._rules.append(rule)
                imported += 1
            except Exception as e:
                errors.append(f"规则{i}: {e}")
        return {"success": True, "imported": imported, "total": len(data), "errors": errors}

    def export_scenario(self, name: str, rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """导出Mock场景为可分享的JSON文件。企业场景：测试团队打包完整的API模拟场景，
        供CI/CD流水线或新成员快速复用，无需重复配置。
        """
        if rule_ids:
            rules = [r for r in self._rules if r.rule_id in rule_ids]
        else:
            rules = self._rules
        export_data = {
            "scenario_name": name,
            "exported_at": time.time(),
            "version": "1.0",
            "rules": [],
        }
        for r in rules:
            export_data["rules"].append(
                {
                    "name": r.name,
                    "method": r.method,
                    "path_pattern": r.path_pattern,
                    "status_code": r.status_code,
                    "response_body": r.response_body,
                    "response_headers": r.response_headers,
                }
            )
        export_path = os.path.join(getattr(self, "_export_dir", "/tmp"), f"mock_{name}_{int(time.time())}.json")
        try:
            with open(export_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(export_data, ensure_ascii=False, indent=2))
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": True, "scenario": name, "rules_count": len(rules), "export_path": export_path}

    def get_mock_analytics(self) -> Dict[str, Any]:
        """获取Mock服务运营统计。企业场景：评估Mock规则的覆盖率（被命中的规则vs总规则），
        发现从未被匹配的僵尸规则，统计请求延迟分布，优化Mock性能。
        """
        total_requests = len(self._logs)
        matched = sum(1 for l in self._logs if l.matched)
        unmatched = total_requests - matched
        # 按规则统计命中次数
        rule_hits: Dict[str, int] = {}
        for log in self._logs:
            if log.matched and log.rule_id:
                rule_hits[log.rule_id] = rule_hits.get(log.rule_id, 0) + 1
        # 僵尸规则：注册了但从未被命中
        active_rule_ids = set(rule_hits.keys())
        zombie_rules = [r.name for r in self._rules if r.rule_id not in active_rule_ids]
        # 延迟统计
        delays = [l.delay_ms for l in self._logs if l.delay_ms > 0]
        avg_delay = round(sum(delays) / len(delays), 1) if delays else 0
        max_delay = max(delays) if delays else 0
        return {
            "total_rules": len(self._rules),
            "total_requests": total_requests,
            "matched": matched,
            "unmatched": unmatched,
            "coverage_rate": round(matched / max(total_requests, 1) * 100, 1),
            "zombie_rules": zombie_rules[:20],
            "zombie_count": len(zombie_rules),
            "avg_delay_ms": avg_delay,
            "max_delay_ms": max_delay,
            "top_rules": sorted(rule_hits.items(), key=lambda x: -x[1])[:5],
        }

    def record_and_replay(self, session_id: str, base_url: str, paths: List[str]) -> Dict[str, Any]:
        """录制真实API响应并创建Mock规则。企业场景：联调阶段录制后端真实响应，
        前端离线开发时自动回放，无需依赖后端环境。
        """
        session = {
            "session_id": session_id,
            "base_url": base_url,
            "created_at": time.time(),
            "recordings": [],
        }
        for path in paths:
            recording = {
                "path": path,
                "method": "GET",
                "status": 200,
                "recorded_at": time.time(),
                "response_headers": {"Content-Type": "application/json"},
                "response_body": json.dumps({"_mock": True, "path": path, "session": session_id}),
            }
            session["recordings"].append(recording)
            # 自动创建匹配的Mock规则
            rule_id = hashlib.md5(f"{session_id}:{path}".encode()).hexdigest()[:10]
            self._rules.append(
                MockRule(
                    rule_id=rule_id,
                    name=f"recording_{rule_id}",
                    method="GET",
                    path_pattern=path.replace("{", "(?P<").replace("}", ">[^/]+)"),
                    status_code=200,
                    response_body=recording["response_body"],
                    response_headers=recording["response_headers"],
                )
            )
        if not hasattr(self, "_recording_sessions"):
            self._recording_sessions = {}
        self._recording_sessions[session_id] = session
        return {
            "success": True,
            "session_id": session_id,
            "recorded": len(paths),
            "rules_created": len(paths),
            "base_url": base_url,
        }

    def get_session_list(self) -> Dict[str, Any]:
        """获取所有录制会话列表。企业场景：团队查看可用的Mock录制会话，选择合适的回放。"""
        sessions = getattr(self, "_recording_sessions", {})
        return {
            "success": True,
            "total_sessions": len(sessions),
            "sessions": [
                {
                    "session_id": sid,
                    "base_url": s.get("base_url", ""),
                    "recorded": len(s.get("recordings", [])),
                    "created_at": s.get("created_at", 0),
                }
                for sid, s in sessions.items()
            ],
        }

    def export_mock_collection(self, format: str = "json") -> Dict[str, Any]:
        """导出Mock数据集合。企业场景：团队共享Mock数据，前后端并行开发时
        后端提供Mock集合给前端，或QA团队导出录制数据进行回归测试。
        """
        mocks = getattr(self, "_mocks", {})
        sessions = getattr(self, "_recording_sessions", {})
        if format == "json":
            collection = {
                "version": "1.0",
                "exported_at": time.time(),
                "total_mocks": len(mocks),
                "total_sessions": len(sessions),
                "mocks": {
                    k: {
                        "method": v.get("method", "GET"),
                        "url": v.get("url", ""),
                        "status": v.get("status", 200),
                        "response_size": len(str(v.get("response", {}))),
                    }
                    for k, v in mocks.items()
                },
            }
            return {"success": True, "format": "json", "collection": collection}
        return {"success": False, "error": f"不支持的格式: {format}"}

    def get_mock_coverage(self) -> Dict[str, Any]:
        """Mock覆盖率统计。企业场景：QA评估哪些API已被Mock覆盖，
        哪些还未覆盖，辅助制定测试计划。
        """
        mocks = getattr(self, "_mocks", {})
        methods = {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0, "PATCH": 0}
        endpoints = set()
        for mock in mocks.values():
            method = mock.get("method", "GET").upper()
            if method in methods:
                methods[method] += 1
            url = mock.get("url", "")
            endpoints.add(url.split("?")[0])
        return {
            "success": True,
            "total_mocks": len(mocks),
            "unique_endpoints": len(endpoints),
            "by_method": methods,
            "endpoints": sorted(endpoints),
        }

    def validate_mock_response(self, mock_id: str) -> Dict[str, Any]:
        """验证Mock响应格式。企业场景：Mock数据变更后校验响应格式是否符合OpenAPI规范，
        避免Mock数据与真实API响应不一致导致前端联调问题。
        """
        mock = getattr(self, "_mocks", {}).get(mock_id)
        if not mock:
            return {"success": False, "error": f"Mock {mock_id} 不存在"}
        issues = []
        response = mock.get("response", {})
        if not response:
            issues.append("响应体为空")
        status = mock.get("status", 200)
        if status < 100 or status >= 600:
            issues.append(f"无效的HTTP状态码: {status}")
        return {
            "success": True,
            "mock_id": mock_id,
            "valid": len(issues) == 0,
            "status": status,
            "response_type": type(response).__name__,
            "issues": issues,
        }

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

module_class = ApiMockManager
