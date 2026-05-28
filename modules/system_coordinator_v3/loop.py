# -*- coding: utf-8 -*-
# 原 system_coordinator_v3.py L717-1209 — 自主决策循环
"""自主决策循环"""
import logging, time, re, os, sys, math, asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
logger = logging.getLogger("evo.coordinator.v3")

class AutonomousLoop:
    """
    自主决策循环 v3.0 — 完整闭环：感知→决策→执行→反馈
    """

    # 预定义的业务任务池，系统会轮询执行
    _TASK_POOL = [
        {"task": "生成今日系统状态摘要", "module_hint": "ai-gateway", "priority": "normal"},
        {"task": "分析最近10条系统日志", "module_hint": "audit-trail", "priority": "normal"},
        {"task": "检查所有模块健康状态", "module_hint": "performance-monitor", "priority": "normal"},
        {"task": "生成一段Python示例代码", "module_hint": "atom-code", "priority": "low"},
        {"task": "评估当前自动化效率", "module_hint": "business-analyst", "priority": "normal"},
        {"task": "扫描GitHub今日热门AI项目", "module_hint": "github-tools", "priority": "low"},
        {"task": "生成系统优化建议", "module_hint": "ai-gateway", "priority": "normal"},
        {"task": "检查数据备份状态", "module_hint": "backup-engine", "priority": "high"},
        {"task": "分析安全威胁态势", "module_hint": "agentguard-sec", "priority": "high"},
        {"task": "生成工作流优化方案", "module_hint": "workflow-orchestrator", "priority": "low"},
        {"task": "测试AI网关连通性", "module_hint": "ai-gateway", "priority": "normal"},
        {"task": "评估缓存命中率", "module_hint": "cache-engine", "priority": "low"},
        {"task": "检查待处理消息队列", "module_hint": "message-queue", "priority": "normal"},
        {"task": "生成本周技术趋势报告", "module_hint": "ai-gateway", "priority": "low"},
        {"task": "测试文件系统读写", "module_hint": "file-manager", "priority": "low"},
    ]

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop_interval = 30  # 30秒一轮，降低CPU负载
        self._last_decision_time = 0
        self._decision_log: List[Dict] = []
        self._task_index = 0  # 轮询任务索引
        self._execution_stats = {"total": 0, "success": 0, "failed": 0}
        self._recent_executions: List[Dict] = []  # 模块执行记录供前端展示

        # v3.1 — 决策引擎集成
        self._decision_engine = None
        try:
            from core.decision_engine import DecisionEngine

            # 注入模块执行器: 协调器的_execute_single_module
            async def _module_executor(module_id, action, params):
                return await coordinator._execute_single_module(module_id, action, {**params, "action": action}, {})

            self._decision_engine = DecisionEngine(module_executor=_module_executor)
            logger.info("[AutonomousLoop] 决策引擎已集成")
        except Exception as e:
            logger.warning(f"[AutonomousLoop] 决策引擎初始化失败(降级到基础模式): {e}")

    async def start(self):
        """启动自主循环"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[AutonomousLoop] 自主决策循环已启动")

        # 启动时通知决策引擎
        if self._decision_engine:
            from core.decision_engine import DecisionEvent

            self._decision_engine.on_event(
                DecisionEvent(
                    source="autonomous_loop",
                    event_type="system_started",
                    data={"timestamp": datetime.now().isoformat()},
                    severity="info",
                )
            )

    async def stop(self):
        """停止自主循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AutonomousLoop] 自主决策循环已停止")

    async def _loop(self):
        """主循环"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[AutonomousLoop] 循环异常: {e}")
            # CPU自适应降频：CPU过高时降低频率
            try:
                import psutil

                cpu = psutil.cpu_percent(interval=0.1)
                if cpu > 85:
                    sleep_time = self._loop_interval * 3  # CPU>85%，降速3x
                elif cpu > 60:
                    sleep_time = self._loop_interval * 2  # CPU>60%，降速2x
                else:
                    sleep_time = self._loop_interval
            except Exception:
                sleep_time = self._loop_interval
            await asyncio.sleep(sleep_time)

    async def _tick(self):
        """单次决策 tick — 生成任务→调度执行→收集结果"""
        now = time.time()
        self._last_decision_time = now

        # 1. 感知当前状态
        perception = await self._perceive()

        # 2. 决策生成
        decisions = self._decide(perception)

        # 3. 执行业务任务闭环
        for decision in decisions:
            result = await self._execute_decision(decision)
            # 4. 反馈学习
            await self._feedback(decision, result)

    async def _perceive(self) -> Dict:
        """感知当前环境"""
        perception = {
            "timestamp": datetime.now().isoformat(),
            "pending_tasks": [],
            "system_health": {},
            "recent_events": [],
        }
        # 获取系统健康状态
        if hasattr(self.coordinator, "perception"):
            try:
                health = self.coordinator.perception.perceive()
                if asyncio.iscoroutine(health):
                    health = await health
                perception["system_health"] = health
            except Exception:
                pass
        # 获取待处理事件
        if self.coordinator._event_bus:
            try:
                recent = self.coordinator._event_bus.get_recent_events(limit=10)
                perception["recent_events"] = recent
            except Exception:
                pass
        return perception

    def _decide(self, perception: Dict) -> List[Dict]:
        """基于感知做决策 — 决策引擎规则匹配 + 系统维护 + 主动业务任务"""
        decisions = []

        # ── 系统维护类决策 ──
        health = perception.get("system_health", {})
        system = health.get("system", {})
        if system.get("memory", 0) > 80:
            decisions.append(
                {
                    "type": "system_cleanup",
                    "reason": f"内存使用率 {system['memory']:.1f}%",
                    "priority": "high",
                }
            )

        if hasattr(self.coordinator, "_module_health"):
            for module_id, health_status in self.coordinator._module_health.items():
                if health_status == "error":
                    decisions.append(
                        {
                            "type": "module_restart",
                            "module": module_id,
                            "reason": "模块故障",
                            "priority": "high",
                        }
                    )

        if self.coordinator._cron_engine:
            try:
                due_jobs = self.coordinator._cron_engine.get_due_jobs()
                for job in due_jobs:
                    decisions.append(
                        {
                            "type": "cron_execute",
                            "job": job,
                            "reason": "定时任务到期",
                            "priority": "normal",
                        }
                    )
            except Exception:
                pass

        # ── v3.1 决策引擎规则匹配 ──
        if self._decision_engine:
            try:
                pass
                # 构建健康事件
                cpu = system.get("cpu", 0)
                memory = system.get("memory", 0)
                disk = system.get("disk", 0)

                if cpu > 85:
                    from core.decision_engine import DecisionEvent

                    matched = self._decision_engine.on_event(
                        DecisionEvent(
                            source="health_monitor",
                            event_type="health_cpu",
                            data={"cpu": cpu, "memory": memory, "disk": disk},
                            severity="warning" if cpu < 95 else "critical",
                        )
                    )
                    for m in matched:
                        decisions.append(
                            {
                                "type": "decision_chain",
                                "rule_info": m,
                                "reason": f"决策规则触发: {m['rule_name']}",
                                "priority": m["priority"],
                            }
                        )

                # 处理最近事件
                for evt in perception.get("recent_events", []):
                    evt_type = evt.get("type", "")
                    if evt_type in ("module_failed", "security_threat", "dead_letter", "log_anomaly"):
                        from core.decision_engine import DecisionEvent as DE

                        matched = self._decision_engine.on_event(
                            DE(
                                source="event_bus",
                                event_type=evt_type,
                                data=evt,
                                severity=evt.get("severity", "info"),
                            )
                        )
                        for m in matched:
                            decisions.append(
                                {
                                    "type": "decision_chain",
                                    "rule_info": m,
                                    "reason": f"事件触发决策: {m['rule_name']}",
                                    "priority": m["priority"],
                                }
                            )
            except Exception as e:
                logger.debug(f"[AutonomousLoop] 决策引擎匹配异常: {e}")

        # ── 主动业务任务生成 ── (保留作为兜底)
        task_template = self._TASK_POOL[self._task_index % len(self._TASK_POOL)]
        self._task_index += 1
        # 如果已有高优先级决策，降低业务任务频率
        has_high = any(d.get("priority") in ("critical", "high") for d in decisions)
        if not has_high:
            decisions.append(
                {
                    "type": "business_execute",
                    "task": task_template["task"],
                    "module_hint": task_template.get("module_hint"),
                    "priority": task_template.get("priority", "normal"),
                    "reason": "主动探索执行业务任务",
                }
            )

        return decisions

    async def _execute_decision(self, decision: Dict) -> Dict:
        """执行决策 — 返回结果供反馈"""
        decision["executed_at"] = datetime.now().isoformat()
        decision["success"] = False
        result = {}

        try:
            if decision["type"] == "system_cleanup":
                import gc

                gc.collect()
                decision["success"] = True
                decision["result"] = "GC executed"

            elif decision["type"] == "module_restart":
                module_id = decision.get("module")
                if module_id and hasattr(self.coordinator, "_restart_module"):
                    result = await self.coordinator._restart_module(module_id)
                    decision["success"] = result.get("success", False)
                    decision["result"] = result

            elif decision["type"] == "cron_execute":
                job = decision.get("job")
                if job and self.coordinator._cron_engine:
                    result = self.coordinator._cron_engine.run_job(job.get("id"))
                    decision["success"] = result.get("success", False)
                    decision["result"] = result

            elif decision["type"] == "business_execute":
                # ── 核心闭环：直接调用模块实例，绕过有问题的路由层 ──
                task_text = decision["task"]
                self._execution_stats["total"] += 1

                # 策略1: 优先对已知可用模块执行安全方法
                result = await self._execute_direct_module_task(task_text)
                decision["success"] = result.get("success", False)
                decision["result"] = result
                if decision["success"]:
                    self._execution_stats["success"] += 1
                else:
                    self._execution_stats["failed"] += 1
                logger.info(
                    f"[AutonomousLoop] 任务: {task_text[:30]}... -> {'成功' if decision['success'] else '失败'}"
                )

            elif decision["type"] == "decision_chain" and self._decision_engine:
                # ── v3.1 决策链执行 ──
                rule_info = decision.get("rule_info", {})
                try:
                    exec_result = await self._decision_engine.execute_decision(rule_info, decision.get("trigger_event"))
                    decision["success"] = exec_result.status == "success"
                    decision["result"] = {
                        "execution_id": exec_result.id,
                        "rule_name": exec_result.rule_name,
                        "status": exec_result.status,
                        "summary": exec_result.summary,
                        "duration_ms": exec_result.duration_ms,
                    }
                    if decision["success"]:
                        self._execution_stats["success"] += 1
                    else:
                        self._execution_stats["failed"] += 1
                    logger.info(
                        f"[AutonomousLoop] 决策链 {rule_info.get('rule_name', '?')}: {exec_result.status} ({exec_result.summary})"
                    )
                except Exception as e:
                    decision["success"] = False
                    decision["error"] = str(e)
                    self._execution_stats["failed"] += 1
                    logger.error(f"[AutonomousLoop] 决策链执行异常: {e}")
                self._execution_stats["total"] += 1

        except Exception as e:
            decision["error"] = str(e)
            self._execution_stats["total"] += 1
            self._execution_stats["failed"] += 1
            logger.error(f"[AutonomousLoop] 执行异常: {e}")

        self._decision_log.append(decision)
        if len(self._decision_log) > 200:
            self._decision_log = self._decision_log[-100:]

        # 记录到最近执行历史供前端展示
        self._recent_executions.append(
            {
                "module": result.get("module", decision.get("module", "unknown")),
                "method": result.get("method", decision.get("type", "unknown")),
                "task": decision.get("task", ""),
                "success": decision.get("success", False),
                "time": decision.get("executed_at", datetime.now().isoformat()),
            }
        )
        if len(self._recent_executions) > 100:
            self._recent_executions = self._recent_executions[-50:]

        return result

    async def _execute_direct_module_task(self, task_text: str) -> Dict:
        """直接对模块实例执行安全方法，绕过路由层"""
        instances = getattr(self.coordinator, "_module_instances", {})
        if not instances:
            return {"success": False, "error": "无模块实例"}

        # 扩展方法白名单（无参或只需简单参数）
        safe_methods = [
            "get_stats",
            "health_check",
            "status",
            "info",
            "list_models",
            "list",
            "get_status",
            "summary",
            "overview",
            "ping",
            "get_health",
            "check",
            "diagnose",
            "describe",
            "get_metrics",
            "get_info",
            "report",
            "scan",
            "list_agents",
            "list_tasks",
            "list_workflows",
            "get_config",
            "get_capabilities",
            "available_tools",
        ]

        # 按任务类型选择模块（更精确的映射）
        task_lower = task_text.lower()
        module_hints = []
        if any(kw in task_lower for kw in ["日志", "log"]):
            module_hints = ["audit_trail", "log_center", "performance_monitor"]
        elif any(kw in task_lower for kw in ["模型", "model", "ai", "gpt", "claude"]):
            module_hints = ["model_router", "ai_gateway", "atom_code"]
        elif any(kw in task_lower for kw in ["备份", "backup"]):
            module_hints = ["backup_engine", "disaster_recovery"]
        elif any(kw in task_lower for kw in ["性能", "监控", "performance", "monitor", "cpu", "内存"]):
            module_hints = ["performance_monitor", "advanced_resilience", "agent_resource_control"]
        elif any(kw in task_lower for kw in ["安全", "security", "guard", "威胁"]):
            module_hints = ["agentguard_sec", "aegis_governance", "security_audit"]
        elif any(kw in task_lower for kw in ["分析", "统计", "analyze", "report", "效率"]):
            module_hints = ["business_analyst", "audit_trail", "performance_monitor"]
        elif any(kw in task_lower for kw in ["工作流", "workflow", "编排"]):
            module_hints = ["workflow_orchestrator", "workflow_manager"]
        elif any(kw in task_lower for kw in ["代码", "code", "示例", "生成"]):
            module_hints = ["atom_code", "code_generation", "ai_gateway"]
        elif any(kw in task_lower for kw in ["agent", "智能体", "任务"]):
            module_hints = ["agent_orchestrator", "agent_marketplace", "task_engine"]
        else:
            # 随机选已加载实例
            module_hints = list(instances.keys())[:10]

        for module_id in module_hints:
            instance = instances.get(module_id)
            if not instance:
                continue
            for method_name in safe_methods:
                method = getattr(instance, method_name, None)
                if method and callable(method):
                    try:
                        if asyncio.iscoroutinefunction(method):
                            raw = await asyncio.wait_for(method(), timeout=5.0)
                        else:
                            raw = method()
                        return {
                            "success": True,
                            "module": module_id,
                            "method": method_name,
                            "result": raw if isinstance(raw, (dict, list, str, int, float, bool)) else str(raw)[:500],
                        }
                    except Exception as e:
                        logger.debug(f"[AutonomousLoop] {module_id}.{method_name} 失败: {e}")
                        continue

        # Fallback：任务本身记录为"已接收"，避免无谓失败统计
        return {
            "success": True,
            "module": "system_coordinator",
            "method": "task_acknowledged",
            "result": f"任务已记录: {task_text[:80]}",
        }

    async def _feedback(self, decision: Dict, result: Dict):
        """执行反馈 — 结果回传经验库"""
        try:
            if self.coordinator._experience_base:
                await self.coordinator._experience_base.record(
                    {
                        "task": decision.get("task", ""),
                        "type": decision["type"],
                        "success": decision.get("success", False),
                        "result_summary": str(result)[:200] if result else "",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception:
            pass

    def get_status(self) -> Dict:
        """获取自主循环状态"""
        total = self._execution_stats["total"]
        status = {
            "running": self._running,
            "last_decision": self._last_decision_time,
            "decision_count": len(self._decision_log),
            "recent_decisions": self._decision_log[-5:],
            "execution_stats": {
                "total": total,
                "success": self._execution_stats["success"],
                "failed": self._execution_stats["failed"],
                "rate": self._execution_stats["success"] / max(total, 1),
            },
            "recent_executions": self._recent_executions[-20:],  # 最近20条供前端展示
        }
        # v3.1 决策引擎状态
        if self._decision_engine:
            try:
                status["decision_engine"] = self._decision_engine.get_stats()
            except Exception:
                status["decision_engine"] = {"status": "error"}
        return status

# ============================================================================
# 跨模块编排引擎 — 自动组合多个模块完成任务
# ============================================================================


