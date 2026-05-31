"""AUTO-EVO-AI -- 编排执行器（从 agent_orchestrator.py 提取）"""
from __future__ import annotations
import time, json, logging, threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules._base.orchestrator_types import TaskStatus, SubTask, IntentCategory
logger = logging.getLogger(__name__)
class TaskPlanner:
    """
    任务拆解器
    将用户意图拆解为可执行的子任务DAG
    """

    # 意图 → 模块映射策略
    INTENT_MODULE_MAP: dict[IntentCategory, list[str]] = {
        IntentCategory.DATA_ANALYSIS: ["data_analysis", "database_client", "business_analyst"],
        IntentCategory.DOCUMENT_GEN: ["document_automation", "content_generator"],
        IntentCategory.COMMUNICATION: ["enterprise_notifier", "email_automation", "instant_messaging"],
        IntentCategory.RPA_DESKTOP: [
            "turix_cua_bridge",
            "visual_rpa_core",
            "open_interpreter_bridge",
            "rpa_controller",
        ],
        IntentCategory.STRATEGY: ["crewai_strategy", "langgraph_decision", "business_analyst", "decision_engine"],
        IntentCategory.SECURITY: ["opa_policy_engine", "cerbos_permission", "temporal_approval", "risk_control"],
        IntentCategory.MONITORING: ["aiops_monitor", "self_healing", "audit_trail"],
        IntentCategory.CONTENT: ["content_generator", "media_content_agent"],
        IntentCategory.ECOMMERCE: ["ecommerce_agent"],
        IntentCategory.FINANCE_LEGAL: ["finance_legal_agent"],
        IntentCategory.FILE_OPERATION: ["database_client", "api_gateway"],
        IntentCategory.WEB_OPERATION: ["api_gateway", "mcp_integration", "open_interpreter_bridge"],
        IntentCategory.SCHEDULE: ["workflow_orchestrator", "agent_resource_control"],
        IntentCategory.SYSTEM: ["self_evolving_engine", "longterm_memory", "model_router", "skill_marketplace"],
        IntentCategory.CUSTOM: [],
    }

    def __init__(self, registry: ModuleRegistry):
        self.registry = registry

    def plan(
        self, user_input: str, primary_intent: IntentCategory, secondary_intents: list[IntentCategory]
    ) -> list[SubTask]:
        """
        将用户输入拆解为子任务列表

        支持复合意图拆解，例如：
        "把今天的销售数据整理成报告，发给张总"
        → [数据分析, 文档生成, 邮件发送]
        """
        sub_tasks: list[SubTask] = []
        task_counter = 0

        # 1. 主意图任务
        primary_modules = self.INTENT_MODULE_MAP.get(primary_intent, [])
        for mod_name in primary_modules:
            cap = self.registry.get_module(mod_name)
            if cap:
                task_counter += 1
                task = SubTask(
                    task_id=f"sub_{uuid.uuid4().hex[:8]}",
                    name=cap.display_name,
                    description=self._generate_task_desc(user_input, cap, primary_intent),
                    module_name=mod_name,
                    intent=primary_intent,
                    priority=cap.priority,
                    params={"user_input": user_input, "intent": primary_intent.value},
                )
                sub_tasks.append(task)

        # 2. 次要意图任务（非重复）
        added_modules = set(primary_modules)
        for intent in secondary_intents:
            sec_modules = self.INTENT_MODULE_MAP.get(intent, [])
            for mod_name in sec_modules:
                if mod_name not in added_modules:
                    cap = self.registry.get_module(mod_name)
                    if cap:
                        task_counter += 1
                        task = SubTask(
                            task_id=f"sub_{uuid.uuid4().hex[:8]}",
                            name=cap.display_name,
                            description=self._generate_task_desc(user_input, cap, intent),
                            module_name=mod_name,
                            intent=intent,
                            priority=cap.priority,
                            params={"user_input": user_input, "intent": intent.value},
                        )
                        sub_tasks.append(task)
                        added_modules.add(mod_name)

        # 3. 设置依赖关系（按优先级排序，低优先级依赖高优先级）
        self._resolve_dependencies(sub_tasks)

        # 4. 如果没有任何子任务（CUSTOM），尝试通用方案
        if not sub_tasks:
            sub_tasks = self._create_generic_plan(user_input)

        return sub_tasks

    def _generate_task_desc(self, user_input: str, cap: ModuleCapability, intent: IntentCategory) -> str:
        """生成子任务描述"""
        desc_map = {
            IntentCategory.DATA_ANALYSIS: f"分析处理：{user_input}",
            IntentCategory.DOCUMENT_GEN: f"生成文档：{user_input}",
            IntentCategory.COMMUNICATION: f"发送通知：{user_input}",
            IntentCategory.RPA_DESKTOP: f"桌面操作：{user_input}",
            IntentCategory.STRATEGY: f"战略分析：{user_input}",
            IntentCategory.SECURITY: f"安全检查：{user_input}",
            IntentCategory.MONITORING: f"监控检测：{user_input}",
            IntentCategory.CONTENT: f"内容创作：{user_input}",
            IntentCategory.ECOMMERCE: f"电商处理：{user_input}",
            IntentCategory.FINANCE_LEGAL: f"财税法务：{user_input}",
            IntentCategory.FILE_OPERATION: f"文件操作：{user_input}",
            IntentCategory.WEB_OPERATION: f"网络操作：{user_input}",
            IntentCategory.SCHEDULE: f"定时任务：{user_input}",
            IntentCategory.SYSTEM: f"系统管理：{user_input}",
            IntentCategory.CUSTOM: f"执行任务：{user_input}",
        }
        return desc_map.get(intent, f"执行：{user_input}")

    def _resolve_dependencies(self, tasks: list[SubTask]):
        """解析任务依赖关系"""
        # 按优先级排序
        tasks.sort(key=lambda t: (t.priority.value, t.intent.value))

        # 同类意图内串行，不同类意图可并行
        intent_groups: dict[IntentCategory, list[SubTask]] = defaultdict(list)
        for t in tasks:
            intent_groups[t.intent].append(t)

        for intent, group in intent_groups.items():
            for i in range(1, len(group)):
                group[i].depends_on.append(group[i - 1].task_id)

    def _create_generic_plan(self, user_input: str) -> list[SubTask]:
        """创建通用执行计划"""
        return [
            SubTask(
                task_id=f"sub_{uuid.uuid4().hex[:8]}",
                name="通用任务执行",
                description=f"执行：{user_input}",
                module_name="open_interpreter_bridge",
                intent=IntentCategory.CUSTOM,
                params={"user_input": user_input},
                priority=TaskPriority.MEDIUM,
            )
        ]

# ============================================================================
# 模块执行器
# ============================================================================

class ModuleExecutor:
    """
    模块执行器
    负责动态加载和执行模块，处理超时、重试、降级
    断点1：统一执行接口
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._loaded_modules: dict[str, Any] = {}
        self._load_errors: dict[str, str] = {}
        self._lock = threading.Lock()

    def _publish_event(self, event_type: str, data: dict):
        """断点2：发布模块执行事件"""
        try:
            from modules.event_bus import get_event_bus

            eb = get_event_bus()
            asyncio.create_task(eb.publish(event_type, data=data, source="module_executor"))
        except Exception:
            pass

    def load_module(self, module_name: str) -> Tuple[bool, Any, str]:
        """
        动态加载模块

        Returns:
            (成功?, 模块对象, 错误信息)
        """
        with self._lock:
            if module_name in self._loaded_modules:
                return (True, self._loaded_modules[module_name], "")
            if module_name in self._load_errors:
                return (False, None, self._load_errors[module_name])

            import importlib

            mod = importlib.import_module(f"modules.{module_name}")
            with self._lock:
                self._loaded_modules[module_name] = mod
            return (True, mod, "")

    async def execute(self, sub_task: SubTask, registry: ModuleRegistry, timeout: float | None = None) -> SubTask:
        """
        执行子任务

        支持超时控制、自动重试、降级回退
        """
        _ = self.trace("execute")
        metrics_collector.counter("agent_orchestrator_ops_total", labels={"task": sub_task.module_name})
        self.audit("execute_task", f"task={sub_task.module_name}, timeout={timeout}")
        cap = registry.get_module(sub_task.module_name)
        actual_timeout = timeout or (cap.timeout if cap else 120.0)

        for attempt in range(sub_task.max_retries + 1):
            sub_task.started_at = datetime.now().isoformat()
            sub_task.status = TaskStatus.RUNNING
            start = time.time()

            try:
                pass
                # 加载模块
                success, mod, err = self.load_module(sub_task.module_name)
                if not success:
                    # 尝试降级
                    if cap and cap.fallback:
                        logger.warning(f"模块 {sub_task.module_name} 加载失败，降级到 {cap.fallback}: {err}")
                        sub_task.module_name = cap.fallback
                        sub_task.retry_count += 1
                        continue
                    raise RuntimeError(err)

                # 查找执行入口
                result = self._call_module(mod, sub_task)

                sub_task.result = result
                sub_task.status = TaskStatus.COMPLETED
                sub_task.completed_at = datetime.now().isoformat()
                sub_task.duration_ms = (time.time() - start) * 1000
                return sub_task

            except Exception as e:
                sub_task.retry_count += 1
                sub_task.error = str(e)
                logger.warning(f"子任务 {sub_task.name} 第{attempt + 1}次执行失败: {e}")

                # 降级
                if cap and cap.fallback and sub_task.module_name != cap.fallback:
                    logger.info(f"降级到 {cap.fallback}")
                    sub_task.module_name = cap.fallback
                    sub_task.error = ""
                    continue

                if attempt == sub_task.max_retries:
                    sub_task.status = TaskStatus.DEGRADED
                    sub_task.completed_at = datetime.now().isoformat()
                    sub_task.duration_ms = (time.time() - start) * 1000
                    sub_task.result = {"error": sub_task.error, "degraded": True}

        return sub_task

    def _call_module(self, mod: Any, sub_task: SubTask) -> Any:
        """调用模块的执行入口（断点1修复 + 断点2事件发布）"""
        # 断点1修复：策略1 - 查找 execute/run/process/handle 标准方法
        for method_name in ("execute", "run", "process", "handle"):
            if hasattr(mod, method_name):
                func = getattr(mod, method_name)
                if callable(func):
                    result = func(sub_task.params)
                    # 断点2: 发布模块执行事件
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "method": method_name,
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result

        # 断点1修复：策略2 - 查找 Main/Engine/Core/Handler/Agent 类
        for cls_name in ("Main", "Engine", "Core", "Handler", "Agent"):
            if hasattr(mod, cls_name):
                cls = getattr(mod, cls_name)
                if hasattr(cls, "execute"):
                    result = cls().execute(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "class": cls_name,
                            "method": "execute",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result
                elif hasattr(cls, "run"):
                    result = cls().run(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "class": cls_name,
                            "method": "run",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result

        # 断点1修复：策略3 - 查找标准 execute 入口（给没有上述方法的模块提供兜底）
        if hasattr(mod, "Main"):
            try:
                main_instance = mod.Main()
                if hasattr(main_instance, "execute"):
                    result = main_instance.execute(sub_task.params)
                    self._publish_event(
                        "module.executed",
                        {
                            "module": sub_task.module_name,
                            "instance": "Main",
                            "method": "execute",
                            "success": result.get("success") if isinstance(result, dict) else True,
                        },
                    )
                    return result
            except Exception:
                pass

        # 策略4：模块元数据返回
        return {
            "module": sub_task.module_name,
            "status": "loaded",
            "note": "模块已加载，标准执行接口待注册",
            # 断点1：标注该模块需要接入标准化execute接口
            "_needs_interface": True,
            "_available_methods": [m for m in dir(mod) if not m.startswith("_")],
        }

# ============================================================================
# 进化反馈器
# ============================================================================

class EvolutionFeedback:
    """
    进化反馈器
    将执行结果反馈给 self_evolving_engine 进行学习
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._engine = None
        self._memory = None

    def set_memory(self, memory_engine):
        """P1: 外部注入记忆引擎实例"""
        self._memory_engine = memory_engine

    def _get_engine(self):
        if self._engine is None:
            from modules import self_evolving_engine

            self._engine = self_evolving_engine
        return self._engine

    def _get_memory(self):
        if self._memory is None:
            from modules import longterm_memory

            self._memory = longterm_memory
        return self._memory

    def record_execution(self, task: OrchestratorTask):
        """记录任务执行结果用于学习"""
        # P1: 写入长期记忆
        me = getattr(self, "_memory_engine", None)
        if me:
            try:
                modules_used = [st.module_name for st in task.sub_tasks]
                success = task.status == TaskStatus.COMPLETED
                me.save_memory(
                    content=f"意图:{task.intent.value} | 模块:{','.join(modules_used)} | 质量:{task.quality_score:.0%}",
                    memory_type="execution_log",
                    entity_id=task.task_id,
                    weight=0.7 if success else 0.9,
                )
            except Exception as e:
                logger.debug(f"[P1记忆] EvolutionFeedback写入失败: {e}")

        engine = self._get_engine()
        if engine and hasattr(engine, "record_experience"):
            try:
                engine.record_experience(
                    task_type=task.intent.value,
                    user_input=task.user_input,
                    success=task.status == TaskStatus.COMPLETED,
                    modules_used=[st.module_name for st in task.sub_tasks],
                    quality_score=task.quality_score,
                    lessons=task.lessons_learned,
                )
                logger.info("已将执行经验反馈给自我进化引擎")
            except Exception as e:
                logger.debug(f"进化反馈写入失败: {e}")

    def store_context(self, key: str, value: Any):
        """P1: 存储长期记忆上下文（增强版）"""
        # 优先使用注入的 memory_engine
        me = getattr(self, "_memory_engine", None)
        if me:
            try:
                me.save_memory(
                    content=f"{key}: {str(value)[:200]}", memory_type="context", entity_id="evolution", weight=0.5
                )
                return
            except Exception as e:
                logger.debug(f"记忆引擎写入失败: {e}")
        # 降级：旧的 store API
        memory = self._get_memory()
        if memory and hasattr(memory, "store"):
            try:
                memory.store(key, value)
            except Exception as e:
                logger.debug(f"长期记忆写入失败: {e}")

# ============================================================================
class ExecutionDAGBuilder:
    """执行DAG构建器 - 将任务分解为有向无环图并编排执行顺序。

    企业场景：复杂工作流（如CI/CD流水线、数据ETL管道）需要
    正确处理任务依赖、并行化、条件分支和失败回退。
    """

    def __init__(self):
        self._initialized = False
        self._status = "pending"
        self._nodes: dict[str, dict] = {}  # task_id -> {deps, action, parallel}
        self._edges: dict[str, Set[str]] = defaultdict(set)

    def add_task(self, task_id: str, action: str, depends_on: list[str] = None, parallel: bool = False):
        """添加任务节点"""
        self._nodes[task_id] = {
            "action": action,
            "depends_on": depends_on or [],
            "parallel": parallel,
            "status": "pending",
        }
        for dep in depends_on or []:
            self._edges[dep].add(task_id)

    def build(self) -> dict:
        """构建可执行的DAG，返回执行层级"""
        in_degree = {tid: len(info["depends_on"]) for tid, info in self._nodes.items()}
        reverse = defaultdict(set)
        for tid, info in self._nodes.items():
            for dep in info["depends_on"]:
                reverse[dep].add(tid)

        # 拓扑分层
        layers = []
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        visited = set()
        while queue:
            layer = []
            for tid in queue:
                if tid in visited:
                    continue
                visited.add(tid)
                layer.append(tid)
            if layer:
                layers.append(layer)
            next_queue = []
            for tid in layer:
                for dependent in reverse.get(tid, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            queue = next_queue

        # 检测环
        if len(visited) != len(self._nodes):
            missing = set(self._nodes) - visited
            return {"success": False, "error": "circular_dependency", "cycle_nodes": list(missing)}

        # 计算并行度
        max_parallel = max(len(l) for l in layers) if layers else 0
        return {
            "success": True,
            "layers": layers,
            "total_tasks": len(self._nodes),
            "max_parallelism": max_parallel,
            "critical_path_length": len(layers),
        }

    def estimate_execution_time(self, task_durations: dict[str, float]) -> dict:
        """估算DAG总执行时间（考虑并行）"""
        dag = self.build()
        if not dag["success"]:
            return {"error": "DAG contains cycle"}
        total = 0
        for layer in dag["layers"]:
            layer_max = max((task_durations.get(t, 1.0) for t in layer), default=1.0)
            total += layer_max
        return {
            "estimated_seconds": round(total, 1),
            "layers": dag["critical_path_length"],
            "max_parallelism": dag["max_parallelism"],
            "speedup_vs_serial": round(sum(task_durations.values()) / total, 1) if total > 0 else 0,
        }
