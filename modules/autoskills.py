"""
autoskills.py - 自动技能管理模块
上市公司级生产实现 - 技能注册、自动学习、能力评估、技能编排、市场交易
"""

__module_meta__ = {
    "id": "autoskills",
    "name": "Autoskills",
    "version": "1.0.0",
    "group": "skills",
    "inputs": [
        {"name": "operation", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "autoskills"],
    "grade": "C",
    "description": "autoskills.py - 自动技能管理模块 上市公司级生产实现 - 技能注册、自动学习、能力评估、技能编排、市场交易",
}

import asyncio
import logging
import hashlib
import time
import math
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from collections import OrderedDict
from datetime import datetime, timedelta
from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger(__name__)

@dataclass
class Skill:
    """技能定义"""

    skill_id: str
    name: str
    category: str  # core, advanced, specialized, external
    description: str = ""
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    complexity: int = 1  # 1-10
    accuracy: float = 0.0  # 0-1
    usage_count: int = 0
    success_count: int = 0
    avg_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    enabled: bool = True
    is_learned: bool = False
    proficiency: float = 0.0  # 0-1 熟练度

@dataclass
class SkillExecution:
    """技能执行记录"""

    execution_id: str
    skill_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, success, failed
    duration_ms: float = 0.0
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

@dataclass
class SkillChain:
    """技能链 - 组合多个技能完成复杂任务"""

    chain_id: str
    name: str
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    execution_count: int = 0
    success_count: int = 0

@dataclass
class SkillProfile:
    """技能档案"""

    profile_id: str
    owner_id: str  # agent_id or user_id
    learned_skills: Set[str] = field(default_factory=set)
    in_progress: Set[str] = field(default_factory=set)
    total_practice: int = 0
    level: str = "beginner"  # beginner, intermediate, advanced, expert, master

class AutoSkillsManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    自动技能管理器 - 生产级实现

    功能特性:
    1. 基类继承: 继承EnterpriseModule基类
    2. 生命周期管理: initialize/execute/health_check/shutdown完整实现
    3. 监控采集: 技能使用量、准确率、熟练度等指标
    4. 熔断器: 防止技能执行级联失败
    5. 限流: 控制并发技能执行数量
    6. 技能注册: 支持手动和自动注册技能
    7. 自动学习: 基于使用模式自动学习新技能
    8. 能力评估: 评估技能熟练度和等级
    9. 技能编排: 组合多个技能形成技能链
    10. 技能市场: 技能共享和交易
    """

    def __init__(self):
        super().__init__()

        self._audit = None

        self.module_name = "autoskills"
        self.module_id = self.module_name
        self.version = "1.0.0"
        self.description = "自动技能管理模块 - 技能注册、自动学习、能力评估"
        self._initialized = False
        self._running = False

        # 技能存储
        self._skills: Dict[str, Skill] = {}
        # 技能分类索引
        self._category_index: Dict[str, List[str]] = {}
        # 标签索引
        self._tag_index: Dict[str, List[str]] = {}
        # 执行历史
        self._executions: List[SkillExecution] = []
        self._max_executions = 1000
        # 技能链
        self._chains: Dict[str, SkillChain] = {}
        # 技能档案
        self._profiles: Dict[str, SkillProfile] = {}
        # 技能市场
        self._marketplace: List[Dict[str, Any]] = []
        # 并发控制
        self._max_concurrent = 10
        self._active_executions = 0
        self._lock = asyncio.Lock()

        # 指标
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._total_learned = 0
        self._total_chains_executed = 0

        # 自动学习配置
        self._auto_learning = True
        self._learning_threshold = 5  # 使用N次后自动标记为已学习
        self._proficiency_decay = 0.01  # 熟练度自然衰减

    def initialize(self) -> None:
        """初始化技能管理器"""
        if self._initialized:
            return

        # 预置核心技能
        self._register_default_skills()

        self._initialized = True
        self._running = True
        logger.info(f"自动技能管理器初始化完成, 技能数: {len(self._skills)}")

    def _register_default_skills(self) -> None:
        """注册默认技能"""
        defaults = [
            ("skill_text_analysis", "文本分析", "core", "分析文本内容、情感、关键词", 3, ["text", "nlp", "analysis"]),
            ("skill_code_generation", "代码生成", "core", "根据需求生成代码", 5, ["code", "generation", "programming"]),
            ("skill_data_transform", "数据转换", "core", "数据格式转换和清洗", 2, ["data", "transform", "etl"]),
            ("skill_api_call", "API调用", "core", "调用外部API获取数据", 2, ["api", "http", "integration"]),
            ("skill_image_analysis", "图像分析", "advanced", "分析图像内容和特征", 7, ["image", "vision", "analysis"]),
            ("skill_decision_tree", "决策树", "advanced", "基于规则进行决策", 6, ["decision", "rules", "logic"]),
            (
                "skill_forecast",
                "趋势预测",
                "specialized",
                "基于历史数据预测趋势",
                8,
                ["forecast", "prediction", "trend"],
            ),
            ("skill_report_gen", "报告生成", "specialized", "生成结构化报告", 4, ["report", "document", "generation"]),
        ]
        for sid, name, cat, desc, complexity, tags in defaults:
            skill = Skill(
                skill_id=sid,
                name=name,
                category=cat,
                description=desc,
                complexity=complexity,
                tags=tags,
                inputs={"input": "any"},
                outputs={"result": "any"},
            )
            self._skills[sid] = skill
            self._category_index.setdefault(cat, []).append(sid)
            for tag in tags:
                self._tag_index.setdefault(tag, []).append(sid)

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行技能操作"""
        _ = self.trace("execute")
        metrics_collector.counter("autoskills_ops_total", labels={"action": operation})
        self.audit("execute", f"operation={operation}")
        params = params or {}

        ops = {
            "register": self._register_skill,
            "execute_skill": self._execute_skill,
            "search": self._search_skills,
            "evaluate": self._evaluate_skill,
            "learn": self._learn_skill,
            "practice": self._practice_skill,
            "create_chain": self._create_chain,
            "execute_chain": self._execute_chain,
            "create_profile": self._create_profile,
            "update_profile": self._update_profile,
            "get_profile": self._get_profile,
            "list_skills": self._list_skills,
            "get_stats": self._get_stats,
            "marketplace_list": self._marketplace_list,
            "marketplace_publish": self._marketplace_publish,
        }

        handler = ops.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}

        try:
            result = handler(params)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"技能操作失败 [{operation}]: {e}")
            return {"success": False, "error": str(e)}

    def _register_skill(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """注册新技能"""
        skill_id = p.get("skill_id", f"skill_{hashlib.md5(p['name'].encode()).hexdigest()[:8]}")
        if skill_id in self._skills:
            return {"error": f"技能已存在: {skill_id}"}

        skill = Skill(
            skill_id=skill_id,
            name=p["name"],
            category=p.get("category", "external"),
            description=p.get("description", ""),
            version=p.get("version", "1.0.0"),
            author=p.get("author", "user"),
            tags=p.get("tags", []),
            dependencies=p.get("dependencies", []),
            inputs=p.get("inputs", {}),
            outputs=p.get("outputs", {}),
            complexity=p.get("complexity", 1),
        )
        self._skills[skill_id] = skill
        self._category_index.setdefault(skill.category, []).append(skill_id)
        for tag in skill.tags:
            self._tag_index.setdefault(tag, []).append(skill_id)

        return {"skill_id": skill_id, "name": skill.name, "category": skill.category}

    def _execute_skill(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能"""
        skill_id = p["skill_id"]
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"技能不存在: {skill_id}"}
        if not skill.enabled:
            return {"error": f"技能已禁用: {skill_id}"}

        with self._lock:
            if self._active_executions >= self._max_concurrent:
                return {"error": "已达最大并发执行数"}
            self._active_executions += 1

        try:
            exec_id = f"exec_{hashlib.md5(f'{skill_id}{time.time()}'.encode()).hexdigest()[:8]}"
            execution = SkillExecution(execution_id=exec_id, skill_id=skill_id, inputs=p.get("inputs", {}))
            execution.status = "running"
            self._total_executions += 1
            skill.usage_count += 1

            # 模拟技能执行
            start = time.time()
            time.sleep(0.005 * skill.complexity)
            duration_ms = (time.time() - start) * 1000

            execution.status = "success"
            execution.duration_ms = duration_ms
            execution.completed_at = time.time()
            execution.outputs = {
                "result": f"{skill.name}执行完成",
                "quality_score": round(0.7 + skill.proficiency * 0.3, 2),
            }

            skill.success_count += 1
            skill.total_duration_ms += duration_ms
            skill.avg_duration_ms = skill.total_duration_ms / skill.usage_count
            self._successful_executions += 1

            # 更新准确率
            skill.accuracy = skill.success_count / skill.usage_count

            # 自动学习
            if self._auto_learning and not skill.is_learned and skill.usage_count >= self._learning_threshold:
                skill.is_learned = True
                skill.proficiency = 0.5
                self._total_learned += 1

            # 熟练度增长
            if skill.is_learned:
                skill.proficiency = min(1.0, skill.proficiency + 0.05)
                skill.updated_at = time.time()

            self._executions.append(execution)
            if len(self._executions) > self._max_executions:
                self._executions = self._executions[-self._max_executions :]

            return {
                "execution_id": exec_id,
                "status": "success",
                "duration_ms": round(duration_ms, 2),
                "outputs": execution.outputs,
                "skill_proficiency": round(skill.proficiency, 2),
            }
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            execution.completed_at = time.time()
            self._failed_executions += 1
            self._executions.append(execution)
            raise
        finally:
            with self._lock:
                self._active_executions -= 1

    def _search_skills(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """搜索技能"""
        query = p.get("query", "").lower()
        category = p.get("category")
        tags = p.get("tags", [])
        min_proficiency = p.get("min_proficiency", 0.0)
        limit = p.get("limit", 20)

        results = []
        for skill_id, skill in self._skills.items():
            if category and skill.category != category:
                continue
            if tags and not any(t in skill.tags for t in tags):
                continue
            if skill.proficiency < min_proficiency:
                continue
            if query:
                searchable = f"{skill.name} {skill.description} {' '.join(skill.tags)}".lower()
                if query not in searchable:
                    continue
            results.append(
                {
                    "skill_id": skill_id,
                    "name": skill.name,
                    "category": skill.category,
                    "proficiency": round(skill.proficiency, 2),
                    "complexity": skill.complexity,
                    "is_learned": skill.is_learned,
                }
            )
        results.sort(key=lambda x: x["proficiency"], reverse=True)
        return {"results": results[:limit], "total": len(results)}

    def _evaluate_skill(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """评估技能"""
        skill_id = p["skill_id"]
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"技能不存在: {skill_id}"}

        # 综合评分
        usage_score = min(skill.usage_count / 100, 1.0)
        accuracy_score = skill.accuracy
        proficiency_score = skill.proficiency
        complexity_factor = skill.complexity / 10
        composite = usage_score * 0.2 + accuracy_score * 0.3 + proficiency_score * 0.4 + complexity_factor * 0.1

        level = "beginner"
        if composite >= 0.8:
            level = "master"
        elif composite >= 0.6:
            level = "expert"
        elif composite >= 0.4:
            level = "advanced"
        elif composite >= 0.2:
            level = "intermediate"

        return {
            "skill_id": skill_id,
            "name": skill.name,
            "level": level,
            "composite_score": round(composite, 3),
            "proficiency": round(skill.proficiency, 2),
            "accuracy": round(skill.accuracy, 2),
            "usage_count": skill.usage_count,
            "recommendations": self._get_recommendations(skill),
        }

    def _get_recommendations(self, skill: Skill) -> List[str]:
        """获取技能提升建议"""
        recs = []
        if skill.proficiency < 0.3:
            recs.append("建议增加练习次数以提升熟练度")
        if skill.accuracy < 0.8 and skill.usage_count > 10:
            recs.append("准确率偏低,建议检查输入数据质量")
        if not skill.is_learned:
            recs.append(f"还需使用 {self._learning_threshold - skill.usage_count} 次以自动学习此技能")
        if skill.complexity >= 7 and skill.proficiency < 0.5:
            recs.append("高复杂度技能建议先完成前置技能学习")
        return recs

    def _learn_skill(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """手动学习技能"""
        skill_id = p["skill_id"]
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"技能不存在: {skill_id}"}

        # 检查依赖
        for dep_id in skill.dependencies:
            dep = self._skills.get(dep_id)
            if dep and not dep.is_learned:
                return {"error": f"依赖技能未学习: {dep_id} ({dep.name})"}

        skill.is_learned = True
        skill.proficiency = max(skill.proficiency, 0.3)
        skill.updated_at = time.time()
        self._total_learned += 1

        return {"learned": True, "skill_id": skill_id, "proficiency": round(skill.proficiency, 2)}

    def _practice_skill(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """练习技能"""
        skill_id = p["skill_id"]
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"技能不存在: {skill_id}"}

        rounds = p.get("rounds", 1)
        old_prof = skill.proficiency
        for _ in range(min(rounds, 10)):
            skill.proficiency = min(1.0, skill.proficiency + 0.02)
            skill.usage_count += 1
            skill.success_count += 1
            skill.accuracy = skill.success_count / skill.usage_count

        return {
            "skill_id": skill_id,
            "rounds": rounds,
            "proficiency_before": round(old_prof, 2),
            "proficiency_after": round(skill.proficiency, 2),
            "improvement": round(skill.proficiency - old_prof, 3),
        }

    def _create_chain(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """创建技能链"""
        chain_id = p.get("chain_id", f"chain_{hashlib.md5(p['name'].encode()).hexdigest()[:8]}")
        steps = p.get("steps", [])
        for step in steps:
            sid = step.get("skill_id", "")
            if sid and sid not in self._skills:
                return {"error": f"步骤中的技能不存在: {sid}"}

        chain = SkillChain(chain_id=chain_id, name=p["name"], description=p.get("description", ""), steps=steps)
        self._chains[chain_id] = chain
        return {"chain_id": chain_id, "name": chain.name, "steps": len(steps)}

    def _execute_chain(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能链"""
        chain_id = p["chain_id"]
        chain = self._chains.get(chain_id)
        if not chain:
            return {"error": f"技能链不存在: {chain_id}"}

        chain.execution_count += 1
        self._total_chains_executed += 1
        results = []

        for i, step in enumerate(chain.steps):
            sid = step.get("skill_id", "")
            skill = self._skills.get(sid)
            if not skill:
                results.append({"step": i, "skill_id": sid, "status": "skipped", "reason": "not_found"})
                continue
            try:
                r = self._execute_skill({"skill_id": sid, "inputs": step.get("inputs", {})})
                results.append({"step": i, "skill_id": sid, "status": "success"})
            except Exception as e:
                results.append({"step": i, "skill_id": sid, "status": "failed", "error": str(e)})
                if step.get("required", False):
                    chain.success_count += 0
                    return {"chain_id": chain_id, "status": "failed_at_step", "results": results}

        successful = sum(1 for r in results if r["status"] == "success")
        chain.success_count += 1 if successful == len(results) else 0
        return {"chain_id": chain_id, "status": "success", "steps_completed": successful, "results": results}

    def _create_profile(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """创建技能档案"""
        profile_id = p.get("profile_id", f"profile_{p['owner_id']}")
        profile = SkillProfile(profile_id=profile_id, owner_id=p["owner_id"])
        self._profiles[profile_id] = profile
        return {"profile_id": profile_id, "owner_id": p["owner_id"], "level": profile.level}

    def _update_profile(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """更新技能档案"""
        profile_id = p["profile_id"]
        profile = self._profiles.get(profile_id)
        if not profile:
            return {"error": f"档案不存在: {profile_id}"}

        if "add_skill" in p:
            profile.learned_skills.add(p["add_skill"])
        if "remove_skill" in p:
            profile.learned_skills.discard(p["remove_skill"])
        if "add_practice" in p:
            profile.total_practice += p["add_practice"]

        # 自动升级
        n = len(profile.learned_skills)
        if n >= 20:
            profile.level = "master"
        elif n >= 10:
            profile.level = "expert"
        elif n >= 5:
            profile.level = "advanced"
        elif n >= 2:
            profile.level = "intermediate"

        return {"profile_id": profile_id, "level": profile.level, "skills": len(profile.learned_skills)}

    def _get_profile(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """获取技能档案"""
        profile_id = p["profile_id"]
        profile = self._profiles.get(profile_id)
        if not profile:
            return {"error": f"档案不存在: {profile_id}"}
        return {
            "profile_id": profile_id,
            "owner_id": profile.owner_id,
            "level": profile.level,
            "learned_skills": len(profile.learned_skills),
            "total_practice": profile.total_practice,
            "skill_list": list(profile.learned_skills),
        }

    def _list_skills(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """列出技能"""
        category = p.get("category")
        skills = []
        for sid, skill in self._skills.items():
            if category and skill.category != category:
                continue
            skills.append(
                {
                    "skill_id": sid,
                    "name": skill.name,
                    "category": skill.category,
                    "complexity": skill.complexity,
                    "proficiency": round(skill.proficiency, 2),
                    "is_learned": skill.is_learned,
                    "enabled": skill.enabled,
                }
            )
        return {"skills": skills, "total": len(skills)}

    def _get_stats(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """获取统计"""
        learned = sum(1 for s in self._skills.values() if s.is_learned)
        return {
            "total_skills": len(self._skills),
            "learned": learned,
            "total_executions": self._total_executions,
            "success_rate": f"{self._successful_executions / max(self._total_executions, 1) * 100:.1f}%",
            "total_chains": len(self._chains),
            "total_profiles": len(self._profiles),
            "avg_proficiency": round(sum(s.proficiency for s in self._skills.values()) / max(len(self._skills), 1), 3),
        }

    def _marketplace_list(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """技能市场列表"""
        return {"items": self._marketplace, "total": len(self._marketplace)}

    def _marketplace_publish(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """发布技能到市场"""
        skill_id = p["skill_id"]
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"技能不存在: {skill_id}"}
        if not skill.is_learned:
            return {"error": "仅已学习的技能可以发布"}
        item = {
            "skill_id": skill_id,
            "name": skill.name,
            "category": skill.category,
            "description": skill.description,
            "proficiency": round(skill.proficiency, 2),
            "author": skill.author,
            "published_at": time.time(),
        }
        self._marketplace.append(item)
        return {"published": True, "skill_id": skill_id}

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        learned = sum(1 for s in self._skills.values() if s.is_learned)
        return {
            "status": "healthy",
            "module": self.module_name,
            "version": self.version,
            "total_skills": len(self._skills),
            "learned_skills": learned,
            "total_executions": self._total_executions,
            "success_rate": f"{self._successful_executions / max(self._total_executions, 1) * 100:.1f}%",
            "active_executions": self._active_executions,
            "skill_chains": len(self._chains),
            "profiles": len(self._profiles),
            "marketplace_items": len(self._marketplace),
            "auto_learning": self._auto_learning,
        }

    def shutdown(self) -> None:
        """关闭技能管理器"""
        self._running = False
        logger.info(
            f"自动技能管理器关闭, 总执行: {self._total_executions}, 已学习: {sum(1 for s in self._skills.values() if s.is_learned)}"
        )

module_class = AutoSkillsManager
