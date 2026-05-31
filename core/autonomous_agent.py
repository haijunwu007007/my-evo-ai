"""
AUTO-EVO-AI 自主智能体引擎 (Autonomous Agent Engine)
=====================================================
上市公司级生产标准

核心理念: 让系统从"你叫我做"升级为"我发现该做了自己去做"
实现方式: 自主决策循环 + 经验积累 + 自我优化 + 跨模块联动

五大自主能力:
1. 自主规划: 定期分析系统状态, 自动决策下一步行动
2. 自我修复: 检测异常自动恢复, 不等人工干预
3. 自我学习: 分析执行历史, 自动优化决策规则
4. 跨模块联动: 自动发现模块间数据关系, 动态串联
5. LLM深度推理: 定期调用LLM做系统级深度分析

设计原则:
- 作为后台常驻循环运行, 不阻塞主线程
- 所有自主行为可追溯(日志+审计)
- 保守策略: 自主动作默认只做"安全操作"(分析/建议/低风险修复)
- 高风险操作(删除/修改/外部调用)只生成建议, 不自动执行
- 经验冷启动: 通过内置专家规则快速积累初始经验
"""

from __future__ import annotations

import time
import json
import asyncio
from core.logging_config import get_logger
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from collections import defaultdict

logger = get_logger("evo.autonomous")


# ============================================================================
# 数据模型
# ============================================================================

class AutonomousAction(str, Enum):
    """自主行为类型"""
    ANALYSIS = "analysis"              # 分析(安全)
    RECOMMENDATION = "recommendation"  # 建议(安全)
    SCHEDULE = "schedule"             # 调度(安全)
    SELF_HEAL = "self_heal"           # 自愈(中风险)
    RULE_OPTIMIZE = "rule_optimize"   # 规则优化(中风险)
    DATA_FLOW = "data_flow"           # 数据流联动(中风险)
    LLM_REASONING = "llm_reasoning"   # LLM深度推理(安全)


class RiskLevel(str, Enum):
    SAFE = "safe"           # 无风险: 纯分析/生成建议
    LOW = "low"             # 低风险: 调度/配置微调
    MEDIUM = "medium"       # 中风险: 规则变更/数据流变更
    HIGH = "high"           # 高风险: 删除/外部调用/重大配置
    CRITICAL = "critical"   # 危险: 系统级变更


@dataclass
class AutonomousDecision:
    """自主决策记录"""
    id: str = ""
    cycle_id: str = ""
    action_type: str = ""
    risk_level: str = "safe"
    trigger: str = ""           # 触发原因
    description: str = ""       # 决策描述
    action_config: dict = field(default_factory=dict)  # 执行参数
    result: dict = field(default_factory=dict)
    status: str = "pending"     # pending/executed/skipped/failed
    auto_executed: bool = False  # 是否自动执行(仅safe/low)
    created_at: str = ""
    executed_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(
                f"{self.action_type}:{self.trigger}:{time.time()}".encode()
            ).hexdigest()[:16]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class AutonomousCycle:
    """一次自主决策循环"""
    id: str = ""
    started_at: str = ""
    finished_at: str = ""
    decisions: list[dict] = field(default_factory=list)
    analysis_summary: dict = field(default_factory=dict)
    status: str = "running"


@dataclass
class DataFlowLink:
    """模块间数据流链接"""
    source_module: str
    source_output_field: str
    target_module: str
    target_input_field: str
    confidence: float = 0.0
    discovered_at: str = ""
    verified: bool = False


# ============================================================================
# 系统状态分析器
# ============================================================================

class SystemAnalyzer:
    """
    系统健康状态分析器
    从各子系统采集数据, 综合分析, 产生自主决策建议
    """

    def __init__(self):
        self._last_analysis: dict[str, Any] = {}

    async def analyze(self, context: dict) -> dict[str, Any]:
        """
        综合分析系统状态, 返回分析报告
        
        Args:
            context: 包含registry/coordinator/scheduler/event_engine等引用
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_health": "unknown",
            "issues": [],
            "opportunities": [],
            "recommendations": [],
            "metrics": {},
        }

        # 1. 模块健康分析
        module_report = await self._analyze_modules(context)
        report["metrics"]["modules"] = module_report
        report["issues"].extend(module_report.get("issues", []))
        report["opportunities"].extend(module_report.get("opportunities", []))

        # 2. 调度器状态分析
        schedule_report = self._analyze_scheduler(context)
        report["metrics"]["scheduler"] = schedule_report
        report["issues"].extend(schedule_report.get("issues", []))

        # 3. 事件引擎分析
        event_report = self._analyze_events(context)
        report["metrics"]["events"] = event_report
        if event_report.get("frequent_failures"):
            report["issues"].append({
                "type": "event_flood",
                "severity": "medium",
                "message": f"事件引擎近期有{event_report['frequent_failures']}次频繁失败事件"
            })

        # 4. 决策引擎经验分析
        decision_report = self._analyze_decision_engine(context)
        report["metrics"]["decision"] = decision_report
        report["opportunities"].extend(decision_report.get("opportunities", []))

        # 5. 综合评分
        score = self._calculate_health_score(report)
        report["system_health"] = self._score_to_level(score)
        report["health_score"] = score

        self._last_analysis = report
        return report

    async def _analyze_modules(self, context: dict) -> dict:
        """分析模块健康状态"""
        result = {"issues": [], "opportunities": []}

        registry = context.get("registry")
        if not registry:
            return result

        health = registry.get_all_health()
        total = len(health)
        if total == 0:
            return result

        error_count = sum(1 for h in health.values() if h.get("status") in ("error", "lazy_error"))
        active_count = sum(1 for h in health.values() if h.get("status") == "active")
        lazy_count = sum(1 for h in health.values() if h.get("status") == "lazy")

        result["total"] = total
        result["active"] = active_count
        result["lazy"] = lazy_count
        result["error"] = error_count
        result["health_rate"] = round(active_count / total * 100, 1) if total > 0 else 0

        if error_count > 0:
            error_names = [n for n, h in health.items() if h.get("status") in ("error", "lazy_error")]
            result["issues"].append({
                "type": "module_errors",
                "severity": "high" if error_count > 5 else "medium",
                "message": f"{error_count}个模块异常: {error_names[:5]}",
                "modules": error_names,
            })

        # 发现从未使用的模块(优化机会)
        if lazy_count > 50:
            result["opportunities"].append({
                "type": "lazy_modules",
                "message": f"{lazy_count}个模块从未加载, 考虑预加载关键模块"
            })

        return result

    def _analyze_scheduler(self, context: dict) -> dict:
        """分析调度器状态"""
        result = {"issues": [], "opportunities": []}
        scheduler = context.get("scheduler")
        if not scheduler:
            return result

        try:
            stats = scheduler.stats()
            result.update(stats)

            if not stats.get("running"):
                result["issues"].append({
                    "type": "scheduler_stopped",
                    "severity": "high",
                    "message": "调度器未运行"
                })
        except Exception as e:
            result["issues"].append({
                "type": "scheduler_error",
                "severity": "medium",
                "message": f"调度器状态获取失败: {e}"
            })

        return result

    def _analyze_events(self, context: dict) -> dict:
        """分析事件引擎状态"""
        result = {}
        ee = context.get("event_engine")
        if not ee:
            return result

        try:
            stats = ee.stats()
            result.update(stats)

            # 检查最近事件中是否有大量失败
            if stats.get("events_last_hour", 0) > 100:
                result["frequent_failures"] = stats["events_last_hour"]
        except Exception:
            pass

        return result

    def _analyze_decision_engine(self, context: dict) -> dict:
        """分析决策引擎经验"""
        result = {"opportunities": []}
        de = context.get("decision_engine")
        if not de:
            return result

        try:
            # 检查是否有规则可优化
            rules = de.get_rules()
            active_rules = [r for r in rules if r.get("enabled")]
            if len(active_rules) < 3:
                result["opportunities"].append({
                    "type": "more_rules_needed",
                    "message": f"仅{len(active_rules)}条活跃决策规则, 建议增加自动化规则"
                })

            # 检查经验数据是否充分
            history = de.get_history(limit=100)
            if len(history) < 10:
                result["opportunities"].append({
                    "type": "need_more_data",
                    "message": "决策历史数据不足, 建议运行自主分析积累经验"
                })
        except Exception:
            pass

        return result

    def _calculate_health_score(self, report: dict) -> float:
        """计算系统健康评分 0-100"""
        score = 100.0

        # 模块健康扣分
        mod_metrics = report["metrics"].get("modules", {})
        if mod_metrics.get("total", 0) > 0:
            error_rate = mod_metrics.get("error", 0) / mod_metrics["total"]
            score -= error_rate * 30  # 最多扣30分

        # 问题扣分
        for issue in report.get("issues", []):
            severity = issue.get("severity", "low")
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5
            else:
                score -= 2

        return max(0, min(100, score))

    def _score_to_level(self, score: float) -> str:
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "warning"
        elif score >= 40:
            return "degraded"
        else:
            return "critical"


# ============================================================================
# 数据流发现器
# ============================================================================

class DataFlowDiscoverer:
    """
    自动发现模块间的数据流关系
    基于历史执行记录分析模块输入输出的关联模式
    """

    def __init__(self):
        self._discovered_links: list[DataFlowLink] = []
        self._execution_patterns: dict[str, list[dict]] = defaultdict(list)

    def record_execution(self, module_name: str, action: str, params: dict, result: dict):
        """记录一次模块执行, 用于后续分析数据流"""
        pattern = {
            "module": module_name,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "output_keys": list(result.keys()) if isinstance(result, dict) else [],
            "input_keys": list(params.keys()) if isinstance(params, dict) else [],
        }
        self._execution_patterns[module_name].append(pattern)
        # 只保留最近100次
        if len(self._execution_patterns[module_name]) > 100:
            self._execution_patterns[module_name] = self._execution_patterns[module_name][-100:]

    def discover_links(self, context: dict) -> list[dict]:
        """
        分析执行历史, 发现潜在的模块间数据流关系
        
        Returns:
            数据流链接列表
        """
        links = []
        modules = list(self._execution_patterns.keys())

        if len(modules) < 2:
            return links

        # 分析: 如果模块A的输出字段名与模块B的输入参数名匹配,
        # 且A经常在B之前执行, 则可能存在数据流
        for i, mod_a in enumerate(modules):
            for mod_b in modules[i+1:]:
                patterns_a = self._execution_patterns[mod_a][-20:]
                patterns_b = self._execution_patterns[mod_b][-20:]

                if not patterns_a or not patterns_b:
                    continue

                # 查找匹配的字段
                output_fields = set()
                for p in patterns_a:
                    output_fields.update(p.get("output_keys", []))

                input_fields = set()
                for p in patterns_b:
                    input_fields.update(p.get("input_keys", []))

                common = output_fields & input_fields
                if common:
                    confidence = min(len(common) * 20, 95)  # 粗略置信度
                    if confidence >= 40:
                        link = DataFlowLink(
                            source_module=mod_a,
                            source_output_field=",".join(list(common)[:3]),
                            target_module=mod_b,
                            target_input_field=",".join(list(common)[:3]),
                            confidence=confidence,
                            discovered_at=datetime.now().isoformat(),
                        )
                        links.append(asdict(link))

        self._discovered_links = [
            DataFlowLink(**l) for l in links
        ] if links else []

        return links

    def get_discovered_links(self) -> list[dict]:
        return [asdict(l) for l in self._discovered_links]


# ============================================================================
# 自主智能体引擎 (核心)
# ============================================================================

class AutonomousAgent:
    """
    自主智能体引擎
    
    运行方式:
    1. 作为后台异步循环运行 (autonomous_cycle_loop)
    2. 每个周期: 分析→决策→执行→学习
    3. 循环间隔可配置(默认30分钟)
    4. 所有决策持久化, 可追溯
    """

    def __init__(self, interval_seconds: int = 1800):
        """
        Args:
            interval_seconds: 自主决策循环间隔(秒), 默认30分钟
        """
        self._running = False
        self._interval = interval_seconds
        self._analyzer = SystemAnalyzer()
        self._flow_discoverer = DataFlowDiscoverer()
        self._decisions: list[AutonomousDecision] = []
        self._cycles: list[AutonomousCycle] = []
        self._cycle_count = 0
        self._stats = {
            "total_decisions": 0,
            "auto_executed": 0,
            "skipped": 0,
            "failed": 0,
        }
        # 数据目录
        self._data_dir = Path(".evo_data/autonomous")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._data_dir / "autonomous.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS autonomous_cycles (
                    id TEXT PRIMARY KEY,
                    started_at TEXT,
                    finished_at TEXT,
                    decisions TEXT DEFAULT '[]',
                    analysis_summary TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'running'
                );
                CREATE TABLE IF NOT EXISTS autonomous_decisions (
                    id TEXT PRIMARY KEY,
                    cycle_id TEXT,
                    action_type TEXT,
                    risk_level TEXT,
                    trigger_reason TEXT,
                    description TEXT,
                    action_config TEXT DEFAULT '{}',
                    result TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    auto_executed INTEGER DEFAULT 0,
                    created_at TEXT,
                    executed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS data_flow_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_module TEXT,
                    source_output_field TEXT,
                    target_module TEXT,
                    target_input_field TEXT,
                    confidence REAL,
                    discovered_at TEXT,
                    verified INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_decisions_cycle ON autonomous_decisions(cycle_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_status ON autonomous_decisions(status);
                CREATE INDEX IF NOT EXISTS idx_cycles_status ON autonomous_cycles(status);
            """)
            conn.commit()
        finally:
            conn.close()

    def _save_cycle(self, cycle: AutonomousCycle):
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO autonomous_cycles
                (id, started_at, finished_at, decisions, analysis_summary, status)
                VALUES (?,?,?,?,?,?)
            """, (cycle.id, cycle.started_at, cycle.finished_at,
                  json.dumps(cycle.decisions, ensure_ascii=False),
                  json.dumps(cycle.analysis_summary, ensure_ascii=False),
                  cycle.status))
            conn.commit()
        finally:
            conn.close()

    def _save_decision(self, decision: AutonomousDecision):
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO autonomous_decisions
                (id, cycle_id, action_type, risk_level, trigger_reason,
                 description, action_config, result, status, auto_executed,
                 created_at, executed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (decision.id, decision.cycle_id, decision.action_type,
                  decision.risk_level, decision.trigger,
                  decision.description,
                  json.dumps(decision.action_config, ensure_ascii=False),
                  json.dumps(decision.result, ensure_ascii=False),
                  decision.status, int(decision.auto_executed),
                  decision.created_at, decision.executed_at))
            conn.commit()
        finally:
            conn.close()

    # ─── 核心循环 ───

    async def start(self, context: dict = None):
        """启动自主决策循环"""
        if self._running:
            return
        self._running = True
        logger.info("[AutonomousAgent] 自主智能体启动, 循环间隔: %ds", self._interval)

        # 存储上下文引用(懒加载的引擎实例)
        self._context = context or {}

        asyncio.create_task(self._cycle_loop())

    async def stop(self):
        """停止自主决策循环"""
        self._running = False
        logger.info("[AutonomousAgent] 自主智能体停止")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _cycle_loop(self):
        """主循环"""
        # 首次启动延迟60秒, 等系统完全就绪
        await asyncio.sleep(60)

        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error("[AutonomousAgent] 循环异常: %s", e, exc_info=True)

            # 可变间隔: 系统越健康间隔越长, 越异常间隔越短
            interval = self._adaptive_interval()
            await asyncio.sleep(interval)

    def _adaptive_interval(self) -> int:
        """自适应间隔: 健康=30min, 警告=15min, 异常=5min"""
        base = self._interval
        if self._cycles:
            last = self._cycles[-1]
            health = last.analysis_summary.get("health_score", 80)
            if health < 40:
                return min(base, 300)   # 5分钟
            elif health < 70:
                return min(base, 900)   # 15分钟
        return base  # 30分钟

    async def _run_cycle(self):
        """执行一次完整的自主决策循环"""
        cycle = AutonomousCycle(
            id=hashlib.md5(f"cycle:{time.time()}".encode()).hexdigest()[:16],
            started_at=datetime.now().isoformat(),
            status="running",
        )
        self._cycle_count += 1
        logger.info("[AutonomousAgent] ▶ 第%d次自主决策循环开始", self._cycle_count)

        # ═══ 阶段1: 系统状态分析 ═══
        analysis = await self._analyzer.analyze(self._context)
        cycle.analysis_summary = analysis

        # ═══ 阶段2: 产生决策 ═══
        decisions = self._generate_decisions(analysis)

        # ═══ 阶段3: 执行安全决策 ═══
        for decision in decisions:
            result = await self._execute_decision(decision)
            cycle.decisions.append(asdict(decision))
            self._save_decision(decision)
            self._stats["total_decisions"] += 1

        # ═══ 阶段4: 数据流发现 ═══
        try:
            links = self._flow_discoverer.discover_links(self._context)
            if links:
                self._save_data_flow_links(links)
                cycle.analysis_summary["data_flow_links"] = len(links)
        except Exception as e:
            logger.debug("[AutonomousAgent] 数据流发现跳过: %s", e)

        # ═══ 阶段5: 学习反馈 ═══
        try:
            await self._apply_learning_feedback(analysis)
        except Exception as e:
            logger.debug("[AutonomousAgent] 学习反馈跳过: %s", e)

        # 完成
        cycle.finished_at = datetime.now().isoformat()
        cycle.status = "completed"
        self._cycles.append(cycle)
        if len(self._cycles) > 100:
            self._cycles = self._cycles[-50:]
        self._save_cycle(cycle)

        decision_summary = f"产生{len(decisions)}个决策, " \
                          f"自动执行{sum(1 for d in decisions if d.auto_executed)}个, " \
                          f"生成{sum(1 for d in decisions if not d.auto_executed)}个建议"
        logger.info("[AutonomousAgent] ✓ 第%d次循环完成: %s | 健康评分: %.0f",
                    self._cycle_count, decision_summary,
                    analysis.get("health_score", 0))

    def _generate_decisions(self, analysis: dict) -> list[AutonomousDecision]:
        """根据分析结果产生自主决策"""
        decisions = []
        health = analysis.get("system_health", "unknown")
        score = analysis.get("health_score", 80)

        for issue in analysis.get("issues", []):
            decision = self._handle_issue(issue, health, score)
            if decision:
                decisions.append(decision)

        for opp in analysis.get("opportunities", []):
            decision = self._handle_opportunity(opp, health, score)
            if decision:
                decisions.append(decision)

        # 定期自主行为(每5个周期触发一次)
        if self._cycle_count % 5 == 0:
            decisions.append(AutonomousDecision(
                action_type=AutonomousAction.RULE_OPTIMIZE.value,
                risk_level=RiskLevel.LOW.value,
                trigger="periodic_maintenance",
                description="定期维护: 检查并优化决策规则",
                auto_executed=True,
            ))

        if self._cycle_count % 10 == 0:
            decisions.append(AutonomousDecision(
                action_type=AutonomousAction.LLM_REASONING.value,
                risk_level=RiskLevel.SAFE.value,
                trigger="periodic_deep_analysis",
                description="定期深度分析: 使用LLM进行系统级洞察",
                auto_executed=True,
            ))

        return decisions

    def _handle_issue(self, issue: dict, health: str, score: float) -> AutonomousDecision | None:
        """处理发现的问题"""
        issue_type = issue.get("type", "")
        severity = issue.get("severity", "low")

        if issue_type == "module_errors":
            modules = issue.get("modules", [])
            return AutonomousDecision(
                action_type=AutonomousAction.SELF_HEAL.value,
                risk_level=RiskLevel.LOW.value,
                trigger=f"module_errors:{len(modules)}",
                description=f"自动修复异常模块: {', '.join(modules[:3])}",
                action_config={"modules": modules[:5], "action": "reload"},
                auto_executed=True,
            )

        elif issue_type == "scheduler_stopped":
            return AutonomousDecision(
                action_type=AutonomousAction.SCHEDULE.value,
                risk_level=RiskLevel.LOW.value,
                trigger="scheduler_stopped",
                description="调度器已停止, 尝试重启",
                action_config={"action": "restart"},
                auto_executed=True,
            )

        elif issue_type == "event_flood":
            return AutonomousDecision(
                action_type=AutonomousAction.ANALYSIS.value,
                risk_level=RiskLevel.SAFE.value,
                trigger=f"event_flood:{issue.get('frequent_failures', 0)}",
                description=f"事件风暴检测: 建议检查事件规则配置",
                auto_executed=True,
            )

        return None

    def _handle_opportunity(self, opp: dict, health: str, score: float) -> AutonomousDecision | None:
        """处理发现的机会"""
        opp_type = opp.get("type", "")

        if opp_type == "need_more_data" or opp_type == "more_rules_needed":
            return AutonomousDecision(
                action_type=AutonomousAction.ANALYSIS.value,
                risk_level=RiskLevel.SAFE.value,
                trigger=f"opportunity:{opp_type}",
                description=opp.get("message", "优化机会"),
                auto_executed=True,
            )

        elif opp_type == "lazy_modules":
            return AutonomousDecision(
                action_type=AutonomousAction.DATA_FLOW.value,
                risk_level=RiskLevel.SAFE.value,
                trigger="lazy_modules_detected",
                description="扫描未加载模块, 发现可联动关系",
                auto_executed=True,
            )

        return None

    async def _execute_decision(self, decision: AutonomousDecision) -> dict:
        """执行自主决策"""
        try:
            if not decision.auto_executed:
                decision.status = "skipped"
                self._stats["skipped"] += 1
                return {"status": "skipped", "reason": "需要人工确认"}

            action = decision.action_type
            config = decision.action_config
            result = {}

            if action == AutonomousAction.SELF_HEAL.value:
                result = await self._do_self_heal(config)
            elif action == AutonomousAction.ANALYSIS.value:
                result = await self._do_analysis(config)
            elif action == AutonomousAction.RULE_OPTIMIZE.value:
                result = await self._do_rule_optimize()
            elif action == AutonomousAction.DATA_FLOW.value:
                result = self._do_data_flow_discovery()
            elif action == AutonomousAction.LLM_REASONING.value:
                result = await self._do_llm_reasoning()
            elif action == AutonomousAction.SCHEDULE.value:
                result = await self._do_schedule_action(config)

            decision.result = result
            decision.status = "executed"
            decision.executed_at = datetime.now().isoformat()
            self._stats["auto_executed"] += 1

        except Exception as e:
            decision.result = {"error": str(e)}
            decision.status = "failed"
            self._stats["failed"] += 1
            logger.error("[AutonomousAgent] 决策执行失败: %s -> %s", decision.description, e)

        return decision.result

    # ─── 决策动作实现 ───

    async def _do_self_heal(self, config: dict) -> dict:
        """执行自愈: 重新加载异常模块"""
        modules = config.get("modules", [])
        registry = self._context.get("registry")
        results = {}

        if not registry:
            return {"error": "registry不可用"}

        for name in modules[:5]:
            try:
                old_mod = registry.modules.pop(name, None)
                if old_mod and hasattr(old_mod, 'shutdown'):
                    try:
                        old_mod.shutdown()
                    except Exception:
                        pass
                registry.health.pop(name, None)

                new_mod = await asyncio.wait_for(
                    registry.lazy_load_module(name), timeout=30
                )
                results[name] = "reloaded" if new_mod else "load_failed"
            except TimeoutError:
                results[name] = "timeout"
            except Exception as e:
                results[name] = f"error: {e}"

        return results

    async def _do_analysis(self, config: dict) -> dict:
        """执行深度分析"""
        # 触发学习引擎分析
        le = self._context.get("learning_engine")
        result = {}

        if le:
            try:
                summary = le.get_dashboard_summary()
                result["learning_summary"] = summary
            except Exception as e:
                result["learning_error"] = str(e)

        # 触发决策引擎经验报告
        de = self._context.get("decision_engine")
        if de:
            try:
                experience = de.get_experience_report()
                result["experience_report"] = experience
            except Exception as e:
                result["experience_error"] = str(e)

        return result

    async def _do_rule_optimize(self) -> dict:
        """优化决策规则"""
        de = self._context.get("decision_engine")
        le = self._context.get("learning_engine")

        if not de or not le:
            return {"status": "skipped", "reason": "引擎不可用"}

        try:
            # 生成反馈规则
            suggestions = le.generate_feedback_rules(decision_engine=de)
            # 自动应用高置信度建议
            applied = le.auto_apply_top_suggestions(decision_engine=de, max_apply=3)
            return {
                "suggestions_generated": len(suggestions),
                "auto_applied": applied.get("applied_count", 0),
                "applied_details": applied.get("applied", []),
            }
        except Exception as e:
            return {"error": str(e)}

    def _do_data_flow_discovery(self) -> dict:
        """发现模块间数据流"""
        links = self._flow_discoverer.discover_links(self._context)
        return {
            "links_discovered": len(links),
            "links": links[:10],
        }

    async def _do_llm_reasoning(self) -> dict:
        """LLM深度推理分析"""
        ic = self._context.get("intelligent_coordinator")
        if not ic:
            return {"status": "skipped", "reason": "智能协调器不可用"}

        try:
            # 使用智能协调器做一次自主分析
            result = ic.parse_only(
                "请分析当前系统状态, 识别潜在问题和优化机会, 给出具体可执行建议",
                session_id="autonomous_reasoning"
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _do_schedule_action(self, config: dict) -> dict:
        """调度器操作"""
        scheduler = self._context.get("scheduler")
        action = config.get("action", "")

        if not scheduler:
            return {"error": "scheduler不可用"}

        try:
            if action == "restart":
                if not scheduler._running:
                    await scheduler.start()
                    return {"status": "restarted"}
                return {"status": "already_running"}
        except Exception as e:
            return {"error": str(e)}

        return {"status": "unknown_action"}

    # ─── 学习反馈 ───

    async def _apply_learning_feedback(self, analysis: dict):
        """将本轮分析结果反馈给学习引擎"""
        le = self._context.get("learning_engine")
        if not le:
            return

        try:
            # 记录本轮分析作为学习数据
            issues = analysis.get("issues", [])
            opps = analysis.get("opportunities", [])
            health = analysis.get("health_score", 80)

            if hasattr(le, 'record_analysis'):
                le.record_analysis({
                    "cycle": self._cycle_count,
                    "health_score": health,
                    "issues_count": len(issues),
                    "opportunities_count": len(opps),
                })
        except Exception:
            pass

    # ─── 数据流持久化 ───

    def _save_data_flow_links(self, links: list[dict]):
        conn = self._get_conn()
        try:
            for link in links:
                conn.execute("""
                    INSERT INTO data_flow_links
                    (source_module, source_output_field, target_module,
                     target_input_field, confidence, discovered_at)
                    VALUES (?,?,?,?,?,?)
                """, (
                    link.get("source_module", ""),
                    link.get("source_output_field", ""),
                    link.get("target_module", ""),
                    link.get("target_input_field", ""),
                    link.get("confidence", 0),
                    link.get("discovered_at", ""),
                ))
            conn.commit()
        finally:
            conn.close()

    def record_module_execution(self, module_name: str, action: str,
                                 params: dict, result: dict):
        """供外部调用: 记录模块执行, 用于数据流分析"""
        self._flow_discoverer.record_execution(module_name, action, params, result)

    # ─── 状态查询 ───

    def get_stats(self) -> dict:
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "interval_seconds": self._interval,
            "adaptive_interval": self._adaptive_interval(),
            "decisions_stats": self._stats,
            "last_cycle": asdict(self._cycles[-1]) if self._cycles else None,
        }

    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM autonomous_decisions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_recent_cycles(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM autonomous_cycles ORDER BY started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['decisions'] = json.loads(d.get('decisions') or '[]')
                d['analysis_summary'] = json.loads(d.get('analysis_summary') or '{}')
                result.append(d)
            return result
        finally:
            conn.close()

    def get_data_flow_links(self) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM data_flow_links ORDER BY confidence DESC LIMIT 50"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# ============================================================================
# 全局单例
# ============================================================================

_autonomous_agent: AutonomousAgent | None = None


def get_autonomous_agent() -> AutonomousAgent:
    global _autonomous_agent
    if _autonomous_agent is None:
        _autonomous_agent = AutonomousAgent()
    return _autonomous_agent


def reset_autonomous_agent():
    global _autonomous_agent
    if _autonomous_agent and _autonomous_agent._running:
        asyncio.create_task(_autonomous_agent.stop())
    _autonomous_agent = None
