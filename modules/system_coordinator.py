# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI 系统核心协调器 v2.0
===============================
智能路由 + 经验驱动 + 事件协同 + 全模块互联

核心进化：
  v1.0: 关键词路由 → 只有3-4种执行路径
  v2.0: AI意图分析 + 经验库决策 + 模块能力感知 → 431模块全参与
"""

__module_meta__ = {
    "id": "system-coordinator",
    "name": "System Coordinator",
    "version": "1.0.0",
    "group": "system",
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
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "engine", "system"],
    "grade": "A",
    "description": "AUTO-EVO-AI 系统核心协调器 v2.0 ===============================",
}

import json
import logging
import asyncio
import time
import re
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("evo.coordinator")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # ============================================================================
    # 任务类型识别
    # ============================================================================
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

class TaskType:
    """任务类型枚举"""

    AI_ANALYSIS = "ai_analysis"  # AI分析/生成
    MODULE_EXEC = "module_exec"  # 内部模块执行
    BROWSER_OP = "browser_op"  # 浏览器操作
    FILE_OP = "file_op"  # 文件操作
    COMMAND = "command"  # 命令执行
    CODE_GEN = "code_gen"  # 代码生成
    WEB_SCRAPE = "web_scrape"  # 网页抓取
    NOTIFICATION = "notification"  # 通知推送
    DATA_PROCESS = "data_process"  # 数据处理
    SCHEDULE = "schedule"  # 定时调度
    MONITOR = "monitor"  # 监控报警
    LEARNING = "learning"  # 技能学习
    ORCHESTRATION = "orchestration"  # 多模块编排
    UNKNOWN = "unknown"

# ============================================================================
# 智能路由引擎
# ============================================================================

class SmartRouter:
    """
    智能路由引擎 v2.0
    - AI意图分析（优先）
    - 经验库匹配（次优先）
    - 模块能力感知（兜底）
    - 关键词规则（最末）
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        # 模块能力索引: category -> [module_ids]
        self._module_index: Dict[str, List[str]] = defaultdict(list)
        # 关键词到任务类型的映射
        self._keyword_map = self._build_keyword_map()
        # 经验缓存
        self._experience_cache: Dict[str, str] = {}

    def _build_keyword_map(self) -> Dict[str, str]:
        """构建关键词→任务类型映射"""
        return {
            TaskType.AI_ANALYSIS: ["分析", "评估", "判断", "预测", "研究", "analyze", "evaluate", "predict"],
            TaskType.MODULE_EXEC: ["执行", "运行", "调用", "模块", "execute", "run", "module"],
            TaskType.BROWSER_OP: [
                "浏览器",
                "网页",
                "打开",
                "点击",
                "截图",
                "browser",
                "navigate",
                "click",
                "screenshot",
            ],
            TaskType.FILE_OP: ["文件", "读取", "写入", "创建", "删除", "file", "read", "write", "create", "delete"],
            TaskType.COMMAND: ["命令", "shell", "终端", "cmd", "command", "bash"],
            TaskType.CODE_GEN: ["代码", "生成", "编写", "重构", "code", "generate", "refactor", "write"],
            TaskType.WEB_SCRAPE: ["抓取", "爬取", "扫描", "采集", "scrape", "crawl", "fetch", "scan"],
            TaskType.NOTIFICATION: ["通知", "推送", "发送", "提醒", "notify", "push", "send", "remind"],
            TaskType.DATA_PROCESS: ["数据", "处理", "清洗", "统计", "data", "process", "clean", "statistics"],
            TaskType.SCHEDULE: ["定时", "调度", "计划", "cron", "schedule", "cron", "periodic"],
            TaskType.MONITOR: ["监控", "告警", "健康", "状态", "monitor", "alert", "health", "status"],
            TaskType.LEARNING: ["学习", "训练", "适应", "learn", "train", "adapt", "skill"],
            TaskType.ORCHESTRATION: ["编排", "协调", "工作流", "orchestrate", "coordinate", "workflow"],
        }

    def build_module_index(self, mm, module_metadata: Dict):
        """构建模块能力索引"""
        self._module_index.clear()
        for module_id, meta in module_metadata.items():
            group = meta.get("group", "未分类")
            self._module_index[group].append(module_id)
            # 按标签索引
            tags = meta.get("tags", [])
            for tag in tags:
                self._module_index[tag].append(module_id)
        logger.info(f"[Router] 模块索引已建立: {len(self._module_index)} 个类别/标签")

    def _match_by_keywords(self, task: str) -> TaskType:
        """关键词匹配"""
        task_lower = task.lower()
        for task_type, keywords in self._keyword_map.items():
            for kw in keywords:
                if kw.lower() in task_lower:
                    return task_type
        return TaskType.UNKNOWN

    def _match_by_experience(self, task: str) -> Optional[Dict]:
        """
        断点3修复：从经验库 + 长期记忆智能匹配历史成功方案
        不仅匹配相似任务，还提取可复用的模块组合
        """
        # 缺口1修复：先查长期记忆（语义检索，覆盖更广）
        if self.coordinator._memory:
            try:
                relevant = self.coordinator._memory.query_memory(task, top_k=3)
                if relevant:
                    best = None
                    best_score = 0
                    for r in relevant:
                        entry = r.get("entry", {})
                        score = r.get("score", 0)
                        content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
                        agent_id = entry.get("metadata", {}).get("agent_id", "")
                        # 优先其他Agent的共享经验（避免重复犯错）
                        if score > best_score and score > 0.5:
                            best_score = score
                            best = {"content": content, "agent_id": agent_id, "score": score}
                    if best:
                        logger.info(
                            f"[MemoryRouter] 记忆命中: {best['content'][:60]} (score={best['score']:.0%}, agent={best['agent_id']})"
                        )
                        return {
                            "action": best["content"],
                            "context": best["content"],
                            "metadata": {"memory_source": "longterm", "agent_id": best["agent_id"]},
                            "score": best["score"],
                            "use_count": 1,
                        }
            except Exception as e:
                logger.debug(f"[MemoryRouter] 长期记忆检索跳过: {e}")

        if not self.coordinator._experience_base:
            return None

        task_lower = task.lower()

        # 优先从经验库查找相似成功经验
        similar = self.coordinator._experience_base.find_similar(task, limit=10)

        if similar:
            # 找成功率最高的经验
            best = max(similar, key=lambda e: e.success_rate * (e.use_count + 1) * 0.1)
            if best.success_rate >= 0.6 or best.use_count >= 2:
                logger.info(
                    f"[Experience] 命中经验: {best.action} (成功率: {best.success_rate:.0%}, 使用: {best.use_count}次)"
                )
                return {
                    "action": best.action,
                    "context": best.context,
                    "metadata": best.metadata or {},
                    "score": best.success_rate,
                    "use_count": best.use_count,
                }

        # 降级：查最近成功经验
        experiences = self.coordinator._experience_base.get_recent(limit=20)
        best = None
        best_score = 0
        for exp in experiences:
            if not exp.get("success"):
                continue
            exp_context = str(exp.get("context", "")).lower()
            exp_action = exp.get("action", "").lower()

            # 词重叠相似度
            words = set(task_lower.split())
            exp_words = set(exp_context.split()) | set(exp_action.split())
            overlap = len(words & exp_words)
            score = overlap / max(len(words), 1)

            if score > best_score and score > 0.15:
                best_score = score
                best = exp

        if best:
            return {
                "action": best.action,
                "context": best.context,
                "metadata": best.metadata or {},
                "score": best_score,
                "use_count": best.use_count,
            }

        return None

    def _match_modules_by_context(self, task: str, context: Dict) -> List[str]:
        """根据任务上下文匹配合适的模块"""
        matched = []
        task_lower = task.lower()

        # 1. 显式指定模块
        if context.get("module"):
            matched.append(context["module"])

        # 2. 从任务文本匹配模块名/标签
        for module_id, meta in self.coordinator._module_metadata.items():
            name = meta.get("name", "").lower()
            tags = [t.lower() for t in meta.get("tags", [])]
            group = meta.get("group", "").lower()

            score = 0
            # 模块名匹配
            for word in name.split():
                if word in task_lower:
                    score += 3
            # 标签匹配
            for tag in tags:
                if tag in task_lower:
                    score += 2
            # 分组匹配
            if group in task_lower:
                score += 1

            if score >= 2:
                matched.append(module_id)

        # 3. 按任务类型做兜底匹配
        task_type = self._match_by_keywords(task)
        if not matched:
            matched = self._fallback_by_type(task_type, task_lower)

        return list(dict.fromkeys(matched))  # 去重保持顺序

    def _fallback_by_type(self, task_type: str, task_lower: str) -> List[str]:
        """按任务类型兜底匹配模块"""
        fallback_map = {
            TaskType.AI_ANALYSIS: ["agent-orchestrator", "ai-gateway"],
            TaskType.MODULE_EXEC: ["module-manager", "agent-orchestrator"],
            TaskType.BROWSER_OP: ["browser-agent", "browser-use"],
            TaskType.FILE_OP: ["file-operations", "filesystem"],
            TaskType.COMMAND: ["shell-executor", "command-runner"],
            TaskType.CODE_GEN: ["code-generator", "code-template"],
            TaskType.WEB_SCRAPE: ["github-scanner", "web-crawler"],
            TaskType.NOTIFICATION: ["feishu-notifier", "pushnotify"],
            TaskType.DATA_PROCESS: ["data-processor", "excel-engine"],
            TaskType.SCHEDULE: ["task-scheduler", "smart-scheduler"],
            TaskType.MONITOR: ["system-monitor", "health-checker"],
            TaskType.LEARNING: ["skill-learner", "experience-base"],
            TaskType.ORCHESTRATION: ["workflow-manager", "agent-orchestrator"],
        }

        candidates = fallback_map.get(task_type, [])
        # 只返回实际注册了的模块
        registered = (
            (
                getattr(self.coordinator._mm, "module_registry", None)
                or getattr(self.coordinator._mm, "modules", None)
                or {}
            )
            if self.coordinator._mm
            else {}
        )
        return [m for m in candidates if m in registered]

    async def route(self, task: str, context: Dict = None) -> Dict:
        """
        智能路由主方法 v2.0
        优先级: 经验库(断点3) > AI分析 > 上下文匹配 > 关键词规则
        """
        context = context or {}
        task_lower = task.lower()
        reasoning_steps = []

        # Step 1: 经验库匹配（断点3修复 - 真正启用经验路由）
        exp_match = self._match_by_experience(task)
        if exp_match:
            action = exp_match.get("action", "")
            metadata = exp_match.get("metadata", {})

            # 经验里的action可能是模块ID，也可能是关键词
            if self.coordinator._mm and action in (
                getattr(self.coordinator._mm, "module_registry", None)
                or getattr(self.coordinator._mm, "modules", None)
                or {}
            ):
                reasoning_steps.append(f"✅ 经验库命中: {action} (成功率: {exp_match.get('score', 0):.0%})")
                return {
                    "task_type": TaskType.MODULE_EXEC,
                    "modules": [action],
                    "params": metadata,
                    "reasoning": reasoning_steps,
                    "source": "experience",
                    "_experience_id": exp_match.get("id"),
                }

            # 经验里没有精确模块ID，用关键词继续匹配
            if action:
                reasoning_steps.append(f"🔍 经验参考: {action[:50]}，继续智能匹配")

        # Step 2: AI意图分析（如果可用）
        if self.coordinator._ai_gateway:
            try:
                ai_result = self._ai_intent_analysis(task, context)
                if ai_result and ai_result.get("modules"):
                    reasoning_steps.append(f"✅ AI分析: {ai_result.get('intent', '?')} → {ai_result['modules']}")
                    return {
                        "task_type": ai_result.get("task_type", TaskType.MODULE_EXEC),
                        "modules": ai_result["modules"],
                        "params": ai_result.get("params", {}),
                        "reasoning": reasoning_steps,
                        "source": "ai",
                    }
            except Exception as e:
                reasoning_steps.append(f"⚠️ AI分析失败: {e}")

        # Step 3: 模块上下文匹配（整合经验关键词）
        matched = self._match_modules_by_context(task, context)
        task_type = self._match_by_keywords(task)

        if matched:
            reasoning_steps.append(f"✅ 上下文匹配: {matched} (类型={task_type})")
        else:
            reasoning_steps.append(f"⚠️ 无精确匹配，使用任务类型: {task_type}")
            matched = self._fallback_by_type(task_type, task_lower)

        return {
            "task_type": task_type,
            "modules": matched,
            "params": context.get("params", {}),
            "reasoning": reasoning_steps,
            "source": "keyword" if matched else "fallback",
        }

    async def _ai_intent_analysis(self, task: str, context: Dict) -> Optional[Dict]:
        """使用AI进行意图分析"""
        prompt = f"""分析以下任务，返回JSON格式：
{{"intent": "任务意图简述", "task_type": "ai_analysis/module_exec/browser_op/file_op/code_gen/web_scrape/notification/data_process/schedule/monitor/learning/orchestration/unknown", "modules": ["最适合的模块ID列表，最多3个"], "params": {{"额外参数"}}, "confidence": 0.0-1.0}}

任务: {task}

模块注册情况（部分）: {list((getattr(self.coordinator._mm, "module_registry", None) or getattr(self.coordinator._mm, "modules", None) or {}).keys())[:50] if self.coordinator._mm else []}

只返回JSON，不要其他文字。"""

        try:
            result = self.coordinator._ai_gateway.chat(
                messages=[{"role": "user", "content": prompt}], model="glm-4-flash"
            )
            import json

            # 尝试解析AI返回
            text = result.get("result", result.get("content", "")) if isinstance(result, dict) else str(result)
            # 提取JSON
            json_match = re.search(r'\{[^{}]*"modules"[^{}]*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("modules") and data.get("confidence", 0) > 0.5:
                    return data
        except Exception:
            pass
        return None

# ============================================================================
# 增强感知器
# ============================================================================

class EnhancedPerception:
    """
    增强感知器 v2.0
    感知范围：系统资源 + 事件总线 + 文件变化 + 时间 + 模块状态
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._last_perception = {}
        self._perception_count = 0
        self._perception_interval = 5  # 秒

    def should_perceive(self) -> bool:
        """是否需要执行感知"""
        self._perception_count += 1
        if self._perception_count % 10 == 0:
            return True
        return False

    async def perceive(self) -> Dict[str, Any]:
        """
        执行一次完整感知
        返回所有感知到的状态
        """
        perception = {
            "timestamp": datetime.now().isoformat(),
            "events": self._perceive_events(),
            "system": self._perceive_system(),
            "goals": self._perceive_goals(),
            "experience": self._perceive_experience(),
            "alerts": [],
        }

        # 检测变化
        alerts = self._detect_changes(perception)
        perception["alerts"] = alerts

        self._last_perception = perception
        return perception

    async def _perceive_events(self) -> Dict:
        """感知事件总线"""
        if not self.coordinator._event_bus:
            return {"active": False}

        stats = self.coordinator._event_bus.get_stats()
        recent = self.coordinator._event_bus.get_recent_events(limit=5)
        return {
            "active": True,
            "total_published": stats.get("published", 0),
            "recent": [e.get("type") for e in recent],
        }

    def _perceive_system(self) -> Dict:
        """感知系统资源"""
        system_info = {"cpu": 0, "memory": 0, "disk": 0, "status": "unknown"}

        try:
            import psutil

            system_info = {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
                "status": "healthy" if psutil.virtual_memory().percent < 85 else "warning",
            }
        except ImportError:
            system_info["status"] = "psutil_not_available"
        except Exception:
            pass

        return system_info

    def _perceive_goals(self) -> Dict:
        """感知目标进度"""
        if not self.coordinator._goal_tracker:
            return {"active": False}

        try:
            report = self.coordinator._goal_tracker.get_report()
            return {
                "active": True,
                "goals": report.get("goals", []),
                "summary": report.get("summary", {}),
            }
        except Exception:
            return {"active": False}

    def _perceive_experience(self) -> Dict:
        """感知经验库状态"""
        if not self.coordinator._experience_base:
            return {"active": False}

        try:
            recent = self.coordinator._experience_base.get_recent(limit=10)
            recent_success = [e for e in recent if e.get("success")]
            return {
                "active": True,
                "total": len(recent),
                "recent_success_rate": len(recent_success) / max(len(recent), 1),
            }
        except Exception:
            return {"active": False}

    def _detect_changes(self, perception: Dict) -> List[str]:
        """检测状态变化，生成告警"""
        alerts = []

        # 系统资源告警
        sys = perception.get("system", {})
        if sys.get("memory", 0) > 85:
            alerts.append(f"⚠️ 内存使用率过高: {sys['memory']:.1f}%")
        if sys.get("cpu", 0) > 90:
            alerts.append(f"⚠️ CPU使用率过高: {sys['cpu']:.1f}%")

        # 事件活跃度
        events = perception.get("events", {})
        if events.get("active") and events.get("total_published", 0) > 0:
            alerts.append(f"📡 事件总线活跃: {events['total_published']} 条事件")

        return alerts

# ============================================================================
# 反思引擎
# ============================================================================

class ReflectionEngine(object):
    """
    反思引擎 v2.0
    每次执行后自动反思：成功？失败？原因？如何改进？
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._reflection_log: List[Dict] = []

    async def reflect(self, task: str, result: Dict, route_info: Dict):
        """
        执行反思
        1. 记录经验
        2. 更新模块权重
        3. 发布反思事件
        """
        success = result.get("success", False)
        reflection = {
            "task": task,
            "success": success,
            "result": str(result.get("result", ""))[:200],
            "error": result.get("error"),
            "modules_used": route_info.get("modules", []),
            "task_type": route_info.get("task_type"),
            "source": route_info.get("source"),
            "timestamp": datetime.now().isoformat(),
        }

        # 1. 记录到经验库（断点3 - 正确的参数顺序）
        if self.coordinator._experience_base:
            try:
                pass
                # context=任务描述，action=使用的模块，result=执行结果
                self.coordinator._experience_base.add_experience(
                    context=task,
                    action="|".join(route_info.get("modules", [])),
                    result=str(result)[:500],
                    success=success,
                    tags=route_info.get("modules", []),
                )
                reflection["experience_recorded"] = True
            except Exception as e:
                reflection["experience_error"] = str(e)

        # 2. 发布反思事件
        if self.coordinator._event_bus:
            try:
                self.coordinator._event_bus.publish(
                    "system.reflection", data=reflection, source="coordinator", metadata={"success": success}
                )
            except Exception:
                pass

        # 3. 自我修复检查
        if not success and self.coordinator._self_healing:
            try:
                self.coordinator._self_healing.record_error(
                    error=Exception(str(result.get("error", ""))),
                    component="|".join(route_info.get("modules", [])),
                    severity="medium",
                )
            except Exception:
                pass

        self._reflection_log.append(reflection)
        return reflection

    def get_insights(self) -> Dict:
        """获取反思洞察"""
        if not self._reflection_log:
            return {"insights": [], "summary": "暂无反思数据"}

        recent = self._reflection_log[-50:]
        success_count = sum(1 for r in recent if r["success"])
        failure_count = len(recent) - success_count

        # 分析失败模式
        failures_by_module = defaultdict(int)
        for r in recent:
            if not r["success"]:
                for m in r.get("modules_used", []):
                    failures_by_module[m] += 1

        return {
            "summary": {
                "total": len(recent),
                "success": success_count,
                "failure": failure_count,
                "success_rate": success_count / len(recent) if recent else 0,
            },
            "failure_patterns": dict(failures_by_module),
            "insights": [
                f"成功率 {success_count / len(recent) * 100:.0f}%" if recent else "无数据",
                f"最高失败模块: {max(failures_by_module, key=failures_by_module.get) if failures_by_module else '无'}",
            ],
        }

# ============================================================================
# 系统核心协调器 v2.0
# ============================================================================

class SystemCoordinator(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    AUTO-EVO-AI 系统核心协调器 v2.0

    进化要点：
    - 智能路由：AI分析 + 经验驱动 + 上下文感知
    - 增强感知：系统资源 + 事件总线 + 目标进度 + 经验模式
    - 反思回流：每次执行后反思 + 经验记录 + 自我修复
    - 全模块互联：431模块通过事件总线和协调器真正互通
    """

    VERSION = "2.0.0"

    def __init__(self):
        super().__init__()
        self.initialized = False
        self.start_time = None
        self.modules: Dict[str, Any] = {}
        self.status = "stopped"

        # 模块引用
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

        # v2.0 核心组件
        self.router = SmartRouter(self)
        self.perception = EnhancedPerception(self)
        self.reflection = ReflectionEngine(self)

        # 断点6初始化：增强感知
        self._file_watch_paths: Dict[str, float] = {}
        self._file_watch_thread: Optional[threading.Thread] = None
        self._file_watch_running = False
        self._external_events: List[Dict] = []
        self._last_resource_check = 0.0
        self._resource_check_interval = 30.0

        # 执行统计
        self._stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "by_type": defaultdict(int),
            "by_module": defaultdict(int),
        }

        # 模块元数据缓存
        self._module_metadata: Dict = {}

        # 断点1: 统一执行器
        self._unified_executor = None

        logger.info(f"[Coordinator v2.0] 创建 | 智能路由 + 反思引擎")

    def register_module(self, name: str, module: Any):
        """注册模块"""
        self.modules[name] = module
        logger.debug(f"[Coordinator] 注册: {name}")

    def initialize(
        self,
        mm=None,
        ai_gateway=None,
        memory=None,
        workflow=None,
        event_bus=None,
        autonomous_agent=None,
        external_executor=None,
        goal_tracker=None,
        self_healing=None,
        experience_base=None,
        resilience=None,
        module_metadata: Dict = None,
    ):
        """初始化所有模块"""

        self._mm = mm
        self._ai_gateway = ai_gateway
        self._memory = memory
        self._workflow = workflow
        self._event_bus = event_bus
        self._autonomous_agent = autonomous_agent
        self._external_executor = external_executor
        self._goal_tracker = goal_tracker
        self._self_healing = self_healing
        self._experience_base = experience_base
        self._resilience = resilience
        self._module_metadata = module_metadata or {}

        modules_map = {
            "module_manager": mm,
            "ai_gateway": ai_gateway,
            "memory_engine": memory,
            "workflow_engine": workflow,
            "event_bus": event_bus,
            "autonomous_agent": autonomous_agent,
            "external_executor": external_executor,
            "goal_tracker": goal_tracker,
            "self_healing": self_healing,
            "experience_base": experience_base,
            "resilience": resilience,
        }

        for name, module in modules_map.items():
            if module:
                self.register_module(name, module)

        # 构建智能路由索引
        if mm and self._module_metadata:
            self.router.build_module_index(mm, self._module_metadata)

        # 注册事件订阅
        self._register_event_subscriptions()

        # 断点5：启动自主智能体主循环
        if self._autonomous_agent:
            try:
                self._autonomous_agent.start()
                logger.info("[Coordinator] 自主智能体已启动并接入主路径")
            except Exception as e:
                logger.warning(f"[Coordinator] 自主智能体启动失败: {e}")

        # 断点6：注册默认文件监控路径（项目目录）
        project_root = Path(__file__).parent.parent
        self.watch_path(str(project_root))

        # 断点1: 初始化统一执行器
        try:
            from modules.module_adapter import create_unified_executor

            self._unified_executor = create_unified_executor(self)
            logger.info("[Coordinator] 统一执行器(ModuleAdapter)已加载")
        except Exception as e:
            logger.warning(f"[Coordinator] 统一执行器初始化失败: {e}")

        self.initialized = True
        self.status = "ready"
        self.start_time = datetime.now()

        logger.info(f"[Coordinator v2.0] 初始化完成 | {len(self.modules)} 模块 | {len(self._module_metadata)} 元数据")

    def _register_event_subscriptions(self):
        """注册事件订阅，建立模块互联"""
        if not self._event_bus:
            return

        # 任务完成 → 更新经验库
        self._event_bus.subscribe("task.completed", self._on_task_completed)
        # 任务失败 → 触发自我修复
        self._event_bus.subscribe("task.failed", self._on_task_failed)
        # 模块注册 → 重建索引
        self._event_bus.subscribe("module.registered", self._on_module_registered)
        # 目标更新 → 发布状态
        self._event_bus.subscribe("goal.updated", self._on_goal_updated)
        # 系统告警 → 自动处理
        self._event_bus.subscribe("system.alert", self._on_system_alert)
        # 缺口3修复：记忆共享 → 通知所有Agent同步
        self._event_bus.subscribe("memory.shared", self._on_memory_shared)

        logger.info("[Coordinator] 事件订阅已注册 (5个通道)")

    def _on_task_completed(self, event):
        """任务完成事件处理"""
        logger.debug(f"任务完成: {event.get('data', {}).get('task', '?')}")

    def _on_task_failed(self, event):
        """任务失败事件处理"""
        data = event.get("data", {})
        if self._self_healing:
            self._self_healing.record_error(
                error=Exception(data.get("error", "unknown")),
                component=data.get("module", "unknown"),
                severity="medium",
            )

    def _on_module_registered(self, event):
        """模块注册事件处理"""
        self.router.build_module_index(self._mm, self._module_metadata)

    def _on_goal_updated(self, event):
        """目标更新事件处理"""
        logger.debug(f"目标更新: {event.get('data', {}).get('name', '?')}")

    def _on_system_alert(self, event):
        """系统告警事件处理"""
        alert = event.get("data", {})
        logger.warning(f"系统告警: {alert}")

        # 内存告警 → 触发GC
        if "memory" in str(alert).lower() and "high" in str(alert).lower():
            import gc

            gc.collect()
            logger.info("[Coordinator] 内存告警触发GC")

    def _on_memory_shared(self, event):
        """缺口3修复：记忆共享事件处理 — 记录日志并转发给自主智能体"""
        data = event.get("data", {})
        memory_id = data.get("memory_id", "")
        agent_id = data.get("agent_id", "")
        visibility = data.get("visibility", "")
        shared_with = data.get("shared_with", [])
        logger.info(f"[Coordinator] 记忆共享事件: {memory_id} from={agent_id} vis={visibility} to={shared_with}")

        # 转发给自主智能体，让它更新本地记忆索引
        if self._autonomous_agent and hasattr(self._autonomous_agent, "on_memory_shared"):
            try:
                self._autonomous_agent.on_memory_shared(data)
            except Exception as e:
                logger.debug(f"[Coordinator] 转发记忆共享到自主智能体失败: {e}")

    # ========================================================================
    # 统一执行接口
    # ========================================================================

    async def execute(self, task: str, context: Dict = None) -> Dict:
        """统一执行接口 - 智能路由 + 执行 + 反思"""
        _ = self.trace("execute")
        metrics_collector.counter("system_coordinator_ops_total", labels={"task": task})
        self.audit("execute", f"task={task}")
        if not self.initialized:
            return {"success": False, "error": "系统未初始化"}

        self._stats["total_tasks"] += 1
        context = context or {}
        context["timestamp"] = datetime.now().isoformat()

        # 断点4: 检查是否需要自动创建目标
        goal_context = None
        if context.get("auto_create_goal", False):
            goal_context = self.intent_to_goal(task)
            context["_goal"] = goal_context

        try:
            pass
            # Step 0: 断点6 - 增强感知（每次执行前检查环境）
            resource_info = self.perceive_resources()
            if resource_info:
                context["_resource"] = resource_info

            # 断点6 - 检查外部事件
            ext_events = self.get_external_events(limit=5)
            if ext_events:
                context["_external_events"] = ext_events
                # 如果有文件变化事件，自动刷新模块索引
                for evt in ext_events:
                    if evt.get("type") == "file_changed":
                        logger.debug(f"[Perception] 文件变化: {evt.get('path')}")

            # Step 1: 智能路由（含断点3 - 经验路由增强）
            route_info = self.router.route(task, context)

            # Step 2: 检查系统健康
            if self._self_healing:
                health = self._self_healing.check_health()
                if health.get("status") != "healthy":
                    logger.warning(f"[Coordinator] 健康检查: {health['status']}")

            # Step 3: 发布执行开始事件
            if self._event_bus:
                self._event_bus.publish("task.starting", data={"task": task, "route": route_info}, source="coordinator")

            # Step 4: 执行任务（支持多模块编排，AutonomousAgent主路径参与）
            result = self._execute_routed(route_info, task, context)

            # Step 5: 断点7 - 结果验证
            for module_id in route_info.get("modules", []):
                if result.get("success") is not None:
                    validation = self._validate_result(module_id, result, task)
                    result["_validation"] = validation
                    if not validation.get("valid"):
                        logger.warning(f"[Validator] 结果可能有问题: {validation['issues']}")

            # Step 6: 反思（含经验记录）
            reflection = self.reflection.reflect(task, result, route_info)

            # Step 7: 断点4: 更新目标进度
            if goal_context and self._goal_tracker and goal_context.get("success"):
                goal_obj = goal_context.get("goal")
                goal_id = getattr(goal_obj, "id", "") if goal_obj else ""
                if goal_id:
                    if result.get("success"):
                        self._goal_tracker.complete_goal(goal_id)
                    else:
                        self._goal_tracker.fail_goal(goal_id, str(result.get("error", "")))

            # Step 8: 发布完成事件
            if self._event_bus:
                event_type = "task.completed" if result.get("success") else "task.failed"
                self._event_bus.publish(
                    event_type, data={"task": task, "result": result, "reflection": reflection}, source="coordinator"
                )

            # 更新统计
            self._stats["by_type"][route_info["task_type"]] += 1
            for m in route_info.get("modules", []):
                self._stats["by_module"][m] += 1
            if result.get("success"):
                self._stats["successful_tasks"] += 1
            else:
                self._stats["failed_tasks"] += 1

            result["_route"] = route_info
            result["_reflection"] = reflection
            result["_goal"] = goal_context
            return result

        except Exception as e:
            logger.error(f"[Coordinator] 执行异常: {e}")
            self._stats["failed_tasks"] += 1
            return {"success": False, "error": str(e)}

    async def _execute_routed(self, route_info: Dict, task: str, context: Dict) -> Dict:
        """
        执行路由后的任务
        断点5修复：AutonomousAgent 升级为主路径参与者，非仅作fallback
        - 优先级: 精确模块匹配 > 经验路由 > AI分析 > AutonomousAgent主循环 > 关键词兜底
        """
        modules = route_info.get("modules", [])
        params = route_info.get("params", {})
        task_type = route_info.get("task_type", TaskType.UNKNOWN)
        source = route_info.get("source", "unknown")

        # 断点5: AutonomousAgent 作为并行候选（非仅fallback）
        # 当经验路由命中 或 AI分析置信度低 时，AutonomousAgent 同时参与决策
        use_autonomous = (
            source == "experience"  # 经验路由 → AutonomousAgent 复验
            or source == "fallback"  # 兜底路由 → AutonomousAgent 主力
            or len(modules) == 0  # 无匹配 → AutonomousAgent 兜底
        )

        # Step 1: 精确模块执行（最高优先级）
        if modules:
            results = []
            for module_id in modules:
                try:
                    r = self._execute_single_module(module_id, task, params, context)
                    results.append({"module": module_id, "result": r})
                    if r.get("success"):
                        # 断点5: 同时通知 AutonomousAgent 执行结果（用于学习）
                        if self._autonomous_agent:
                            self._autonomous_agent.execute_action(
                                {
                                    "type": "module_executed",
                                    "module_id": module_id,
                                    "task": task,
                                    "result": r,
                                    "context": context,
                                }
                            )
                        return r
                except Exception as e:
                    results.append({"module": module_id, "error": str(e)})
                    continue

            # 模块全部失败，记录失败经验
            if self._autonomous_agent and not use_autonomous:
                self._autonomous_agent.execute_action(
                    {
                        "type": "execution_failed",
                        "modules": modules,
                        "task": task,
                        "error": results,
                    }
                )

        # Step 2: AutonomousAgent 主循环参与执行
        if self._autonomous_agent and use_autonomous:
            logger.info(f"[Coordinator] AutonomousAgent 接管执行 (source={source})")
            action_result = self._autonomous_agent.execute_action(
                {
                    "type": "coordinator_task",
                    "task": task,
                    "context": context,
                    "route_info": route_info,
                    "priority": "high" if source in ["experience", "fallback"] else "normal",
                }
            )

            if action_result.get("success"):
                return {
                    "success": True,
                    "result": action_result.get("result"),
                    "source": "autonomous_agent",
                    "_route": route_info,
                }

            # AutonomousAgent 也失败
            if modules:
                return {
                    "success": False,
                    "error": f"模块执行失败，且AutonomousAgent无法处理: {task}",
                    "attempts": results,
                    "autonomous_error": action_result.get("error"),
                }
            return {
                "success": False,
                "error": f"AutonomousAgent无法处理: {task}",
                "autonomous_result": action_result,
            }

        # Step 3: 完全无可用路径
        return {
            "success": False,
            "error": f"无可用执行路径 (source={source})",
            "attempts": results if "results" in dir() else [],
        }

    async def _execute_single_module(self, module_id: str, task: str, params: Dict, context: Dict) -> Dict:
        """执行单个模块"""
        # 内部模块
        mm_modules = (
            (getattr(self._mm, "module_registry", None) or getattr(self._mm, "modules", None) or {}) if self._mm else {}
        )
        if module_id in mm_modules:
            return self._mm.execute_module(module_id, {"input": task, **params, "context": context})

        # 外部执行器
        if self._external_executor:
            if module_id in ["browser-agent", "browser-use"]:
                return self._external_executor.execute_browser({"task": task, **params})
            if module_id in ["file-operations", "filesystem"]:
                return self._external_executor.execute_fs({"task": task, **params})
            if module_id in ["shell-executor", "command-runner"]:
                return self._external_executor.execute_cmd({"task": task, **params})

        # AI网关
        if self._ai_gateway and module_id == "ai-gateway":
            messages = context.get("messages", [{"role": "user", "content": task}])
            result = self._ai_gateway.chat(messages)
            return {"success": True, "type": "ai", "result": result}

        # 工作流引擎
        if self._workflow and module_id == "workflow-manager":
            return self._workflow.run_workflow(task, params)

        # 自主智能体
        if self._autonomous_agent and module_id == "autonomous-agent":
            return self._autonomous_agent.execute_action({"type": "ai_task", "task": task, "context": context})

        return {"success": False, "error": f"模块 {module_id} 未找到或不可执行"}

    # ========================================================================
    # 目标管理
    # ========================================================================

    def set_goal(self, name: str, description: str = "", priority: str = "MEDIUM") -> Dict:
        """设置目标"""
        if self._goal_tracker:
            goal = self._goal_tracker.create_goal(name, description, priority)
            # 发布目标事件
            if self._event_bus:
                asyncio.create_task(self._event_bus.publish("goal.created", data={"goal": goal}, source="coordinator"))
            return {"success": True, "goal": goal}
        return {"success": False, "error": "目标追踪器未初始化"}

    def get_goal_progress(self) -> Dict:
        """获取目标进度"""
        if self._goal_tracker:
            return self._goal_tracker.get_report()
        return {"success": False, "error": "目标追踪器未初始化"}

    # ========================================================================
    # 断点6修复：增强感知层（系统资源+文件变化+外部事件）
    # ========================================================================

    def watch_path(self, path: str):
        """添加文件监控路径"""
        if not self._file_watch_paths:
            self._file_watch_running = True
            self._file_watch_thread = threading.Thread(target=self._file_watch_loop, daemon=True)
            self._file_watch_thread.start()
            logger.info("[Perception] 文件监控线程已启动")
        if os.path.exists(path):
            self._file_watch_paths[path] = os.path.getmtime(path)
            logger.info(f"[Perception] 监控路径: {path}")

    def _file_watch_loop(self):
        """文件监控循环"""
        while self._file_watch_running:
            for path, last_mtime in list(self._file_watch_paths.items()):
                try:
                    if os.path.exists(path):
                        current_mtime = os.path.getmtime(path)
                        if current_mtime > last_mtime:
                            self._file_watch_paths[path] = current_mtime
                            self._on_file_changed(path)
                except Exception:
                    pass
            time.sleep(2)

    def _on_file_changed(self, path: str):
        """文件变化事件处理"""
        if self._event_bus:
            asyncio.create_task(
                self._event_bus.publish("file.changed", data={"path": path, "type": "file"}, source="coordinator")
            )
        self._external_events.append({"type": "file_changed", "path": path, "timestamp": datetime.now().isoformat()})
        if len(self._external_events) > 100:
            self._external_events = self._external_events[-50:]

    def perceive_resources(self) -> Dict:
        """感知系统资源（CPU/内存/磁盘）"""
        now = time.time()
        if now - self._last_resource_check < self._resource_check_interval:
            return {}
        self._last_resource_check = now
        info = {}
        try:
            import psutil

            info = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
            if info.get("memory_percent", 0) > 85:
                import gc

                gc.collect()
                logger.info("[Perception] 内存过高触发GC")
                if self._event_bus:
                    asyncio.create_task(
                        self._event_bus.publish(
                            "system.alert",
                            data={"type": "memory_high", "value": info["memory_percent"]},
                            source="coordinator",
                        )
                    )
        except ImportError:
            info = {"status": "psutil_not_available"}
        except Exception:
            pass
        return info

    def get_external_events(self, limit: int = 20) -> List[Dict]:
        """获取外部事件"""
        return self._external_events[-limit:]

    # ========================================================================
    # 断点7修复：执行结果验证
    # ========================================================================

    def _validate_result(self, module_id: str, result: Dict, task: str) -> Dict:
        """轻量级结果验证"""
        validation = {"module_id": module_id, "valid": True, "checks": [], "issues": []}

        if not result.get("success"):
            validation["valid"] = False
            validation["issues"].append("success标记为False")
            validation["checks"].append(("success", False))
        else:
            validation["checks"].append(("success", True))

        has_result = any(result.get(k) for k in ["result", "data", "output", "message", "summary"])
        if not has_result:
            validation["checks"].append(("has_content", False))
            if module_id in ["filesystem", "file-operations"]:
                output = result.get("output", {})
                path = output.get("path") if isinstance(output, dict) else None
                if path and os.path.exists(path):
                    validation["checks"].append(("file_exists", True))
                else:
                    validation["valid"] = False
                    validation["issues"].append("文件系统操作但输出文件不存在")
        else:
            validation["checks"].append(("has_content", True))

        duration = result.get("execution_time", result.get("duration_ms", 0))
        if isinstance(duration, (int, float)) and duration > 300:
            validation["checks"].append(("execution_time", "slow"))
            validation["issues"].append(f"执行时间过长: {duration:.1f}s")
        else:
            validation["checks"].append(("execution_time", "normal"))

        error = result.get("error", "")
        if error:
            recoverable = ["timeout", "connection", "temporary"]
            if any(e in str(error).lower() for e in recoverable):
                validation["checks"].append(("recoverable_error", True))
            else:
                validation["checks"].append(("recoverable_error", False))

        return validation

    # ========================================================================
    # 断点4修复：用户意图自动转目标
    # ========================================================================

    async def intent_to_goal(self, user_input: str) -> Dict:
        """
        将用户意图自动转为目标，并进行子目标分解
        断点4修复：自动化目标创建链路
        """
        if not self._goal_tracker:
            return {"success": False, "error": "目标追踪器未初始化"}

        # 自动从任务文本提取目标名称
        goal_name = user_input.strip()
        if len(goal_name) > 80:
            goal_name = goal_name[:80] + "..."

        # 提取优先级
        priority_map = {"紧急": 1, "高": 2, "中": 3, "低": 4, "高优": 2}
        priority = 3  # 默认MEDIUM
        for kw, p in priority_map.items():
            if kw in user_input:
                priority = p
                goal_name = goal_name.replace(kw, "").strip()
                break

        # 创建主目标
        goal = self._goal_tracker.create_goal(name=goal_name, description=f"用户意图: {user_input}", priority=priority)

        # 自动分解子目标
        sub_goals = self._decompose_goal(goal, user_input)
        for sg in sub_goals:
            self._goal_tracker.create_goal(
                name=sg["name"],
                description=sg.get("description", ""),
                priority=sg.get("priority", priority),
                parent_id=goal.id,
            )

        # 发布目标创建事件
        if self._event_bus:
            self._event_bus.publish(
                "goal.intent_converted",
                data={
                    "goal_id": goal.id,
                    "goal_name": goal.name,
                    "user_input": user_input,
                    "sub_goals_count": len(sub_goals),
                },
                source="coordinator",
            )

        return {"success": True, "goal": goal, "sub_goals": sub_goals}

    async def _decompose_goal(self, goal: Any, user_input: str) -> List[Dict]:
        """分解目标为子目标"""
        sub_goals = []

        # 复杂关键词列表
        complex_keywords = [
            "多个",
            "分析",
            "优化",
            "全面",
            "检查",
            "创建",
            "生成",
            "整理",
            "扫描",
            "监控",
            "报告",
            "评估",
        ]

        # 使用AI分解
        if self._ai_gateway and self._ai_gateway.models:
            try:
                prompt = f"""将以下用户任务分解为2-5个具体子目标，返回JSON数组：

用户任务: {user_input}

返回格式:
[
    {{"name": "子目标1名称", "description": "描述", "priority": 优先级数字}},
    {{"name": "子目标2名称", "description": "描述", "priority": 优先级数字}}
]

只返回JSON数组，不要其他文字。"""

                result = self._ai_gateway.chat(messages=[{"role": "user", "content": prompt}], model="glm-4-flash")
                text = result.get("result", "") if isinstance(result, dict) else str(result)
                import re

                json_match = re.search(r"\[.*\]", text, re.DOTALL)
                if json_match:
                    import json as json_mod

                    sub_goals = json_mod.loads(json_match.group())
            except Exception:
                pass

        # 规则兜底
        if not sub_goals:
            text_lower = user_input.lower()
            if "分析" in text_lower or "扫描" in text_lower:
                sub_goals = [
                    {"name": "收集数据", "description": "获取必要的数据源"},
                    {"name": "执行分析", "description": "按需求执行分析处理"},
                    {"name": "生成结果", "description": "输出分析结果"},
                ]
            elif "监控" in text_lower:
                sub_goals = [
                    {"name": "检查监控指标", "description": "获取系统监控数据"},
                    {"name": "分析异常", "description": "检测异常指标"},
                    {"name": "告警", "description": "如有异常则告警"},
                ]
            elif "生成" in text_lower or "创建" in text_lower:
                sub_goals = [
                    {"name": "准备数据", "description": "收集生成所需数据"},
                    {"name": "生成内容", "description": "执行内容生成"},
                    {"name": "输出结果", "description": "保存或发送结果"},
                ]

        return sub_goals

    # ========================================================================
    # 状态查询
    # ========================================================================

    def get_status(self) -> Dict:
        """获取系统状态"""
        status = {
            "version": f"v6.37 COORDINATED",
            "coordinator_version": self.VERSION,
            "status": self.status,
            "initialized": self.initialized,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "modules": {
                "registered": len(self.modules),
                "metadata_count": len(self._module_metadata),
                "names": list(self.modules.keys()),
            },
            "execution_stats": {
                "total": self._stats["total_tasks"],
                "success": self._stats["successful_tasks"],
                "failed": self._stats["failed_tasks"],
                "rate": self._stats["successful_tasks"] / max(self._stats["total_tasks"], 1),
                "by_type": dict(self._stats["by_type"]),
                "top_modules": dict(sorted(self._stats["by_module"].items(), key=lambda x: -x[1])[:5]),
            },
            "services": {},
            "intelligence": {
                "router": "smart_v2",
                "perception": "enhanced",
                "reflection": "active",
                "event_bus": self._event_bus is not None,
                "experience": self._experience_base is not None,
            },
        }

        # 各服务状态
        if self._memory:
            status["services"]["memory"] = "active"
        if self._ai_gateway:
            status["services"]["ai"] = f"active ({len(self._ai_gateway.models)} models)"
        if self._autonomous_agent:
            agent_status = self._autonomous_agent.get_status()
            status["services"]["autonomous_agent"] = agent_status.get("state", "unknown")
        if self._self_healing:
            health = self._self_healing.check_health()
            status["services"]["self_healing"] = health.get("overall", "unknown")
        if self._event_bus:
            eb_stats = self._event_bus.get_stats()
            status["services"]["event_bus"] = f"active ({eb_stats.get('published', 0)} published)"

        return status

    def get_capabilities(self) -> Dict:
        """获取系统能力"""
        return {
            "perception": {
                "system_resources": True,
                "events": self._event_bus is not None,
                "goals": self._goal_tracker is not None,
                "experience": self._experience_base is not None,
                "files": self._external_executor is not None,
                "browser": self._external_executor is not None,
            },
            "decision": {
                "ai_intent": self._ai_gateway is not None,
                "experience_matching": self._experience_base is not None,
                "context_aware": True,
                "rule_based": True,
            },
            "execution": {
                "internal_modules": self._mm is not None,
                "external": self._external_executor is not None,
                "commands": self._external_executor is not None,
                "multi_module": True,
            },
            "learning": {
                "reflection": True,
                "experience_base": self._experience_base is not None,
                "skill_creation": True,
                "goals": self._goal_tracker is not None,
            },
            "resilience": {
                "circuit_breaker": self._resilience is not None,
                "retry": self._resilience is not None,
                "fallback": self._resilience is not None,
                "self_healing": self._self_healing is not None,
                "gc_on_alert": True,
            },
            "autonomy": {
                "continuous": self._autonomous_agent is not None,
                "scheduled": True,
                "event_driven": self._event_bus is not None,
                "goal_driven": self._goal_tracker is not None,
            },
            "coordination": {
                "smart_router": True,
                "event_pubsub": self._event_bus is not None,
                "cross_module": True,
            },
        }

    def get_automation_score(self) -> int:
        """计算自动化能力评分"""
        caps = self.get_capabilities()
        weights = {
            "perception": 15,
            "decision": 20,
            "execution": 20,
            "learning": 15,
            "resilience": 15,
            "autonomy": 10,
            "coordination": 5,
        }

        score = 0
        for category, weight in weights.items():
            features = caps.get(category, {})
            if isinstance(features, dict):
                available = sum(1 for v in features.values() if v)
                total = len(features)
                score += (available / max(total, 1)) * weight

        return min(int(score), 100)

    def get_dashboard_data(self) -> Dict:
        """获取Dashboard展示数据"""
        caps = self.get_capabilities()
        score = self.get_automation_score()
        status = self.get_status()

        return {
            "automation_score": score,
            "score_level": "AUTOMATED" if score >= 95 else "ENHANCED" if score >= 80 else "BASIC",
            "version": status["version"],
            "modules_registered": len(self.modules),
            "modules_metadata": len(self._module_metadata),
            "execution_rate": f"{status['execution_stats']['rate'] * 100:.1f}%",
            "capabilities": caps,
            "coordination_enhanced": True,
            "smart_router_active": True,
            "reflection_active": True,
            "event_bus_active": self._event_bus is not None,
        }

    def health_check(self) -> dict:
        """Health check"""
        return {"status": "healthy", "module": self.__class__.__name__}

    async def shutdown(self) -> None:
        """Shutdown module"""
        self._status = "stopped"

# ============================================================================
# 便捷函数
# ============================================================================

def create_coordinator() -> SystemCoordinator:
    """创建并初始化协调器"""
    return SystemCoordinator()

    async def _async_health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": getattr(self.status, "value", "unknown"),
            "healthy": True,
            "module": "unknown",
            "uptime": self._uptime() if hasattr(self, "_uptime") else 0,
        }

    async def shutdown(self) -> None:
        self.status = ModuleStatus.STOPPED

    def health_check(self) -> Dict[str, Any]:
        """同步健康检查（基类要求）"""
        return {"status": "healthy", "module_id": self.module_id}

    async def execute(self, action: str, params: dict = None) -> dict:
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
        if action == "counter":
            try:
                r = self.counter(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "gauge":
            try:
                r = self.gauge(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "histogram":
            try:
                r = self.histogram(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "increment":
            try:
                r = self.increment(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown action: {}".format(action)}

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

module_class = SystemCoordinator
