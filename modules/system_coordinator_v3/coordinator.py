# 原 system_coordinator_v3.py L3044-3951 — 系统协调器主类+工厂
"""系统协调器主类 + 工厂函数"""
import logging, time, re, os, sys, math, asyncio
import threading, importlib, inspect
from typing import Dict, Any, Optional, List
from collections.abc import Callable
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector
from modules.system_coordinator_v3.analyzer import SystemCoordinatorV3Analyzer
from modules.system_coordinator_v3.graph import ModuleCapabilityGraph
from modules.system_coordinator_v3.loop import AutonomousLoop
from modules.system_coordinator_v3.orchestrator import CrossModuleOrchestrator
logger = logging.getLogger("evo.coordinator.v3")

class SystemCoordinatorV3(EnterpriseModule):
    """
    AUTO-EVO-AI 系统核心协调器 v3.0

    进化要点:
    - 全模块自动注册: 自动扫描并注册所有模块
    - 能力图谱: 自动构建模块能力索引
    - 自主决策循环: 系统能自主运行和决策
    - 跨模块编排: 自动组合模块完成复杂任务
    - 向后兼容: 完全兼容 v2.0 API
    """

    VERSION = "V0.1"

    def __init__(self, modules_dir: str = None):
        super().__init__()

        self.initialized = False
        self.start_time = None
        self.modules: dict[str, Any] = {}
        self.status = "stopped"

        # v2.0 模块引用
        self._mm = None
        self._ai_gateway = None
        self._memory = None
        self._workflow = None
        self._event_bus = None
        self._autonomous_agent = None
        self._external_executor = None
        self._goal_tracker = None
        self._self_healing = None
        self._experience_base = None
        self._resilience = None
        self._cron_engine = None

        # v3.0 核心组件
        self.capability_graph = ModuleCapabilityGraph(modules_dir)
        self.autonomous_loop = AutonomousLoop(self)
        self.orchestrator = CrossModuleOrchestrator(self, self.capability_graph)

        # v3.1 智能协调层
        self.intelligent_coordinator = None
        try:
            from core.intelligent_coordinator import IntelligentCoordinator

            self.intelligent_coordinator = IntelligentCoordinator()
            logger.info("[Coordinator v3.1] 智能协调层已加载")
        except Exception as e:
            logger.warning(f"[Coordinator v3.1] 智能协调层加载失败(降级到基础模式): {e}")

        # v2.0 兼容组件
        from modules.system_coordinator import SmartRouter, EnhancedPerception, ReflectionEngine

        self.router = SmartRouter(self)
        self.perception = EnhancedPerception(self)
        self.reflection = ReflectionEngine(self)

        # 模块健康状态
        self._module_health: dict[str, str] = {}
        self._module_instances: dict[str, Any] = {}
        self._ext_module_classes: dict[str, Any] = {}  # 扩展模块类（懒加载）

        # 执行统计
        self._stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "by_type": defaultdict(int),
            "by_module": defaultdict(int),
        }

        # 模块元数据缓存
        self._module_metadata: dict = {}

        logger.info(f"[Coordinator v3.0] 创建 | 全模块自动协调")

    def auto_register_all_modules(self):
        """自动注册所有可导入的模块"""
        registered = 0
        failed = 0

        for module_id, info in self.capability_graph.graph.items():
            try:
                pass
                # 尝试导入模块
                module_path = f"modules.{module_id}"
                module = importlib.import_module(module_path)

                # 查找主类（与模块名匹配或包含主要功能的类）
                main_class = None
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name.lower() == module_id.replace("_", "").lower():
                        main_class = obj
                        break
                    # 或者找第一个非内置类
                    if obj.__module__ == module.__name__ and name not in ["BaseModel", "Enum"]:
                        if not main_class:
                            main_class = obj

                if main_class:
                    # 尝试实例化（无参数或默认参数）
                    try:
                        instance = main_class()
                        self._module_instances[module_id] = instance
                        self.modules[module_id] = instance
                        self._module_health[module_id] = "healthy"
                        registered += 1
                    except Exception as e:
                        # 实例化失败但模块已导入
                        self.modules[module_id] = module
                        self._module_health[module_id] = "imported_only"
                        registered += 1
                else:
                    # 没有类，导入模块本身
                    self.modules[module_id] = module
                    self._module_health[module_id] = "imported_only"
                    registered += 1

            except Exception as e:
                failed += 1
                self._module_health[module_id] = "error"
                logger.debug(f"[AutoRegister] {module_id} 失败: {e}")

        logger.info(f"[AutoRegister] 完成: {registered} 成功, {failed} 失败")
        return {"registered": registered, "failed": failed}

    def _load_core_extensions(self):
        """加载 core/ 目录下的扩展模块（脚本模块 + extension_modules）"""
        import importlib.util
        from pathlib import Path

        loaded = 0
        skipped = 0
        base_dir = Path(__file__).parent.parent

        # 加载 extension_modules.py
        ext_path = base_dir / "core" / "extension_modules.py"
        if ext_path.exists():
            try:
                spec = importlib.util.spec_from_file_location("_ext", str(ext_path))
                ext_mod = importlib.util.module_from_spec(spec)
                sys.modules["_ext"] = ext_mod
                spec.loader.exec_module(ext_mod)

                if hasattr(ext_mod, "EXTENSION_MODULES"):
                    for module_id, module_class in ext_mod.EXTENSION_MODULES.items():
                        if module_id in self.modules or module_id in self._module_instances:
                            skipped += 1
                            continue
                        try:
                            self._module_instances[module_id] = None
                            self._ext_module_classes[module_id] = module_class
                            self._module_health[module_id] = "healthy"
                            loaded += 1
                        except Exception as e:
                            logger.debug(f"[ExtModule] {module_id} 注册失败: {e}")
            except Exception as e:
                logger.warning(f"[ExtModule] extension_modules 加载失败: {e}")

        logger.info(f"[ExtModule] 扩展模块加载: {loaded} 成功, {skipped} 跳过(已存在)")
        return loaded

    def initialize(self, **kwargs):
        """初始化协调器"""
        # 自动注册所有模块
        auto_result = self.auto_register_all_modules()

        # 加载 core/ 目录扩展模块
        ext_count = self._load_core_extensions()

        # 设置 v2.0 模块引用
        self._mm = kwargs.get("mm")
        self._ai_gateway = kwargs.get("ai_gateway")
        self._memory = kwargs.get("memory")
        self._workflow = kwargs.get("workflow")
        self._event_bus = kwargs.get("event_bus")
        self._autonomous_agent = kwargs.get("autonomous_agent")
        self._external_executor = kwargs.get("external_executor")
        self._goal_tracker = kwargs.get("goal_tracker")
        self._self_healing = kwargs.get("self_healing")
        self._experience_base = kwargs.get("experience_base")
        self._resilience = kwargs.get("resilience")
        self._cron_engine = kwargs.get("cron_engine")
        self._module_metadata = kwargs.get("module_metadata", {})

        # 构建路由索引
        if self._module_metadata:
            self.router.build_module_index(self._mm, self._module_metadata)

        self.initialized = True
        self.status = "ready"
        self.start_time = datetime.now()

        logger.info(
            f"[Coordinator v3.0] 初始化完成 | "
            f"{len(self.modules)} 标准模块 | "
            f"{len(self._module_instances)} 总模块 | "
            f"{len(self.capability_graph.graph)} 能力图谱"
        )

        return auto_result

    async def execute(self, task: str, context: dict = None) -> dict:
        """统一执行接口 — v3.1 智能增强版"""
        if not self.initialized:
            return {"success": False, "error": "系统未初始化"}

        self._stats["total_tasks"] += 1
        context = context or {}
        session_id = context.get("session_id")

        try:
            pass
            # v3.1: 智能协调层优先
            if self.intelligent_coordinator:
                try:

                    async def _module_executor(module_id, action, params):
                        return await self._execute_single_module(module_id, action, params, context)

                    ic_result = await self.intelligent_coordinator.process(
                        task, session_id=session_id, module_executor=_module_executor
                    )
                    # 双重检查：外层 success 和内部 result.success 都为 True 才算成功
                    _ic_inner = ic_result.get("result", {})
                    if isinstance(_ic_inner, dict):
                        _ic_result_success = _ic_inner.get("success", True)
                    else:
                        _ic_result_success = True
                    if ic_result.get("success") and _ic_result_success:
                        self._stats["successful_tasks"] += 1
                        return {
                            **ic_result,
                            "coordinator_version": "3.1-intelligent",
                        }
                    # 智能层失败, 降级到v3.0路径但携带智能解析的意图
                    logger.info(
                        f"[Coordinator v3.1] 智能层未成功, 降级到v3.0: {ic_result.get('intent', {}).get('reasoning', '')}"
                    )
                except Exception as e:
                    logger.debug(f"[Coordinator v3.1] 智能层异常: {e}")

            # Step 1: 尝试跨模块编排（包括单步链）
            chain = self.orchestrator.build_chain(task)
            chain_result = None
            if len(chain) >= 1:
                logger.info(f"[Coordinator v3.0] 模块链执行: {[s['module'] for s in chain]}")
                chain_result = await self.orchestrator.execute_chain(chain, task, context)
                if chain_result.get("success"):
                    self._stats["successful_tasks"] += 1
                    return chain_result
                # chain 执行失败，记录日志但继续尝试其他路径
                logger.warning(f"[Coordinator v3.0] 模块链失败: {chain_result.get('error', 'unknown')}，尝试回退路由")

            # Step 2: 回退到 v2.0 智能路由 — 但先检查chain是否已正确匹配了模块
            if chain:
                # chain路由正确但执行失败，记录匹配信息并尝试重试链中的模块
                chain_module = chain[0]["module"]
                logger.info(f"[Coordinator v3.0] 链路由正确({chain_module})但执行失败，尝试registry重试")
                for step in chain:
                    try:
                        pass
                        # 尝试通过registry执行（与API端点相同路径）
                        if self._mm and hasattr(self._mm, "lazy_load_module"):
                            mod = await asyncio.wait_for(self._mm.lazy_load_module(step["module"]), timeout=20.0)
                            if mod and hasattr(mod, "execute"):
                                action = step.get("method", "status") or "status"
                                result = mod.execute(action=action, params={})
                                if asyncio.iscoroutine(result):
                                    result = await result
                                if isinstance(result, dict) or (hasattr(result, "get")):
                                    self._stats["successful_tasks"] += 1
                                    return {
                                        "success": True,
                                        "result": result,
                                        "module": step["module"],
                                        "matched_by": "chain_registry_retry",
                                    }
                        # 也尝试_direct execute
                        retry_action = step.get("method", "status") or "status"
                        single_result = await self._execute_single_module(
                            step["module"],
                            task,
                            {"action": retry_action, "params": {}, "method": retry_action},
                            context,
                        )
                        if single_result.get("success"):
                            self._stats["successful_tasks"] += 1
                            single_result["matched_by"] = "chain_retry"
                            return single_result
                    except Exception as e:
                        logger.debug(f"[Coordinator v3.0] chain_retry {step['module']} failed: {e}")

            route_info = await self.router.route(task, context)
            result = await self._execute_routed(route_info, task, context)
            if result.get("success"):
                # Step 3: 反思
                if hasattr(self, "reflection"):
                    await self.reflection.reflect(task, result, route_info)
                self._stats["successful_tasks"] += 1
                return result

            # Step 3: 直接从能力图谱查找并执行匹配模块
            logger.info(f"[Coordinator v3.0] 路由无结果，尝试能力图谱直接匹配: {task}")
            matches = self.capability_graph.find_modules_by_task(task)
            for module_id, score in matches[:3]:
                if score < 2.0:
                    continue
                try:
                    single_result = await self._execute_single_module(module_id, task, {"input": task}, context)
                    if single_result.get("success"):
                        self._stats["successful_tasks"] += 1
                        single_result["matched_by"] = "capability_graph"
                        single_result["match_score"] = round(score, 2)
                        return single_result
                except Exception as e:
                    logger.debug(f"[Coordinator v3.0] 能力图谱执行 {module_id} 失败: {e}")

            # 所有路径都失败 → 尝试 AI Gateway 兜底
            logger.info(f"[Coordinator v3.0] 模块链+路由+能力图谱均无匹配，尝试AI Gateway兜底: {task[:50]}")
            ai_result = await self._ai_fallback(task, context)
            if ai_result:
                self._stats["successful_tasks"] += 1
                return ai_result

            self._stats["failed_tasks"] += 1
            return {
                "success": False,
                "error": f"当前系统专注于AI/开发/金融/运维领域，无法处理: {task[:60]}",
                "suggestion": "试试输入相关任务，如：查询AI开源项目、股票分析、代码生成、系统监控等",
                "tried_chain": [s["module"] for s in chain] if chain else [],
                "chain_results": chain_result if chain else None,
            }

        except Exception as e:
            self._stats["failed_tasks"] += 1
            return {"success": False, "error": str(e)}

    async def _execute_routed(self, route_info: dict, task: str, context: dict) -> dict:
        """执行路由后的任务 — 兼容 v2.0"""
        modules = route_info.get("modules", [])
        params = route_info.get("params", {})

        # 尝试执行匹配的模块
        for module_id in modules:
            try:
                result = await self._execute_single_module(module_id, task, params, context)
                if result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"[Execute] {module_id} 失败: {e}")
                continue

        # 所有模块失败
        return {"success": False, "error": f"所有模块执行失败: {modules}"}

    def _get_or_create_instance(self, module_id: str):
        """获取模块实例，支持扩展模块的懒加载"""
        # 优先使用 registry（api_server ModuleRegistry）中的实例
        # registry 中的实例来自当前工作目录（D 盘），可能比协调器缓存更新
        if self._mm:
            _registry_mod = (
                getattr(self._mm, "modules", None)
                or getattr(self._mm, "_modules", None)
                or getattr(self._mm, "module_registry", None)
            )
            if _registry_mod and module_id in _registry_mod:
                reg_instance = _registry_mod[module_id]
                # registry 中可能是模块对象而非实例，检查是否有 execute 方法
                if reg_instance is not None and hasattr(reg_instance, "execute") and callable(reg_instance.execute):
                    return reg_instance

        instance = self._module_instances.get(module_id)
        if instance is not None:
            return instance

        # 尝试懒加载扩展模块
        module_class = self._ext_module_classes.get(module_id)
        if module_class:
            try:
                instance = module_class()
                self._module_instances[module_id] = instance
                self._module_health[module_id] = "healthy"
                logger.debug(f"[LazyLoad] 扩展模块 {module_id} 已实例化")
                return instance
            except Exception as e:
                logger.warning(f"[LazyLoad] 扩展模块 {module_id} 实例化失败: {e}")
                self._module_health[module_id] = "error"

        return None

    async def _ai_fallback(self, task: str, context: dict) -> dict | None:
        """AI Gateway兜底 — 用ai_gateway直接回答任务"""
        try:
            instance = self._get_or_create_instance("ai_gateway")
            if not instance:
                return None
            # 尝试调用 chat/ask 方法
            for method_name in ["chat", "ask", "execute", "query"]:
                method = getattr(instance, method_name, None)
                if method and callable(method):
                    try:
                        prompt = f"用户任务: {task}\n请用中文直接回答这个问题。"
                        if method_name == "execute":
                            r = method("chat", {"prompt": prompt, "message": prompt})
                        else:
                            r = method({"prompt": prompt, "message": prompt, "task": task})
                        if r and (
                            isinstance(r, dict)
                            and (
                                r.get("success")
                                or r.get("response")
                                or r.get("result")
                                or r.get("content")
                                or r.get("answer")
                            )
                        ):
                            text = r.get("response") or r.get("result") or r.get("content") or r.get("answer") or str(r)
                            if isinstance(text, dict):
                                text = str(text)
                            return {
                                "success": True,
                                "type": "ai_chat",
                                "module": "ai_gateway",
                                "method": method_name,
                                "task": task,
                                "result": text[:2000],
                            }
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"[Coordinator v3.0] AI fallback失败: {e}")
        return None

    async def _execute_single_module(self, module_id: str, task: str, params: dict, context: dict) -> dict:
        """执行单个模块 — v3.0 增强（带超时保护）"""
        # 1. 获取模块实例（支持懒加载）
        instance = self._get_or_create_instance(module_id)
        if instance:
            requested_method = params.get("method", "")
            exec_params = {k: v for k, v in params.items() if k != "method"}

            if hasattr(instance, "execute") and callable(instance.execute):
                method_name = "execute"
                action = requested_method or task
                # 校验action是否存在（仅记录日志，不强制fallback）
                if action and action != task:
                    valid_actions = self._get_module_actions(instance)
                    if valid_actions and action not in valid_actions:
                        logger.debug(
                            f"[Execute] {module_id} action '{action}' 不在已知列表({len(valid_actions)}个)，仍尝试执行"
                        )
                call_params = {"action": action, "params": exec_params}
                # 标准action拦截：优先走基类_handle_standard_action（避免子类execute覆盖导致的action丢失）
                _STANDARD = {
                    "status",
                    "info",
                    "health",
                    "healthcheck",
                    "ping",
                    "list_actions",
                    "help",
                    "configure",
                    "reset",
                    "metrics",
                    "version",
                    "stop",
                }
                if action.lower() in _STANDARD and hasattr(instance, "_handle_standard_action"):
                    try:
                        std_result = instance._handle_standard_action(action, exec_params)
                        if std_result is not None:
                            if hasattr(std_result, "data"):
                                return {
                                    "success": std_result.success,
                                    "result": std_result.data,
                                    "module": module_id,
                                    "method": action,
                                }
                            return {"success": True, "result": std_result, "module": module_id, "method": action}
                    except Exception:
                        pass
            elif requested_method and hasattr(instance, requested_method):
                method_name = requested_method
                call_params = exec_params
            else:
                method_name = self._find_best_method(instance, task, params)
                call_params = exec_params

            if method_name:
                method = getattr(instance, method_name)
                try:
                    if asyncio.iscoroutinefunction(method):
                        result = await asyncio.wait_for(method(**call_params), timeout=30.0)
                    else:
                        result = method(**call_params)
                    # 处理sync方法返回coroutine的情况（如sync execute调用了async _safe_execute）
                    if asyncio.iscoroutine(result):
                        result = await asyncio.wait_for(result, timeout=30.0)
                    # 判断执行是否成功：检查 result 内部的 success 字段
                    _exec_success = True
                    if isinstance(result, dict) and "success" in result:
                        _exec_success = result.get("success", True)
                    elif isinstance(result, object) and hasattr(result, "success"):
                        _exec_success = getattr(result, "success", True)
                    return {"success": _exec_success, "result": result, "module": module_id, "method": method_name}
                except TimeoutError:
                    return {
                        "success": False,
                        "error": f"模块 {module_id}.{method_name} 执行超时(30s)",
                        "module": module_id,
                        "timeout": True,
                    }
                except Exception as e:
                    return {"success": False, "error": str(e), "module": module_id}

        # 2. 尝试通过 registry 执行模块
        if self._mm:
            registry = self._mm
            # 检查模块是否在 registry 中（兼容 _modules/modules/module_registry）
            modules_dict = (
                getattr(registry, "modules", None)
                or getattr(registry, "_modules", None)
                or getattr(registry, "module_registry", None)
            )
            if modules_dict and module_id in modules_dict:
                mod = None
                # 优先通过 lazy_load_module 获取实际模块实例
                if hasattr(registry, "lazy_load_module"):
                    try:
                        mod = await asyncio.wait_for(registry.lazy_load_module(module_id), timeout=20.0)
                    except (TimeoutError, Exception) as e:
                        logger.debug(f"[Execute] lazy_load {module_id} failed: {e}")
                # fallback: 直接从 modules dict 获取（可能是 ModuleInfo 或实例）
                if mod is None:
                    mod = modules_dict[module_id]
                if mod is not None:
                    # 优先通过execute(action=method)调用
                    if hasattr(mod, "execute") and callable(mod.execute):
                        method_name = params.get("method") or task or "status"
                        exec_params = {k: v for k, v in params.items() if k != "method"}
                        # 标准action拦截：优先走基类_handle_standard_action
                        _STANDARD = {
                            "status",
                            "info",
                            "health",
                            "healthcheck",
                            "ping",
                            "list_actions",
                            "help",
                            "configure",
                            "reset",
                            "metrics",
                            "version",
                            "stop",
                        }
                        if method_name.lower() in _STANDARD and hasattr(mod, "_handle_standard_action"):
                            try:
                                std_result = mod._handle_standard_action(method_name, exec_params)
                                if std_result is not None:
                                    if hasattr(std_result, "data"):
                                        return {
                                            "success": std_result.success,
                                            "result": std_result.data,
                                            "module": module_id,
                                            "method": method_name,
                                        }
                                    return {
                                        "success": True,
                                        "result": std_result,
                                        "module": module_id,
                                        "method": method_name,
                                    }
                            except Exception:
                                pass
                        call_params = {"action": method_name, "params": exec_params}
                        method = getattr(mod, "execute")
                        try:
                            if asyncio.iscoroutinefunction(method):
                                result = await asyncio.wait_for(method(**call_params), timeout=30.0)
                            else:
                                result = method(**call_params)
                            if asyncio.iscoroutine(result):
                                result = await asyncio.wait_for(result, timeout=30.0)
                            return {"success": True, "result": result, "module": module_id, "method": method_name}
                        except TimeoutError:
                            return {
                                "success": False,
                                "error": f"模块 {module_id}.{method_name} 执行超时(30s)",
                                "module": module_id,
                                "timeout": True,
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e), "module": module_id}
                    else:
                        # 无execute方法：直接调用指定方法
                        method_name = params.get("method") or self._find_best_method(mod, task, params)
                        if method_name and hasattr(mod, method_name):
                            method = getattr(mod, method_name)
                            try:
                                exec_params = params.get("params", params)
                                if asyncio.iscoroutinefunction(method):
                                    result = await asyncio.wait_for(method(**exec_params), timeout=30.0)
                                else:
                                    result = method(**exec_params)
                                if asyncio.iscoroutine(result):
                                    result = await asyncio.wait_for(result, timeout=30.0)
                                return {"success": True, "result": result, "module": module_id, "method": method_name}
                            except TimeoutError:
                                return {
                                    "success": False,
                                    "error": f"模块 {module_id}.{method_name} 执行超时(30s)",
                                    "module": module_id,
                                    "timeout": True,
                                }
                            except Exception as e:
                                return {"success": False, "error": str(e), "module": module_id}

        # 3. AI 网关
        if self._ai_gateway and module_id == "ai-gateway":
            messages = context.get("messages", [{"role": "user", "content": task}])
            result = self._ai_gateway.chat(messages)
            return {"success": True, "type": "ai", "result": result}

        # 4. 尝试从扩展模块实例中执行
        instance = self._get_or_create_instance(module_id)
        if not instance and self.capability_graph and module_id in self.capability_graph.graph:
            # 动态导入并实例化模块
            try:
                module_path = f"modules.{module_id}"
                mod = importlib.import_module(module_path)
                # 找主类
                main_class = None
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if name.lower() == module_id.replace("_", "").lower():
                        main_class = obj
                        break
                    if obj.__module__ == mod.__name__ and not main_class:
                        main_class = obj
                if main_class:
                    instance = main_class()
                    self._module_instances[module_id] = instance
                    logger.info(f"[DynamicLoad] 按需加载模块 {module_id}")
            except Exception as e:
                logger.debug(f"[DynamicLoad] 动态加载 {module_id} 失败: {e}")

        if instance:
            # 优先通过execute(action=method)调用
            if hasattr(instance, "execute") and callable(instance.execute):
                method_name = params.get("method") or "status"
                exec_params = {k: v for k, v in params.items() if k != "method"}
                call_params = {"action": method_name, "params": exec_params}
                method = getattr(instance, "execute")
                try:
                    if asyncio.iscoroutinefunction(method):
                        result = await asyncio.wait_for(method(**call_params), timeout=30.0)
                    else:
                        result = method(**call_params)
                    if asyncio.iscoroutine(result):
                        result = await asyncio.wait_for(result, timeout=30.0)
                    return {"success": True, "result": result, "module": module_id, "method": method_name}
                except TimeoutError:
                    return {
                        "success": False,
                        "error": f"模块 {module_id}.{method_name} 执行超时(30s)",
                        "module": module_id,
                        "timeout": True,
                    }
                except Exception as e:
                    return {"success": False, "error": str(e), "module": module_id}
            else:
                method_name = params.get("method") or self._find_best_method(instance, task, params)
                if method_name and hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    try:
                        exec_params = params.get("params", params)
                        if asyncio.iscoroutinefunction(method):
                            result = await asyncio.wait_for(method(**exec_params), timeout=30.0)
                        else:
                            result = method(**exec_params)
                        return {"success": True, "result": result, "module": module_id, "method": method_name}
                    except TimeoutError:
                        return {
                            "success": False,
                            "error": f"模块 {module_id}.{method_name} 执行超时(30s)",
                            "module": module_id,
                            "timeout": True,
                        }
                    except Exception as e:
                        return {"success": False, "error": str(e), "module": module_id}

        return {"success": False, "error": f"模块 {module_id} 无法执行（未注册或无法加载）"}

        return {"success": False, "error": f"模块 {module_id} 无法执行"}

    def _get_module_actions(self, instance: Any) -> list | None:
        """获取模块execute()支持的action列表 — 合并所有来源"""
        if not hasattr(instance, "execute"):
            return None
        all_actions = set()
        import re, inspect

        # 方法1: _action_* 方法名（最可靠）
        for name in dir(instance):
            if name.startswith("_action_") and callable(getattr(instance, name, None)):
                all_actions.add(name[len("_action_") :])

        # 方法2: inspect execute 源码找 dispatch/actions dict keys
        try:
            src = inspect.getsource(instance.execute)
            # 匹配 dispatch = { 或 actions = { — 提取 "key": self._action_xxx
            for pattern in [r"(?:dispatch|actions|_actions|_dispatch_map)\s*=\s*\{([^}]+)\}"]:
                m = re.search(pattern, src, re.DOTALL)
                if m:
                    keys = re.findall(r"""['"]([a-z]\w*)['"]\s*:""", m.group(1))
                    all_actions.update(keys)
        except Exception:
            pass

        # 方法3: 如果有 _dispatch 方法，也inspect它
        if hasattr(instance, "_dispatch"):
            try:
                src = inspect.getsource(instance._dispatch)
                for pattern in [r"(?:dispatch|actions|_actions|handlers)\s*=\s*\{([^}]+)\}"]:
                    m = re.search(pattern, src, re.DOTALL)
                    if m:
                        keys = re.findall(r"""['"]([a-z]\w*)['"]\s*:""", m.group(1))
                        all_actions.update(keys)
            except Exception:
                pass

        # 方法4: _get_available_actions（基类）
        if hasattr(instance, "_get_available_actions") and callable(instance._get_available_actions):
            try:
                extra = instance._get_available_actions()
                if isinstance(extra, (list, tuple, set)):
                    all_actions.update(extra)
            except Exception:
                pass

        return sorted(all_actions) if all_actions else None

    def _find_best_method(self, instance: Any, task: str, params: dict) -> str | None:
        """查找实例上最适合的方法"""
        methods = [m for m in dir(instance) if not m.startswith("_") and callable(getattr(instance, m))]

        # 优先匹配参数中指定的 method
        if "method" in params and params["method"] in methods:
            return params["method"]

        # 最高优先级：若模块有 execute 方法，直接返回（统一入口约定）
        if "execute" in methods:
            return "execute"

        # 按任务类型匹配（只有没有execute才走这里）
        task_lower = task.lower()
        method_scores = {}

        for method in methods:
            score = 0
            method_lower = method.lower()

            # 常见方法名匹配
            if any(kw in task_lower for kw in ["获取", "读取", "查询"]) and method_lower.startswith("get_"):
                score += 5
            if any(kw in task_lower for kw in ["保存", "写入"]) and method_lower.startswith("set_"):
                score += 5
            if any(kw in task_lower for kw in ["发送", "推送"]) and method_lower.startswith("send_"):
                score += 5
            if any(kw in task_lower for kw in ["分析", "统计"]) and "analy" in method_lower:
                score += 5
            if any(kw in task_lower for kw in ["生成", "创建"]) and "gener" in method_lower:
                score += 5

            # 通用方法
            if method_lower in ["run", "process", "handle"]:
                score += 1

            if score > 0:
                method_scores[method] = score

        if method_scores:
            return max(method_scores, key=method_scores.get)

        # 默认方法
        for default in ["execute", "run", "process", "handle"]:
            if default in methods:
                return default

        return methods[0] if methods else None

    async def start_autonomous(self):
        """启动自主决策循环"""
        await self.autonomous_loop.start()

    async def stop_autonomous(self):
        """停止自主决策循环"""
        await self.autonomous_loop.stop()

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "version": f"V0.1 COORDINATED (v3.0)",
            "coordinator_version": self.VERSION,
            "status": self.status,
            "initialized": self.initialized,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "modules": {
                "registered": len(self.modules),
                "instances": len(self._module_instances),
                "healthy": sum(1 for h in self._module_health.values() if h == "healthy"),
                "names": list(self.modules.keys())[:20],
            },
            "capabilities": {
                "total": len(self.capability_graph.graph),
                "capabilities": len(self.capability_graph.capability_index),
                "autonomous_loop": self.autonomous_loop._running,
            },
            "execution_stats": {
                "total": self._stats["total_tasks"] + self.autonomous_loop._execution_stats["total"],
                "success": self._stats["successful_tasks"] + self.autonomous_loop._execution_stats["success"],
                "failed": self._stats["failed_tasks"] + self.autonomous_loop._execution_stats["failed"],
                "rate": (self._stats["successful_tasks"] + self.autonomous_loop._execution_stats["success"])
                / max(self._stats["total_tasks"] + self.autonomous_loop._execution_stats["total"], 1),
            },
            "recent_executions": self.autonomous_loop._recent_executions[-20:],
        }

    def get_capabilities(self) -> dict:
        """获取系统能力"""
        return {
            "perception": True,
            "decision": True,
            "execution": True,
            "learning": True,
            "resilience": True,
            "autonomy": self.autonomous_loop._running,
            "coordination": True,
            "orchestration": True,
        }

    def get_automation_score(self) -> int:
        """计算自动化能力评分"""
        score = 0
        caps = self.get_capabilities()

        # 基础能力
        for cap in ["perception", "decision", "execution", "learning", "resilience", "coordination"]:
            if caps.get(cap):
                score += 12

        # 高级能力
        if caps.get("autonomy"):
            score += 15
        if caps.get("orchestration"):
            score += 15

        # 模块覆盖率
        module_score = min(len(self.modules) * 0.5, 20)
        score += int(module_score)

        return min(score, 100)

# ============================================================================
# 便捷函数
# ============================================================================




def create_coordinator_v3(modules_dir: str = None) -> SystemCoordinatorV3:
    """创建 v3.0 协调器"""
    return SystemCoordinatorV3(modules_dir)

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("system_coordinator_v3.execute", "start", action=action)
        self.metrics_collector.counter("system_coordinator_v3.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "system_coordinator_v3"}
            else:
                result = {"success": True, "action": action, "module": "system_coordinator_v3"}
            self.metrics_collector.counter("system_coordinator_v3.execute.success", 1)
            self.trace("system_coordinator_v3.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("system_coordinator_v3.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "system_coordinator_v3"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "system_coordinator_v3", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("system_coordinator_v3.initialize", "start")
        self.metrics_collector.gauge("system_coordinator_v3.initialized", 1)
        self.audit("初始化system_coordinator_v3", level="info")
        self.trace("system_coordinator_v3.initialize", "end")
        return {"success": True, "module": "system_coordinator_v3"}

module_class = SystemCoordinatorV3
