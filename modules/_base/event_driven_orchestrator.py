"""
AUTO-EVO-AI v7.0 — 事件驱动编排层
=====================================
上市公司生产级实现 — EventBus ↔ TriggerEngine ↔ OrchestrationEngine 联动

架构:
  模块执行完成 → EventBus.publish("pipeline.step.complete", data)
                    ↓
              EventDrivenOrchestrator (本模块)
                    ↓ 检查 __module_meta__.triggers
                    ↓
              TriggerEngine.register_event() 自动订阅
                    ↓ 事件匹配
              TriggerScheduler.match_event() → fire()
                    ↓
              OrchestrationEngine.execute_pipeline() 执行下游模块
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.module_meta import ModuleMeta, ModuleRegistry, ModuleTrigger
from modules._base.orchestration_engine import (
    OrchestrationEngine, ExecutionMode, PipelineResult, PipelineStatus,
)

logger = logging.getLogger("evo.event_driven")


# ============================================================
# 事件驱动编排器
# ============================================================

class EventDrivenOrchestrator:
    """事件驱动编排器——连接 EventBus、TriggerEngine、OrchestrationEngine

    核心流程:
      1. 扫描模块注册表，提取所有 event 类型的 trigger 定义
      2. 为每个 trigger 在 EventBus 上注册监听
      3. 事件到来 → 匹配条件 → 触发 OrchestrationEngine 执行下游流水线
      4. 管理 Cron 守护线程，定时触发 scheduled 模块
      5. 记录所有事件→动作的关联，支持查询

    用法:
        edo = EventDrivenOrchestrator(event_bus, trigger_engine, orch_engine)
        await edo.start()        # 启动监听
        await edo.stop()         # 停止
        await edo.rebuild()      # 重新扫描模块元数据，重建订阅
    """

    # 系统事件命名空间
    NS_PIPELINE = "pipeline."
    NS_MODULE = "module."
    NS_SYSTEM = "system."
    NS_ALL = "*"  # 通配符订阅

    def __init__(
        self,
        event_bus: Any,
        trigger_engine: Any,
        orch_engine: OrchestrationEngine,
        registry: Optional[ModuleRegistry] = None,
    ):
        self._event_bus = event_bus
        self._trigger_engine = trigger_engine
        self._orch = orch_engine
        self._registry = registry or ModuleRegistry()

        # 运行时状态
        self._running = False
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._event_stats: Dict[str, int] = defaultdict(int)
        self._event_history: List[dict] = []
        self._max_history = 1000

        # Cron 守护
        self._cron_task: Optional[asyncio.Task] = None
        self._cron_interval = 30  # 秒，每30秒检查一次

        # 锁
        self._lock = asyncio.Lock()

        logger.info("EventDrivenOrchestrator 初始化完成")

    # ── 生命周期 ──

    async def start(self):
        """启动事件驱动编排器"""
        if self._running:
            logger.warning("EventDrivenOrchestrator 已在运行")
            return
        self._running = True

        # 1. 重建所有订阅
        await self.rebuild()

        # 2. 启动 Cron 守护任务
        self._cron_task = asyncio.create_task(self._cron_loop())

        stats = self._event_stats
        logger.info(
            f"EventDrivenOrchestrator 已启动: "
            f"{len(self._subscriptions)} 订阅, "
            f"{len(self._registry.get_scheduled())} 定时模块"
        )

    async def stop(self):
        """停止事件驱动编排器"""
        self._running = False
        if self._cron_task:
            self._cron_task.cancel()
            self._cron_task = None

        # 清除订阅
        self._subscriptions.clear()
        logger.info("EventDrivenOrchestrator 已停止")

    async def rebuild(self):
        """重新扫描模块元数据，重建事件订阅"""
        async with self._lock:
            self._subscriptions.clear()
            modules = self._registry.get_all()
            registered = 0

            for meta in modules:
                for trigger in meta.triggers:
                    if trigger.type == "event":
                        self._subscribe_event_trigger(meta, trigger)
                        registered += 1

            logger.info(f"事件订阅重建完成: {len(modules)} 模块, {registered} 事件触发器")

    # ── 内部: 事件订阅 ──

    def _subscribe_event_trigger(self, meta: ModuleMeta, trigger: ModuleTrigger):
        """为单个模块的 event 触发器注册监听"""
        event_name = trigger.config.get("on", "")
        if not event_name:
            return

        condition = trigger.config.get("condition", {})

        async def event_handler(event_data: dict):
            """事件回调——匹配条件后执行模块"""
            await self._handle_event(meta, event_name, event_data, condition)

        # 注册到 EventBus
        self._event_bus.subscribe(event_name, event_handler)
        self._subscriptions[event_name].append(event_handler)

        logger.debug(f"事件订阅: {meta.id} ← {event_name}")

    async def _handle_event(
        self, meta: ModuleMeta, event_name: str, event_data: dict, condition: dict
    ):
        """处理事件——条件匹配后触发模块执行"""
        event_id = event_data.get("id", uuid.uuid4().hex[:8])
        payload = event_data.get("data", {})

        # 记录事件
        async with self._lock:
            self._event_stats[event_name] += 1
            self._event_history.append({
                "event_id": event_id,
                "event_type": event_name,
                "target_module": meta.id,
                "source": event_data.get("source", ""),
                "timestamp": datetime.now().isoformat(),
            })
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

        # 条件过滤
        if condition:
            from modules.trigger_engine import ConditionEvaluator
            evaluator = ConditionEvaluator()
            if not evaluator.evaluate(condition, payload):
                logger.debug(f"事件 {event_name} 条件不匹配，跳过 {meta.id}")
                return

        # 执行目标模块
        logger.info(f"事件驱动触发: {event_name} → {meta.id}")
        try:
            result = await self._orch.execute_pipeline(
                [meta.id],
                params=payload,
                mode=ExecutionMode.RESILIENT,
            )
            logger.info(
                f"事件驱动执行完成: {meta.id} "
                f"success={result.success} "
                f"duration={result.duration_ms:.0f}ms"
            )
        except Exception as e:
            logger.error(f"事件驱动执行失败: {meta.id} → {e}")

    # ── Cron 守护 ──

    async def _cron_loop(self):
        """Cron 检查循环——定时触发 scheduled 模块"""
        while self._running:
            try:
                now = datetime.now()
                scheduled = self._registry.get_scheduled()

                for meta in scheduled:
                    for trigger in meta.triggers:
                        if trigger.type == "schedule":
                            cron_expr = trigger.config.get("cron", "")
                            if cron_expr and self._cron_matches(cron_expr, now):
                                logger.info(f"Cron触发: {meta.id} ({cron_expr})")
                                asyncio.create_task(
                                    self._orch.execute_pipeline(
                                        [meta.id],
                                        params={},
                                        mode=ExecutionMode.RESILIENT,
                                    )
                                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cron检查异常: {e}")

            await asyncio.sleep(self._cron_interval)

    @staticmethod
    def _cron_matches(cron_expr: str, dt: datetime) -> bool:
        """检查 cron 表达式是否匹配当前时间（分钟级精度）"""
        try:
            from modules.trigger_engine import CronExpression
            cron = CronExpression(cron_expr)
            return cron.matches(dt)
        except Exception:
            return False

    # ── 注册系统级事件监听（供外部调用） ──

    def on_pipeline_start(self, handler: Callable):
        """监听流水线启动事件"""
        self._event_bus.subscribe(f"{self.NS_PIPELINE}start", handler)

    def on_pipeline_complete(self, handler: Callable):
        """监听流水线完成事件"""
        self._event_bus.subscribe(f"{self.NS_PIPELINE}complete", handler)

    def on_module_execute(self, handler: Callable):
        """监听模块执行事件"""
        self._event_bus.subscribe(f"{self.NS_MODULE}execute", handler)

    def on_system_event(self, handler: Callable):
        """监听系统事件"""
        self._event_bus.subscribe(f"{self.NS_SYSTEM}*", handler)

    # ── 工具方法 ──

    async def emit_event(self, event_type: str, data: Any = None, source: str = ""):
        """手动发射事件（用于模块间通信）"""
        if self._event_bus and hasattr(self._event_bus, "publish"):
            await self._event_bus.publish(event_type, data=data, source=source)

    def get_stats(self) -> dict:
        return {
            "running": self._running,
            "subscriptions": len(self._subscriptions),
            "total_modules": self._registry.count(),
            "scheduled_modules": len(self._registry.get_scheduled()),
            "event_driven_modules": len(self._registry.get_triggered_by_event("")),
            "event_stats": dict(self._event_stats),
            "event_history_size": len(self._event_history),
        }

    def get_event_history(self, limit: int = 50) -> List[dict]:
        return self._event_history[-limit:]

    def get_module_trigger_map(self) -> dict:
        """返回 事件 → [模块ID] 的映射"""
        mapping: Dict[str, List[str]] = defaultdict(list)
        for meta in self._registry.get_all():
            for trigger in meta.triggers:
                if trigger.type == "event":
                    event_name = trigger.config.get("on", "")
                    if event_name:
                        mapping[event_name].append(meta.id)
                elif trigger.type == "schedule":
                    cron = trigger.config.get("cron", "")
                    if cron:
                        key = f"cron:{cron}"
                        mapping[key].append(meta.id)
        return dict(mapping)


# ============================================================
# 协程管道执行器 (整合 EventBus + OrchestrationEngine)
# ============================================================

class PipelineEventBridge:
    """管道事件桥接——让 OrchestrationEngine 的每一步都发出事件

    用法:
        bridge = PipelineEventBridge(event_bus)
        result = await bridge.execute_with_events(
            orch_engine, module_ids, params
        )
        # → 每个步骤自动发 event 到 EventBus
    """

    def __init__(self, event_bus: Any):
        self._event_bus = event_bus
        self._active_pipelines: Dict[str, dict] = {}

    async def execute_with_events(
        self,
        orch: OrchestrationEngine,
        module_ids: List[str],
        params: dict = None,
        mode: ExecutionMode = ExecutionMode.RESILIENT,
    ) -> PipelineResult:
        """执行流水线，每一步自动发出事件"""
        pipeline_id = uuid.uuid4().hex[:12]

        # 发布流水线开始事件
        await self._emit("pipeline.start", {
            "pipeline_id": pipeline_id,
            "modules": module_ids,
            "mode": mode.value,
            "params": params,
        })

        # 执行
        result = await orch.execute_pipeline(module_ids, params or {}, mode)

        # 发布每一步的事件
        for step in result.steps:
            await self._emit("pipeline.step.complete", {
                "pipeline_id": pipeline_id,
                "module_id": step.module_id,
                "success": step.success,
                "duration_ms": step.duration_ms,
                "mode": mode.value,
                "error": step.error,
            })

        # 发布流水线结束事件
        await self._emit("pipeline.complete", {
            "pipeline_id": pipeline_id,
            "modules": module_ids,
            "success": result.success,
            "total_duration_ms": result.duration_ms,
            "success_count": sum(1 for s in result.steps if s.success),
            "total_count": len(result.steps),
        })

        return result

    async def _emit(self, event_type: str, data: dict):
        """发射事件到 EventBus"""
        try:
            if self._event_bus and hasattr(self._event_bus, "publish"):
                await self._event_bus.publish(
                    event_type, data=data, source="PipelineEventBridge"
                )
        except Exception as e:
            logger.debug(f"事件发射失败 {event_type}: {e}")

    def get_active_pipelines(self) -> List[dict]:
        return list(self._active_pipelines.values())


# ============================================================
# 快捷工厂
# ============================================================

async def create_event_driven_system(
    event_bus: Any,
    trigger_engine: Any,
    orch_engine: OrchestrationEngine,
    registry: Optional[ModuleRegistry] = None,
) -> Tuple[EventDrivenOrchestrator, PipelineEventBridge]:
    """一键创建事件驱动系统并启动"""
    if registry is None:
        registry = ModuleRegistry()

    orchestrator = EventDrivenOrchestrator(event_bus, trigger_engine, orch_engine, registry)
    bridge = PipelineEventBridge(event_bus)

    await orchestrator.start()
    logger.info("事件驱动系统已启动")

    return orchestrator, bridge


__all__ = [
    "EventDrivenOrchestrator", "PipelineEventBridge",
    "create_event_driven_system",
]
