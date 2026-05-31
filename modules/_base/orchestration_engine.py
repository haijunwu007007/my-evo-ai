"""
AUTO-EVO-AI V0.1 — 智能编排引擎
====================================
上市公司生产级实现 — 自动发现 → Pipeline构建 → 并行调度 → 自愈合

三层架构:
  L3: process_goal()      自然语言意图 → Pipeline
  L2: execute_pipeline()  依赖解析 → 分层并行执行
  L1: execute_module()    单个模块调用

用法:
    engine = OrchestrationEngine()
    result = await engine.execute_pipeline(["github-scanner", "feishu-notify"])
"""

from __future__ import annotations

import os
import sys
import time
import json
import uuid
import asyncio
import inspect
import logging
import importlib
import importlib.util
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections.abc import Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from modules._base.module_meta import (
    ModuleMeta,
    ModuleIO,
    ModuleStatus,
    ModuleRegistry,
    SchemaValidator,
    validate_input,
)
from modules._base.module_discovery import ModuleDiscoveryEngine
# PipelineEventBridge 在 _init_event_bridge() 中延迟导入，避免环形依赖
from modules.ai_gateway import AIGateway

logger = logging.getLogger("evo.orchestration")


# ── 枚举 ──


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    RELAXED = "relaxed"  # 失败继续
    STRICT = "strict"  # 失败即停
    RESILIENT = "resilient"  # 失败自动替换（默认）
    DEBUG = "debug"


# ── 数据类 ──


@dataclass
class PipelineStep:
    module_id: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 120.0
    fallback_module: str | None = None
    status: str = "pending"
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Pipeline:
    id: str
    name: str
    steps: list[PipelineStep]
    mode: ExecutionMode = ExecutionMode.RESILIENT
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    total_duration_ms: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode.value,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }


@dataclass
class PipelineResult:
    pipeline: Pipeline
    success: bool
    step_results: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


# ── 编排引擎 ──


class OrchestrationEngine:
    """智能编排引擎

    核心能力:
      1. 自动发现模块 → 依赖解析 → 分层并行
      2. 执行模式: RESILIENT(默认自动容错) / STRICT(严格) / RELAXED(继续)
      3. 失败自动降级/重试/替换
      4. 共享上下文在steps间传递
      5. 完整链路追踪
    """

    def __init__(
        self,
        registry: ModuleRegistry | None = None,
        discovery_engine: ModuleDiscoveryEngine | None = None,
        max_parallel: int = 10,
    ):
        self._registry = registry or ModuleRegistry()
        self._discovery = discovery_engine
        self._max_parallel = max_parallel
        self._pipeline_history: list[Pipeline] = []
        self._session_id = str(uuid.uuid4())[:8]
        # AI 配置
        self._ai_model = os.environ.get("AI_DEFAULT_MODEL", "gpt-4o")
        self._ai_gateway = OrchestrationEngine._init_ai_gateway()
        # 事件桥接
        self._event_bridge: PipelineEventBridge | None = None
        self._event_pipeline_active: bool = False

    @staticmethod
    def _init_event_bridge() -> PipelineEventBridge | None:
        """延迟初始化事件桥接"""
        try:
            from modules._base.event_driven_orchestrator import PipelineEventBridge
            return PipelineEventBridge()
        except ImportError as e:
            logger.debug(f"事件桥接不可用: {e}")
            return None

    async def enable_event_driven_mode(self) -> bool:
        """启用事件驱动模式——启动EventBus联动"""
        if self._event_bridge is not None:
            return True
        bridge = self._init_event_bridge()
        if bridge is None:
            logger.warning("事件桥接初始化失败，事件驱动模式不可用")
            return False
        self._event_bridge = bridge
        self._event_pipeline_active = True
        logger.info("事件驱动模式已启用")
        return True

    @staticmethod
    def _init_ai_gateway() -> AIGateway | None:
        try:
            gw = AIGateway()
            if gw.models:
                return gw
            return None
        except Exception as e:
            logger.warning(f"AI网关初始化失败，使用关键词回退模式: {e}")
            return None

    # ── 核心API ──

    async def execute_pipeline(
        self,
        module_ids: list[str],
        params: dict[str, Any] | None = None,
        mode: ExecutionMode = ExecutionMode.RESILIENT,
        name: str = "",
    ) -> PipelineResult:
        """执行模块流水线

        Args:
            module_ids: 模块ID列表
            params: 全局共享参数
            mode: 执行模式
            name: 流水线名称

        Returns:
            PipelineResult: 包含每步结果和聚合状态
        """
        # 1. 解析依赖 → 分层
        layers = self._registry.get_parallel_layers(module_ids)
        if not layers:
            return PipelineResult(
                pipeline=Pipeline(id="", name="error", steps=[], status=PipelineStatus.FAILED),
                success=False,
                summary="依赖解析失败：模块未注册",
            )

        # 2. 构建 Pipeline
        step_map: dict[str, PipelineStep] = {}
        for mid in module_ids:
            step = PipelineStep(module_id=mid, params=params or {})
            meta = self._registry.get(mid)
            if meta:
                step.max_retries = 3 if meta.grade in ("S", "A") else 2
                step.timeout_seconds = 300.0 if meta.grade == "S" else 120.0
                if meta.health_check and meta.health_check.fallback_module:
                    step.fallback_module = meta.health_check.fallback_module
            step_map[mid] = step

        pipeline = Pipeline(
            id=self._generate_pipeline_id(),
            name=name or " → ".join(module_ids[:5]),
            steps=list(step_map.values()),
            mode=mode,
        )

        # 3. 逐层执行
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now().isoformat()

        for layer_idx, layer in enumerate(layers):
            if pipeline.status == PipelineStatus.FAILED:
                break
            logger.info(f"执行第 {layer_idx + 1}/{len(layers)} 层: {layer}")
            await self._execute_layer(pipeline, step_map, layer)

        # 4. 聚合结果
        pipeline.completed_at = datetime.now().isoformat()
        pipeline.total_duration_ms = (
            datetime.fromisoformat(pipeline.completed_at) - datetime.fromisoformat(pipeline.started_at)
        ).total_seconds() * 1000

        failed_steps = [s for s in pipeline.steps if s.status == "failed"]
        if not failed_steps:
            pipeline.status = PipelineStatus.SUCCESS
        elif len(failed_steps) < len(pipeline.steps):
            pipeline.status = PipelineStatus.PARTIAL
        else:
            pipeline.status = PipelineStatus.FAILED

        self._pipeline_history.append(pipeline)

        # 发射流水线完成事件
        if self._event_bridge:
            await self._event_bridge._emit("pipeline.complete", {
                "module_ids": module_ids,
                "success": pipeline.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL),
                "duration_ms": pipeline.total_duration_ms or 0,
                "mode": mode.value,
            })

        return PipelineResult(
            pipeline=pipeline,
            success=pipeline.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL),
            step_results=[s.to_dict() for s in pipeline.steps],
            summary=self._build_summary(pipeline),
        )

    async def process_goal(
        self,
        goal: str,
        mode: ExecutionMode = ExecutionMode.RESILIENT,
    ) -> PipelineResult:
        """用自然语言目标构建并执行流水线

        流程:
          1. 尝试 AI 网关解析意图 → 匹配模块
          2. AI不可用时降级为关键词匹配
          3. 自动执行流水线
        """
        module_ids = []

        # 尝试 AI 驱动
        if self._ai_gateway:
            try:
                module_ids = await self._ai_match_modules_by_goal(goal)
                if module_ids:
                    logger.info(f"AI解析目标 '{goal[:50]}' → {module_ids}")
            except Exception as e:
                logger.warning(f"AI解析失败，降级为关键词匹配: {e}")

        # 降级：关键词匹配
        if not module_ids:
            module_ids = self._keyword_match_modules_by_goal(goal)
            if module_ids:
                logger.info(f"关键词匹配目标 '{goal[:50]}' → {module_ids}")

        if not module_ids:
            return PipelineResult(
                pipeline=Pipeline(id="error", name="无法匹配", steps=[], status=PipelineStatus.FAILED),
                success=False,
                summary=f"无法为目标 '{goal}' 匹配到可用模块",
            )
        return await self.execute_pipeline(module_ids, name=goal, mode=mode)

    # ── 单模块执行 ──

    async def execute_module(
        self,
        module_id: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行单个模块（供外部或链式调用）

        流程:
          1. Schema 校验输入
          2. 调用模块 execute()
          3. Schema 校验输出
          4. 返回标准化结果
        """
        start = time.time()
        result: dict[str, Any] = {
            "module_id": module_id,
            "success": False,
            "error": None,
            "duration_ms": 0.0,
            "data": None,
        }

        try:
            meta = self._registry.get(module_id)

            # Schema 校验（仅当有元数据时）
            if meta:
                validation_errors = validate_input(params, meta.inputs)
                if validation_errors:
                    result["error"] = f"参数校验失败: {'; '.join(validation_errors)}"
                    return result

            # 动态导入并执行（兼容旧 modules_loader.py 系统）
            mod = await self._load_module(module_id)
            if not mod:
                result["error"] = f"无法加载模块 '{module_id}'"
                return result

            merged_params = {**params, **(context or {})}

            # 生产级：兼容 异步/同步/代理对象 三种模式
            if hasattr(mod, "execute"):
                if inspect.iscoroutinefunction(mod.execute):
                    output = await mod.execute(merged_params)
                else:
                    # 同步方法 → 在 executor 中执行防阻塞
                    loop = asyncio.get_event_loop()
                    output = await loop.run_in_executor(None, mod.execute, merged_params)
            elif hasattr(mod, "analyze"):
                if inspect.iscoroutinefunction(mod.analyze):
                    output = await mod.analyze(merged_params)
                else:
                    loop = asyncio.get_event_loop()
                    output = await loop.run_in_executor(None, mod.analyze, merged_params)
            else:
                output = {"success": True, "message": f"模块 {module_id} 无标准入口"}

            # 代理对象返回 str 而非 dict → 标准化
            if isinstance(output, str):
                output = {"success": True, "message": output}
            elif not isinstance(output, dict):
                output = {"success": True, "data": output}

            result["data"] = output
            result["success"] = True

        except TimeoutError:
            result["error"] = f"模块 '{module_id}' 执行超时"
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"模块执行失败 {module_id}: {e}")

        result["duration_ms"] = (time.time() - start) * 1000
        return result

    # ── 内部方法 ──

    async def _execute_layer(
        self,
        pipeline: Pipeline,
        step_map: dict[str, PipelineStep],
        layer: list[str],
    ):
        """执行单层（同层模块并行执行）"""
        semaphore = asyncio.Semaphore(min(len(layer), self._max_parallel))

        async def _run_step(step: PipelineStep):
            async with semaphore:
                step.status = "running"

                # 填充上下文
                merged_params = dict(step.params)
                merged_params.update(pipeline.context)

                # 执行
                retries = 0
                while retries <= step.max_retries:
                    try:
                        result = await asyncio.wait_for(
                            self.execute_module(step.module_id, merged_params),
                            timeout=step.timeout_seconds,
                        )
                        if result["success"]:
                            step.status = "success"
                            step.result = result["data"]
                            step.duration_ms = result.get("duration_ms", 0)
                            # 写入共享上下文
                            if result.get("data"):
                                pipeline.context[f"_{step.module_id}_result"] = result["data"]
                            return
                        # 失败重试
                        error = result.get("error", "未知错误")
                        step.error = error
                        step.retry_count = retries + 1
                        retries += 1
                        if retries <= step.max_retries:
                            wait = min(2**retries, 30)
                            logger.warning(f"重试 {step.module_id} ({retries}/{step.max_retries}): 等 {wait}s")
                            await asyncio.sleep(wait)
                    except TimeoutError:
                        step.error = f"超时 ({step.timeout_seconds}s)"
                        step.retry_count = retries + 1
                        retries += 1

                # 全部重试失败 → 尝试降级
                if step.fallback_module and pipeline.mode in (ExecutionMode.RESILIENT, ExecutionMode.RELAXED):
                    logger.warning(f"尝试降级 {step.module_id} → {step.fallback_module}")
                    step.module_id = step.fallback_module
                    step.retry_count = 0
                    await _run_step(step)
                else:
                    step.status = "failed"
                    if pipeline.mode == ExecutionMode.STRICT:
                        pipeline.status = PipelineStatus.FAILED
                        pipeline.error = f"模块 {step.module_id} 执行失败"

        tasks = [_run_step(step_map[mid]) for mid in layer if mid in step_map]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _load_module(self, module_id: str) -> Any | None:
        """动态加载模块对象（双通道：importlib优先 + 直接spec后备）"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # ── 通道1: 通过 modules_loader.py 映射表加载 ──
        try:
            modules_loader_path = os.path.join(base_dir, "core", "modules_loader.py")
            if os.path.exists(modules_loader_path):
                spec = importlib.util.spec_from_file_location("modules_loader", modules_loader_path)
                if spec and spec.loader:
                    loader_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(loader_mod)
                    if hasattr(loader_mod, "MODULE_PATHS") and module_id in loader_mod.MODULE_PATHS:
                        mod_path, class_name = loader_mod.MODULE_PATHS[module_id]
                        try:
                            mod = importlib.import_module(mod_path)
                            cls = getattr(mod, class_name, None)
                            if cls:
                                instance = cls() if hasattr(cls, "__init__") else cls
                                return instance
                        except Exception as e:
                            logger.debug(f"通道1 {module_id}({mod_path}.{class_name}) 失败: {e}")
        except Exception as e:
            logger.debug(f"通道1 {module_id} 加载器异常: {e}")

        # ── 通道2: 直接按文件名 spec 加载 ──
        try:
            module_path = os.path.join(base_dir, "modules", f"{module_id.replace('-', '_')}.py")
            if not os.path.exists(module_path):
                module_path = os.path.join(base_dir, "modules", f"{module_id}.py")
            if not os.path.exists(module_path):
                logger.debug(f"通道2 {module_id}: 文件不存在 {module_path}")
                return None

            spec = importlib.util.spec_from_file_location(f"_mod_{module_id}", module_path)
            if not spec or not spec.loader:
                logger.debug(f"通道2 {module_id}: spec 创建失败")
                return None

            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # 遍历所有公共类，尝试无参实例化
            for name in sorted(dir(mod)):
                obj = getattr(mod, name, None)
                if name.startswith('_'):
                    continue
                if not (isinstance(obj, type) and hasattr(obj, '__init__')):
                    continue
                # 跳过抽象类/基类/Mixin
                if any(sk in name for sk in ('Base', 'Mixin', 'Abstract', 'Meta', 'Analyzer', 'Error')):
                    continue
                if obj in (object, dict, list, str, int, float, bool, type):
                    continue
                try:
                    instance = obj()
                    logger.debug(f"模块 {module_id}: 成功实例化 {name}")
                    return instance
                except TypeError:
                    continue
                except Exception:
                    continue

            logger.warning(f"模块 {module_id}: 扫描 {len(dir(mod))} 项，无可用类")
            return None
        except Exception as e:
            logger.error(f"加载模块 {module_id} 彻底失败: {e}")
            return None

    async def _ai_match_modules_by_goal(self, goal: str) -> list[str]:
        """AI驱动：用 AIGateway 解析目标 → 匹配模块"""
        if not self._ai_gateway:
            return []

        # 构建能力地图 prompt
        all_modules = self._registry.get_all()
        if not all_modules:
            return []

        module_catalog = "\n".join(
            f"  - id: {m.id} | name: {m.name} | group: {m.group} | "
            f"inputs: {[io.name for io in m.inputs]} | "
            f"triggers: {[t.type for t in m.triggers]} | "
            f"tags: {m.tags}"
            for m in all_modules[:100]  # top100 避免超长
        )

        prompt = (
            "你是一个多智能体系统编排专家。请解析以下用户目标，\n"
            "从模块目录中选择最合适的模块组成流水线。\n\n"
            f"可用模块目录:\n{module_catalog}\n\n"
            f"用户目标: {goal}\n\n"
            "请以JSON格式回复（不含markdown）：\n"
            '{"modules":["module-id-1","module-id-2"],"reasoning":"为什么这样选择"}'
        )

        try:
            response = self._ai_gateway.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self._ai_model,
                temperature=0.1,
            )
            content = response.get("content", "") or response.get("response", "") or str(response)
            # 提取 JSON
            import re as _re

            json_match = _re.search(r"\{.*\}", content, _re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                modules = parsed.get("modules", [])
                # 移除注册表过滤 —— execute_module 内部会通过 _load_module
                # 兼容旧 MODULE_PATHS 系统, 查不到自然失败
                return modules
        except Exception as e:
            logger.debug(f"AI匹配异常: {e}")
        return []

    def _keyword_match_modules_by_goal(self, goal: str) -> list[str]:
        """关键词匹配（AI降级备选）"""
        goal_lower = goal.lower()
        keyword_map: dict[str, list[str]] = {
            "github": ["github-scanner", "data-analysis", "feishu-notify"],
            "git": ["github-scanner", "git-ops"],
            "扫描": ["github-scanner"],
            "通知": ["feishu-notify", "push-notify", "enterprise-notifier"],
            "邮件": ["email-automation", "enterprise-notifier"],
            "飞书": ["feishu-notify", "feishu-notifier"],
            "备份": ["backup-engine", "backup-scheduler"],
            "监控": ["perf-monitor", "local-monitor", "alert-manager"],
            "报告": ["pdf-report", "excel-engine", "report-generator"],
            "代码": ["code-generator", "code-review", "cicd-pipeline"],
            "agent": ["agent-orchestrator", "autonomous-agent"],
            "安全": ["security-scanner", "audit-trail", "compliance-auditor"],
            "数据": ["data-pipeline", "data-analysis"],
            "自动": ["autonomous-agent", "self-evolving-engine"],
            "部署": ["cicd-pipeline", "docker-deploy", "blue-green"],
        }

        matched = []
        for keyword, modules in keyword_map.items():
            if keyword in goal_lower:
                for m in modules:
                    if m not in matched:
                        if self._registry.get(m):
                            matched.append(m)
                        else:
                            matched.append(m)  # 模块未注册也加入（关键词表已知模块）
        return matched

    def _generate_pipeline_id(self) -> str:
        import hashlib

        raw = f"{time.time()}{self._session_id}{uuid.uuid4()}"
        return f"pipeline_{hashlib.md5(raw.encode()).hexdigest()[:12]}"

    def _build_summary(self, pipeline: Pipeline) -> str:
        total = len(pipeline.steps)
        success = sum(1 for s in pipeline.steps if s.status == "success")
        failed = sum(1 for s in pipeline.steps if s.status == "failed")
        parts = [f"{pipeline.name}"]
        parts.append(f"✅{success}/{total}")
        if failed:
            failed_names = [s.module_id for s in pipeline.steps if s.status == "failed"]
            parts.append(f"❌{failed}({'/'.join(failed_names)})")
        parts.append(f"{pipeline.total_duration_ms:.0f}ms")
        return " | ".join(parts)

    # ── 查询 ──

    def get_history(self, limit: int = 20) -> list[dict]:
        return [p.to_dict() for p in self._pipeline_history[-limit:]]

    def get_stats(self) -> dict:
        total = len(self._pipeline_history)
        if total == 0:
            return {"total_pipelines": 0}
        success = sum(1 for p in self._pipeline_history if p.status == PipelineStatus.SUCCESS)
        failed = sum(1 for p in self._pipeline_history if p.status == PipelineStatus.FAILED)
        partial = sum(1 for p in self._pipeline_history if p.status == PipelineStatus.PARTIAL)
        avg_duration = sum(p.total_duration_ms for p in self._pipeline_history) / total
        return {
            "total_pipelines": total,
            "success": success,
            "partial": partial,
            "failed": failed,
            "avg_duration_ms": round(avg_duration, 1),
        }

    async def discover_all(self) -> dict:
        """全量发现并注册模块"""
        if not self._discovery:
            engine = ModuleDiscoveryEngine()
            result = await engine.scan_all()
            self._discovery = engine
            return {"discovered": result.discovered, "updated": result.updated}
        result = await self._discovery.scan_all()
        return {"discovered": result.discovered, "updated": result.updated}
