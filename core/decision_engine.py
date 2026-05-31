"""
AUTO-EVO-AI 自主决策引擎 v1.0
生产级闭环: 事件感知 → 智能决策 → 自动执行 → 结果反馈

上市公司级标准:
- 链式决策: 发现异常 → 诊断分析 → 自动修复 → 验证确认 → 生成报告
- 规则引擎: 可编程决策规则(条件触发 + 定时巡检 + 事件驱动)
- 经验学习: 成功/失败经验持久化，优化后续决策
- 优雅降级: 执行失败自动降级到人工通知
"""

import asyncio
import time
import json
from core.logging_config import get_logger
import traceback
from datetime import datetime, timezone, UTC
from typing import Dict, List, Optional, Any
from collections.abc import Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import sqlite3
import uuid

logger = get_logger("decision_engine")


# ============================================================================
# 数据模型
# ============================================================================

class DecisionPriority(str, Enum):
    CRITICAL = "critical"  # 立即执行
    HIGH = "high"          # 高优先级
    NORMAL = "normal"      # 正常
    LOW = "low"            # 低优先级

class DecisionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"  # 升级到人工处理
    CANCELLED = "cancelled"


@dataclass
class DecisionEvent:
    """决策触发事件"""
    source: str           # 事件来源: scheduler/event_bus/health_check/manual
    event_type: str       # 事件类型
    data: dict            # 事件数据
    severity: str         # 严重级别: critical/warning/info
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class DecisionRule:
    """决策规则"""
    id: str
    name: str
    description: str
    triggers: list[dict]       # 触发条件 [{"type": "event", "event_type": "module_failed"}, ...]
    conditions: list[dict]     # 执行条件 [{"field": "severity", "op": "eq", "value": "critical"}, ...]
    actions: list[dict]        # 执行动作 [{"type": "module", "module": "x", "method": "y"}, ...]
    chain: list[dict]          # 决策链: 按序执行, 前一步输出传递给下一步
    priority: str = "normal"
    enabled: bool = True
    cooldown: int = 300        # 冷却时间(秒), 防止频繁触发
    max_retries: int = 2
    escalation_module: str = "enterprise_notifier"  # 失败后通知
    escalation_action: str = "send"
    last_triggered: float = 0  # 上次触发时间戳
    trigger_count: int = 0
    success_count: int = 0


@dataclass
class DecisionExecution:
    """决策执行记录"""
    id: str
    rule_id: str
    rule_name: str
    priority: str
    status: str = DecisionStatus.PENDING.value
    trigger_event: dict = field(default_factory=dict)
    chain_results: list[dict] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    error: str = ""
    summary: str = ""


# ============================================================================
# 链式决策执行器
# ============================================================================

class ChainExecutor:
    """
    链式决策执行器 — 核心闭环

    支持变量传递: ${steps.0.output.xxx} 引用前一步输出
    支持条件分支: 前一步success决定是否继续
    支持并行执行: parallel步骤可同时跑
    支持超时控制: 整条链和每步都可控
    """

    def __init__(self, module_executor: Callable = None):
        """
        Args:
            module_executor: async def(module_id, action, params) -> dict
                             模块执行回调，由coordinator注入
        """
        self._executor = module_executor

    async def execute_chain(
        self,
        chain: list[dict],
        context: dict = None,
        chain_timeout: int = 120,
    ) -> dict:
        """
        执行决策链

        Args:
            chain: 决策链 [{"step": "detect", "module": "x", "action": "y", "params": {}}, ...]
            context: 初始上下文
            chain_timeout: 整条链超时(秒)

        Returns:
            {"success": bool, "results": [...], "final_output": {}, "summary": str}
        """
        context = context or {}
        results = []
        shared_output = context.get("input", {})

        for i, step in enumerate(chain):
            # 条件分支: 检查是否跳过
            condition = step.get("condition")
            if condition:
                if not self._evaluate_condition(condition, shared_output, results):
                    results.append({
                        "step": step.get("step", f"step_{i}"),
                        "module": step.get("module", ""),
                        "action": step.get("action", ""),
                        "skipped": True,
                        "reason": "condition_not_met",
                    })
                    continue

            # 并行执行
            if step.get("parallel"):
                parallel_results = await self._execute_parallel(
                    step["parallel"], shared_output, results, chain_timeout
                )
                results.extend(parallel_results)
                # 合并并行输出
                for pr in parallel_results:
                    if pr.get("success"):
                        shared_output.update(pr.get("output", {}))
                continue

            # 单步执行
            step_result = await self._execute_single_step(step, shared_output, results, chain_timeout)
            results.append(step_result)

            if step_result.get("skipped"):
                continue

            # 传递输出到下一步
            if step_result.get("success"):
                output = step_result.get("output", {})
                if isinstance(output, dict):
                    shared_output.update(output)
                else:
                    shared_output["last_result"] = output

                # 失败时停止链(除非指定continue_on_error)
                if step_result.get("success") is False and not step.get("continue_on_error"):
                    break
            else:
                if not step.get("continue_on_error"):
                    break

        success_count = sum(1 for r in results if r.get("success") and not r.get("skipped"))
        fail_count = sum(1 for r in results if not r.get("success") and not r.get("skipped"))
        skip_count = sum(1 for r in results if r.get("skipped"))

        return {
            "success": fail_count == 0 and success_count > 0,
            "results": results,
            "final_output": shared_output,
            "summary": f"{success_count}成功/{fail_count}失败/{skip_count}跳过 共{len(results)}步",
        }

    async def _execute_single_step(self, step: dict, shared_output: dict, prev_results: list, chain_timeout: int) -> dict:
        """执行单步"""
        module_id = step.get("module", "")
        action = step.get("action", "status")
        raw_params = step.get("params", {})
        step_timeout = step.get("timeout", min(30, chain_timeout))
        step_name = step.get("step", f"{module_id}.{action}")

        # 参数模板替换
        params = self._resolve_params(raw_params, shared_output, prev_results)

        start = time.monotonic()
        try:
            if self._executor:
                result = await asyncio.wait_for(
                    self._executor(module_id, action, params),
                    timeout=step_timeout
                )
            else:
                result = {"success": False, "error": "no_executor"}

            duration = int((time.monotonic() - start) * 1000)
            output = result.get("result", result.get("data", {}))

            return {
                "step": step_name,
                "module": module_id,
                "action": action,
                "success": result.get("success", False),
                "output": output if isinstance(output, (dict, list, str)) else str(output)[:2000],
                "error": result.get("error", ""),
                "duration_ms": duration,
            }
        except TimeoutError:
            return {
                "step": step_name,
                "module": module_id,
                "action": action,
                "success": False,
                "error": f"超时({step_timeout}s)",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        except Exception as e:
            return {
                "step": step_name,
                "module": module_id,
                "action": action,
                "success": False,
                "error": str(e)[:500],
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

    async def _execute_parallel(self, steps: list, shared_output: dict, prev_results: list, chain_timeout: int) -> list:
        """并行执行多个步骤"""
        tasks = []
        for s in steps:
            tasks.append(self._execute_single_step(s, shared_output, prev_results, chain_timeout))
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _resolve_params(self, params: dict, shared_output: dict, prev_results: list) -> dict:
        """解析参数模板: ${xxx}"""
        if not isinstance(params, dict):
            return params if not isinstance(params, str) else self._resolve_template(params, shared_output, prev_results)

        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                resolved[k] = self._resolve_template(v, shared_output, prev_results)
            elif isinstance(v, dict):
                resolved[k] = self._resolve_params(v, shared_output, prev_results)
            elif isinstance(v, list):
                resolved[k] = [
                    self._resolve_template(i, shared_output, prev_results) if isinstance(i, str) else i
                    for i in v
                ]
            else:
                resolved[k] = v
        return resolved

    def _resolve_template(self, template: str, shared_output: dict, prev_results: list) -> str:
        """解析 ${steps.0.output.xxx} 和 ${shared.xxx} 模板"""
        import re
        def replacer(match):
            expr = match.group(1).strip()
            # ${steps.N.output.xxx}
            if expr.startswith("steps."):
                parts = expr.split(".", 2)
                try:
                    idx = int(parts[1])
                    if idx < len(prev_results):
                        data = prev_results[idx].get("output", {})
                        if len(parts) > 2:
                            for key in parts[2:]:
                                if isinstance(data, dict):
                                    data = data.get(key, "")
                                else:
                                    return ""
                            return str(data) if data else match.group(0)
                        return str(data) if data else match.group(0)
                except (ValueError, IndexError):
                    pass
            # ${shared.xxx} 或直接key
            elif expr.startswith("shared."):
                key = expr[7:]
                return str(shared_output.get(key, match.group(0)))
            else:
                val = shared_output.get(expr, match.group(0))
                return str(val) if val else match.group(0)
            return match.group(0)

        return re.sub(r'\$\{([^}]+)\}', replacer, template)

    def _evaluate_condition(self, condition: dict, shared_output: dict, prev_results: list) -> bool:
        """评估条件: {"field": "steps.0.success", "op": "eq", "value": true}"""
        field = condition.get("field", "")
        op = condition.get("op", "eq")
        expected = condition.get("value")

        # 取值
        actual = self._resolve_template(f"${{{field}}}", shared_output, prev_results)

        # 类型转换
        if isinstance(expected, bool):
            actual = actual.lower() in ("true", "1", "yes")
        elif isinstance(expected, int):
            try:
                actual = int(actual)
            except (ValueError, TypeError):
                return False

        if op == "eq":
            return actual == expected
        elif op == "ne":
            return actual != expected
        elif op == "gt":
            return float(actual) > float(expected)
        elif op == "lt":
            return float(actual) < float(expected)
        elif op == "gte":
            return float(actual) >= float(expected)
        elif op == "lte":
            return float(actual) <= float(expected)
        elif op == "contains":
            return expected in actual
        elif op == "in":
            return actual in expected
        return False


# ============================================================================
# 决策引擎主体
# ============================================================================

class DecisionEngine:
    """
    自主决策引擎 v1.0

    职责:
    1. 事件感知: 接收 scheduler/event_bus/health_check/manual 触发事件
    2. 规则匹配: 从规则库中找出匹配的决策规则
    3. 链式执行: 执行规则定义的决策链(多步骤+变量传递+条件分支)
    4. 结果反馈: 成功记录经验, 失败升级通知
    5. 经验学习: 统计规则命中率, 自动调整优先级
    """

    def __init__(self, db_path: str = None, module_executor: Callable = None):
        self._db_path = db_path or str(Path(__file__).parent.parent / "data" / "decision_engine.db")
        self._executor = module_executor
        self._chain_executor = ChainExecutor(module_executor)
        self._rules: dict[str, DecisionRule] = {}
        self._running_executions: dict[str, DecisionExecution] = {}
        self._event_listeners: dict[str, list[Callable]] = {}  # event_type -> [callbacks]
        self._stats = {"total": 0, "success": 0, "failed": 0, "escalated": 0}

        # 初始化DB
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # 加载预置规则
        self._load_preset_rules()

        logger.info("[DecisionEngine] 初始化完成")

    # ── 数据库 ──

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decision_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    triggers TEXT DEFAULT '[]',
                    conditions TEXT DEFAULT '[]',
                    actions TEXT DEFAULT '[]',
                    chain TEXT DEFAULT '[]',
                    priority TEXT DEFAULT 'normal',
                    enabled INTEGER DEFAULT 1,
                    cooldown INTEGER DEFAULT 300,
                    max_retries INTEGER DEFAULT 2,
                    escalation_module TEXT DEFAULT 'enterprise_notifier',
                    escalation_action TEXT DEFAULT 'send',
                    last_triggered REAL DEFAULT 0,
                    trigger_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS decision_history (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT,
                    rule_name TEXT,
                    priority TEXT,
                    status TEXT DEFAULT 'pending',
                    trigger_event TEXT DEFAULT '{}',
                    chain_results TEXT DEFAULT '[]',
                    summary TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_history_status ON decision_history(status);
                CREATE INDEX IF NOT EXISTS idx_history_rule ON decision_history(rule_id);
                CREATE INDEX IF NOT EXISTS idx_history_time ON decision_history(created_at);
            """)

    # ── 预置规则 ──

    def _load_preset_rules(self):
        """加载预置决策规则 — 生产级闭环"""
        presets = [
            # 1. 模块故障自动修复链
            {
                "id": "auto-heal-module",
                "name": "模块故障自动修复",
                "description": "模块执行失败 → 诊断分析 → 尝试重启 → 验证 → 通知",
                "triggers": [{"type": "event", "event_type": "module_failed"}],
                "conditions": [],
                "priority": "high",
                "cooldown": 120,
                "max_retries": 2,
                "chain": [
                    {
                        "step": "diagnose",
                        "module": "perf_monitor",
                        "action": "diagnose_module",
                        "params": {"module": "${shared.module_id}"},
                        "timeout": 15,
                    },
                    {
                        "step": "check_health",
                        "module": "perf_monitor",
                        "action": "status",
                        "params": {},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 10,
                    },
                    {
                        "step": "notify_result",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "模块 ${shared.module_id} 故障修复: ${steps.2.output.summary}",
                            "level": "${shared.severity}",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 2. CPU过高自动处理链
            {
                "id": "auto-cpu-normalize",
                "name": "CPU异常自动处理",
                "description": "检测CPU过高 → 分析占用进程 → 清理缓存 → GC → 验证",
                "triggers": [{"type": "health", "metric": "cpu", "threshold": 85}],
                "conditions": [],
                "priority": "high",
                "cooldown": 300,
                "chain": [
                    {
                        "step": "analyze",
                        "module": "perf_monitor",
                        "action": "diagnose",
                        "params": {},
                        "timeout": 15,
                    },
                    {
                        "step": "clear_cache",
                        "module": "cache_engine",
                        "action": "clear_expired",
                        "params": {},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 10,
                    },
                    {
                        "step": "report",
                        "module": "perf_monitor",
                        "action": "get_stats",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "CPU异常处理完成: ${steps.2.output.summary}",
                            "level": "warning",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 3. 内存泄漏处理链
            {
                "id": "auto-memory-cleanup",
                "name": "内存泄漏自动清理",
                "description": "内存超阈值 → 分析 → 清理 → 报告",
                "triggers": [{"type": "health", "metric": "memory", "threshold": 80}],
                "conditions": [],
                "priority": "high",
                "cooldown": 600,
                "chain": [
                    {
                        "step": "analyze",
                        "module": "perf_monitor",
                        "action": "diagnose",
                        "params": {"focus": "memory"},
                        "timeout": 15,
                    },
                    {
                        "step": "gc",
                        "module": "cache_engine",
                        "action": "clear_all",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "verify",
                        "module": "perf_monitor",
                        "action": "status",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "内存清理完成: 使用率从${shared.memory_before}%降至${steps.2.output.memory}%",
                            "level": "warning",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 4. 安全威胁响应链
            {
                "id": "security-threat-response",
                "name": "安全威胁自动响应",
                "description": "检测安全威胁 → 扫描 → 隔离 → 报告",
                "triggers": [{"type": "event", "event_type": "security_threat"}],
                "conditions": [{"field": "severity", "op": "in", "value": ["critical", "high"]}],
                "priority": "critical",
                "cooldown": 60,
                "max_retries": 1,
                "chain": [
                    {
                        "step": "full_scan",
                        "module": "security_scanner",
                        "action": "scan",
                        "params": {"scope": "full"},
                        "timeout": 30,
                    },
                    {
                        "step": "audit",
                        "module": "access_control",
                        "action": "get_audit_log",
                        "params": {"limit": 20},
                        "timeout": 15,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "安全威胁检测: ${shared.threat_description}",
                            "level": "critical",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 5. 死信队列处理链
            {
                "id": "dead-letter-recovery",
                "name": "死信队列自动恢复",
                "description": "死信队列堆积 → 分析失败原因 → 自动重试 → 报告",
                "triggers": [{"type": "event", "event_type": "dead_letter"}],
                "conditions": [],
                "priority": "normal",
                "cooldown": 300,
                "max_retries": 3,
                "chain": [
                    {
                        "step": "analyze",
                        "module": "task_queue",
                        "action": "get_stats",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "retry",
                        "module": "task_queue",
                        "action": "retry_all",
                        "params": {},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 30,
                    },
                    {
                        "step": "report",
                        "module": "log_aggregator",
                        "action": "search",
                        "params": {"level": "error", "limit": 10},
                        "timeout": 10,
                    },
                ],
            },
            # 6. 日志异常检测链
            {
                "id": "log-anomaly-detect",
                "name": "日志异常自动检测",
                "description": "日志异常激增 → 聚合分析 → 根因定位 → 通知",
                "triggers": [{"type": "event", "event_type": "log_anomaly"}],
                "conditions": [],
                "priority": "normal",
                "cooldown": 600,
                "chain": [
                    {
                        "step": "aggregate",
                        "module": "log_aggregator",
                        "action": "aggregate",
                        "params": {"time_range": "1h"},
                        "timeout": 15,
                    },
                    {
                        "step": "summarize",
                        "module": "log_aggregator",
                        "action": "summary",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "日志异常检测: ${steps.1.output.summary}",
                            "level": "warning",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 7. 定时健康巡检链
            {
                "id": "scheduled-health-check",
                "name": "定时健康巡检",
                "description": "全面健康检查 → 模块状态 → 性能报告 → 存储",
                "triggers": [{"type": "scheduler", "cron": "0 6 * * *"}],  # 每天6:00
                "conditions": [],
                "priority": "low",
                "cooldown": 3600,
                "chain": [
                    {
                        "step": "health",
                        "module": "perf_monitor",
                        "action": "health_check",
                        "params": {},
                        "timeout": 20,
                    },
                    {
                        "step": "modules",
                        "module": "perf_monitor",
                        "action": "get_module_status",
                        "params": {},
                        "timeout": 15,
                    },
                    {
                        "step": "report",
                        "module": "doc_generator",
                        "action": "generate_report",
                        "params": {
                            "title": "每日健康巡检报告",
                            "content": "${steps.0.output}",
                        },
                        "timeout": 15,
                    },
                ],
            },
            # 8. 数据库性能优化链
            {
                "id": "db-perf-optimize",
                "name": "数据库性能自动优化",
                "description": "检测慢查询 → 分析执行计划 → 优化建议 → 通知",
                "triggers": [{"type": "health", "metric": "slow_query", "threshold": 10}],
                "conditions": [],
                "priority": "normal",
                "cooldown": 1800,
                "chain": [
                    {
                        "step": "slow_queries",
                        "module": "database_client",
                        "action": "slow_queries",
                        "params": {},
                        "timeout": 15,
                    },
                    {
                        "step": "analyze",
                        "module": "database_client",
                        "action": "analyze_query",
                        "params": {"queries": "${steps.0.output.queries}"},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 20,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "数据库性能分析: ${steps.1.output.summary}",
                            "level": "normal",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 9. 磁盘空间清理链
            {
                "id": "disk-cleanup",
                "name": "磁盘空间自动清理",
                "description": "磁盘空间不足 → 清理日志 → 清理缓存 → 通知",
                "triggers": [{"type": "health", "metric": "disk", "threshold": 90}],
                "conditions": [],
                "priority": "high",
                "cooldown": 1800,
                "chain": [
                    {
                        "step": "check_disk",
                        "module": "perf_monitor",
                        "action": "get_disk_usage",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "clean_logs",
                        "module": "log_aggregator",
                        "action": "clean_old",
                        "params": {"days": 7},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 30,
                    },
                    {
                        "step": "verify",
                        "module": "perf_monitor",
                        "action": "get_disk_usage",
                        "params": {},
                        "timeout": 10,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "磁盘清理完成: 释放${shared.freed_space}MB",
                            "level": "warning",
                        },
                        "timeout": 10,
                    },
                ],
            },
            # 10. GitHub Trending自动分析链
            {
                "id": "github-daily-analysis",
                "name": "GitHub热门项目每日分析",
                "description": "扫描热门项目 → AI分析 → 生成报告 → 推送通知",
                "triggers": [{"type": "scheduler", "cron": "0 22 * * *"}],  # 每天22:00
                "conditions": [],
                "priority": "low",
                "cooldown": 86400,
                "chain": [
                    {
                        "step": "scan",
                        "module": "github_scanner",
                        "action": "fetch_trending",
                        "params": {"since": "daily", "keyword": "AI"},
                        "timeout": 30,
                    },
                    {
                        "step": "analyze",
                        "module": "ai_gateway",
                        "action": "analyze",
                        "params": {"content": "${steps.0.output}", "instruction": "分析这些AI开源项目的技术价值和商业潜力"},
                        "condition": {"field": "steps.0.success", "op": "eq", "value": True},
                        "timeout": 60,
                    },
                    {
                        "step": "notify",
                        "module": "enterprise_notifier",
                        "action": "send",
                        "params": {
                            "message": "GitHub AI热门项目日报: ${steps.1.output}",
                            "level": "info",
                        },
                        "timeout": 10,
                    },
                ],
            },
        ]

        for preset in presets:
            rule = DecisionRule(
                id=preset["id"],
                name=preset["name"],
                description=preset["description"],
                triggers=preset.get("triggers", []),
                conditions=preset.get("conditions", []),
                actions=preset.get("actions", []),
                chain=preset.get("chain", []),
                priority=preset.get("priority", "normal"),
                cooldown=preset.get("cooldown", 300),
                max_retries=preset.get("max_retries", 2),
                escalation_module=preset.get("escalation_module", "enterprise_notifier"),
                escalation_action=preset.get("escalation_action", "send"),
            )
            self._rules[rule.id] = rule
            self._persist_rule(rule)

        logger.info(f"[DecisionEngine] 加载 {len(presets)} 条预置规则")

    def _persist_rule(self, rule: DecisionRule):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO decision_rules
                (id, name, description, triggers, conditions, actions, chain, priority,
                 enabled, cooldown, max_retries, escalation_module, escalation_action,
                 last_triggered, trigger_count, success_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id, rule.name, rule.description,
                json.dumps(rule.triggers, ensure_ascii=False),
                json.dumps(rule.conditions, ensure_ascii=False),
                json.dumps(rule.actions, ensure_ascii=False),
                json.dumps(rule.chain, ensure_ascii=False),
                rule.priority, int(rule.enabled), rule.cooldown, rule.max_retries,
                rule.escalation_module, rule.escalation_action,
                rule.last_triggered, rule.trigger_count, rule.success_count,
            ))

    # ── 事件处理 ──

    def on_event(self, event: DecisionEvent) -> list[dict]:
        """
        接收事件，匹配规则，返回触发的决策列表(同步)
        实际执行由调用方异步调用 execute_decisions
        """
        matched = []
        now = time.time()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # 冷却检查
            if now - rule.last_triggered < rule.cooldown:
                continue

            # 触发匹配
            if not self._match_trigger(rule, event):
                continue

            # 条件检查
            if not self._match_conditions(rule, event):
                continue

            matched.append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "priority": rule.priority,
                "chain": rule.chain,
            })

            # 更新触发时间
            rule.last_triggered = now
            rule.trigger_count += 1
            self._persist_rule(rule)

        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        matched.sort(key=lambda x: priority_order.get(x["priority"], 99))

        return matched

    def _match_trigger(self, rule: DecisionRule, event: DecisionEvent) -> bool:
        for trigger in rule.triggers:
            t_type = trigger.get("type")
            if t_type == "event" and trigger.get("event_type") == event.event_type:
                return True
            if t_type == "health":
                metric = trigger.get("metric", "")
                if metric in event.event_type or event.event_type in f"health_{metric}":
                    threshold = trigger.get("threshold", 0)
                    value = event.data.get(metric, event.data.get("value", 0))
                    try:
                        if float(value) >= float(threshold):
                            return True
                    except (ValueError, TypeError):
                        pass
        return False

    def _match_conditions(self, rule: DecisionRule, event: DecisionEvent) -> bool:
        if not rule.conditions:
            return True
        for cond in rule.conditions:
            field = cond.get("field", "")
            op = cond.get("op", "eq")
            value = cond.get("value")

            if field == "severity":
                actual = event.severity
            else:
                actual = event.data.get(field, "")

            if op == "eq" and actual != value or op == "ne" and actual == value or op == "in" and actual not in (value if isinstance(value, list) else [value]):
                return False
            elif op == "gt":
                try:
                    if float(actual) <= float(value):
                        return False
                except (ValueError, TypeError):
                    return False
            elif op == "contains":
                if value not in str(actual):
                    return False
        return True

    # ── 决策执行 ──

    async def execute_decision(self, rule_info: dict, trigger_event: dict = None) -> DecisionExecution:
        """执行一条决策规则"""
        exec_id = f"dec_{uuid.uuid4().hex[:10]}"
        execution = DecisionExecution(
            id=exec_id,
            rule_id=rule_info["rule_id"],
            rule_name=rule_info["rule_name"],
            priority=rule_info["priority"],
            trigger_event=trigger_event or {},
            started_at=datetime.now(UTC).isoformat(),
        )
        execution.status = DecisionStatus.RUNNING.value
        self._running_executions[exec_id] = execution

        self._stats["total"] += 1
        start_time = time.monotonic()

        try:
            chain = rule_info.get("chain", [])
            if not chain:
                execution.status = DecisionStatus.SUCCESS.value
                execution.summary = "空链,跳过"
                return execution

            # 构建上下文
            context = {
                "input": {
                    "rule_id": rule_info["rule_id"],
                    "rule_name": rule_info["rule_name"],
                    "trigger_event": trigger_event or {},
                }
            }
            if trigger_event:
                context["input"].update(trigger_event.get("data", {}))

            # 执行链
            result = await self._chain_executor.execute_chain(chain, context)

            # 更新执行记录
            execution.chain_results = result["results"]
            execution.duration_ms = int((time.monotonic() - start_time) * 1000)

            if result["success"]:
                execution.status = DecisionStatus.SUCCESS.value
                execution.summary = result["summary"]
                self._stats["success"] += 1
                # 更新规则成功计数
                rule = self._rules.get(rule_info["rule_id"])
                if rule:
                    rule.success_count += 1
                    self._persist_rule(rule)
            else:
                execution.status = DecisionStatus.FAILED.value
                execution.summary = result["summary"]
                execution.error = "; ".join(
                    r.get("error", "") for r in result["results"] if r.get("error")
                )
                self._stats["failed"] += 1

                # 升级通知
                await self._escalate(execution)

        except Exception as e:
            execution.status = DecisionStatus.FAILED.value
            execution.error = traceback.format_exc()[-1000:]
            execution.duration_ms = int((time.monotonic() - start_time) * 1000)
            self._stats["failed"] += 1
            logger.error(f"[DecisionEngine] 执行异常 {exec_id}: {e}", exc_info=True)
            await self._escalate(execution)

        finally:
            execution.finished_at = datetime.now(UTC).isoformat()
            self._persist_execution(execution)
            self._running_executions.pop(exec_id, None)

        return execution

    async def _escalate(self, execution: DecisionExecution):
        """升级通知 — 决策失败时通知人工"""
        rule = self._rules.get(execution.rule_id)
        if not rule or not self._executor:
            return

        try:
            await asyncio.wait_for(
                self._executor(
                    rule.escalation_module,
                    rule.escalation_action,
                    {
                        "message": f"[决策升级] {execution.rule_name} 执行失败: {execution.summary or execution.error[:200]}",
                        "level": "warning",
                        "rule_id": execution.rule_id,
                        "execution_id": execution.id,
                    }
                ),
                timeout=10
            )
            self._stats["escalated"] += 1
            logger.info(f"[DecisionEngine] 已升级通知: {execution.rule_name}")
        except Exception as e:
            logger.warning(f"[DecisionEngine] 升级通知失败: {e}")

    def _persist_execution(self, execution: DecisionExecution):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO decision_history
                (id, rule_id, rule_name, priority, status, trigger_event, chain_results,
                 summary, error, started_at, finished_at, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.id, execution.rule_id, execution.rule_name, execution.priority,
                execution.status,
                json.dumps(execution.trigger_event, ensure_ascii=False),
                json.dumps(execution.chain_results, ensure_ascii=False, default=str),
                execution.summary, execution.error,
                execution.started_at, execution.finished_at, execution.duration_ms,
            ))

    # ── 公开查询接口 ──

    def get_rules(self) -> list[dict]:
        """获取所有规则"""
        return [self._rule_to_dict(r) for r in self._rules.values()]

    def get_rule(self, rule_id: str) -> dict | None:
        rule = self._rules.get(rule_id)
        return self._rule_to_dict(rule) if rule else None

    def add_rule(self, rule_data: dict) -> dict:
        """动态添加规则"""
        rule = DecisionRule(
            id=rule_data.get("id", f"custom_{uuid.uuid4().hex[:8]}"),
            name=rule_data["name"],
            description=rule_data.get("description", ""),
            triggers=rule_data.get("triggers", []),
            conditions=rule_data.get("conditions", []),
            actions=rule_data.get("actions", []),
            chain=rule_data.get("chain", []),
            priority=rule_data.get("priority", "normal"),
            cooldown=rule_data.get("cooldown", 300),
            max_retries=rule_data.get("max_retries", 2),
        )
        self._rules[rule.id] = rule
        self._persist_rule(rule)
        return self._rule_to_dict(rule)

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("DELETE FROM decision_rules WHERE id = ?", (rule_id,))
            return True
        return False

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = enabled
            self._persist_rule(rule)
            return True
        return False

    def update_rule(self, rule_id: str, updates: dict) -> dict | None:
        """更新规则字段"""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for key in ("name", "description", "triggers", "conditions", "actions",
                     "chain", "priority", "cooldown", "max_retries", "enabled"):
            if key in updates:
                setattr(rule, key, updates[key])
        self._persist_rule(rule)
        return self._rule_to_dict(rule)

    def get_history(self, limit: int = 50, status: str = None, rule_id: str = None) -> list[dict]:
        """查询执行历史"""
        query = "SELECT * FROM decision_history WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = []
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, params):
                r = dict(row)
                r["trigger_event"] = json.loads(r.get("trigger_event", "{}"))
                r["chain_results"] = json.loads(r.get("chain_results", "[]"))
                rows.append(r)
        return rows

    def get_execution_detail(self, execution_id: str) -> dict | None:
        """获取单次执行详情"""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM decision_history WHERE id = ?", (execution_id,)).fetchone()
            if row:
                r = dict(row)
                r["trigger_event"] = json.loads(r.get("trigger_event", "{}"))
                r["chain_results"] = json.loads(r.get("chain_results", "[]"))
                return r
        return None

    def get_stats(self) -> dict:
        """获取引擎统计"""
        rule_stats = {
            r.id: {
                "name": r.name,
                "trigger_count": r.trigger_count,
                "success_count": r.success_count,
                "success_rate": r.success_count / max(r.trigger_count, 1),
                "enabled": r.enabled,
            }
            for r in self._rules.values()
        }
        return {
            "engine_stats": self._stats,
            "rules_count": len(self._rules),
            "rules_enabled": sum(1 for r in self._rules.values() if r.enabled),
            "running_executions": len(self._running_executions),
            "rule_stats": rule_stats,
        }

    def _rule_to_dict(self, rule: DecisionRule) -> dict:
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "triggers": rule.triggers,
            "conditions": rule.conditions,
            "actions": rule.actions,
            "chain": rule.chain,
            "priority": rule.priority,
            "enabled": rule.enabled,
            "cooldown": rule.cooldown,
            "max_retries": rule.max_retries,
            "escalation_module": rule.escalation_module,
            "escalation_action": rule.escalation_action,
            "last_triggered": rule.last_triggered,
            "trigger_count": rule.trigger_count,
            "success_count": rule.success_count,
            "experience_score": self._experience_score(rule),
        }

    # ── v1.1 经验加权 + 智能协调层集成 ──

    def _experience_score(self, rule: DecisionRule) -> float:
        """
        计算规则的经验分 0-100
        
        因子:
        - 历史成功率 (权重40%)
        - 触发频次 (权重20%)
        - 平均执行时间 (权重20%, 越短越好)
        - 最近表现趋势 (权重20%)
        """
        total = rule.trigger_count
        if total == 0:
            return 50.0  # 无经验, 中等分

        # 成功率
        success_rate = rule.success_count / total

        # 频次因子 (对数缩放, 避免极高频规则垄断)
        import math
        freq_factor = min(math.log1p(total) / math.log1p(100), 1.0)

        # 时间因子 (从history查平均耗时)
        avg_ms = self._get_rule_avg_duration(rule.id)
        time_factor = max(0, 1.0 - avg_ms / 30000)  # 30s内完成得满分

        # 趋势因子 (最近5次 vs 历史)
        trend_factor = self._get_rule_trend(rule.id)

        score = (
            success_rate * 40 +
            freq_factor * 20 +
            time_factor * 20 +
            trend_factor * 20
        )
        return round(score, 1)

    def _get_rule_avg_duration(self, rule_id: str) -> float:
        """获取规则平均执行耗时(ms)"""
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT AVG(duration_ms) FROM decision_history WHERE rule_id = ? AND status = 'success'",
                    (rule_id,)
                ).fetchone()
                return row[0] if row and row[0] else 0
        except Exception:
            return 0

    def _get_rule_trend(self, rule_id: str) -> float:
        """
        获取规则最近趋势 0-1
        
        最近5次成功率 vs 历史成功率
        返回: 0.5=平稳, >0.5=改善, <0.5=恶化
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                # 最近5次
                recent = conn.execute(
                    "SELECT success FROM (SELECT CASE WHEN status='success' THEN 1 ELSE 0 END as success "
                    "FROM decision_history WHERE rule_id = ? ORDER BY created_at DESC LIMIT 5)",
                    (rule_id,)
                ).fetchall()
                if not recent:
                    return 0.5
                recent_rate = sum(r[0] for r in recent) / len(recent)

                # 历史全部
                total = conn.execute(
                    "SELECT COUNT(*) FROM decision_history WHERE rule_id = ?",
                    (rule_id,)
                ).fetchone()[0]
                success_total = conn.execute(
                    "SELECT COUNT(*) FROM decision_history WHERE rule_id = ? AND status = 'success'",
                    (rule_id,)
                ).fetchone()[0]
                overall_rate = success_total / max(total, 1)

                # 趋势: 最近好于历史→高分
                return min(max((recent_rate - overall_rate + 1) / 2, 0), 1)
        except Exception:
            return 0.5

    def smart_evaluate(self, event: DecisionEvent, intelligent_coordinator: Any = None) -> list[dict]:
        """
        v1.1 智能评估 — 规则匹配 + 经验加权 + 智能协调器建议
        
        Args:
            event: 决策事件
            intelligent_coordinator: IntelligentCoordinator实例(可选)
        
        Returns:
            匹配的决策列表, 按综合评分排序
        """
        # 1. 基础规则匹配
        matched = self.on_event(event)

        # 2. 经验加权评分
        for m in matched:
            rule = self._rules.get(m["rule_id"])
            if rule:
                m["experience_score"] = self._experience_score(rule)
                m["success_rate"] = rule.success_count / max(rule.trigger_count, 1)
            else:
                m["experience_score"] = 50.0
                m["success_rate"] = 0.0

        # 3. 智能协调器增强
        if intelligent_coordinator:
            try:
                ic_result = intelligent_coordinator.parse_only(
                    f"系统事件: {event.event_type}, 严重性: {event.severity}, 数据: {json.dumps(event.data, ensure_ascii=False)}"
                )
                ic_intent = ic_result.get("intent", {})
                ic_modules = ic_intent.get("modules_hint", [])
                # 如果智能协调器建议了额外模块, 添加为补充决策
                if ic_modules and ic_intent.get("confidence", 0) > 0.5:
                    m["ic_suggestion"] = {
                        "recommended_modules": ic_modules[:3],
                        "intent_type": ic_intent.get("intent_type", ""),
                        "confidence": ic_intent.get("confidence", 0),
                    }
            except Exception as e:
                logger.debug(f"[DecisionEngine] 智能协调器评估失败: {e}")

        # 4. 按综合评分排序: experience_score * 0.6 + priority_weight * 0.4
        priority_weight = {"critical": 100, "high": 75, "normal": 50, "low": 25}
        for m in matched:
            pw = priority_weight.get(m["priority"], 50)
            m["composite_score"] = round(
                m.get("experience_score", 50) * 0.6 + pw * 0.4, 1
            )
        matched.sort(key=lambda x: -x.get("composite_score", 0))

        return matched

    def get_experience_report(self) -> dict:
        """
        获取经验报告 — 所有规则的经验评分和优化建议
        """
        report = {
            "rules": [],
            "optimization_suggestions": [],
        }
        for rule in self._rules.values():
            score = self._experience_score(rule)
            trend = self._get_rule_trend(rule.id)
            avg_ms = self._get_rule_avg_duration(rule.id)

            rule_info = {
                "id": rule.id,
                "name": rule.name,
                "experience_score": score,
                "trend": "improving" if trend > 0.6 else ("degrading" if trend < 0.4 else "stable"),
                "trigger_count": rule.trigger_count,
                "success_rate": round(rule.success_count / max(rule.trigger_count, 1), 2),
                "avg_duration_ms": round(avg_ms),
                "enabled": rule.enabled,
            }
            report["rules"].append(rule_info)

            # 优化建议
            if score < 40 and rule.trigger_count >= 3:
                report["optimization_suggestions"].append({
                    "rule_id": rule.id,
                    "type": "low_score",
                    "message": f"规则 '{rule.name}' 经验分{score}分, 建议检查或禁用",
                    "severity": "warning",
                })
            if trend < 0.3 and rule.trigger_count >= 5:
                report["optimization_suggestions"].append({
                    "rule_id": rule.id,
                    "type": "degrading",
                    "message": f"规则 '{rule.name}' 成功率趋势恶化, 建议调整chain或threshold",
                    "severity": "warning",
                })
            if avg_ms > 20000:
                report["optimization_suggestions"].append({
                    "rule_id": rule.id,
                    "type": "slow",
                    "message": f"规则 '{rule.name}' 平均耗时{avg_ms:.0f}ms, 超过20s阈值",
                    "severity": "info",
                })

        report["rules"].sort(key=lambda x: -x["experience_score"])
        return report
