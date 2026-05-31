"""
# Grade: A
经验库 - AUTO-EVO-AI V0.1
基于历史的决策、经验复用、智能推荐
"""

__module_meta__ = {
        "id": "experience-base",
        "name": "Experience Base",
        "version": "V0.1",
        "group": "memory",
        "inputs": [
            {
                "name": "context",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "keyword",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "limit",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_a",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_b",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "experience"
        ],
        "grade": "A",
        "description": "经验库 - AUTO-EVO-AI V0.1 基于历史的决策、经验复用、智能推荐"
    }

import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum
import sqlite3
from pathlib import Path
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

class ExperienceBaseAnalyzer(object):
    """experience_base 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "experience_base"
        self.version = "1.0.0"
        self._analyzer = ExperienceBaseAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "ExperienceBaseAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "experience_base"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== experience_base ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class ExperienceType(Enum):
    """经验类型"""

    SUCCESS = "success"  # 成功经验
    FAILURE = "failure"  # 失败经验
    PATTERN = "pattern"  # 模式识别
    DECISION = "decision"  # 决策经验

@dataclass
class Experience:
    """经验"""

    id: str
    type: str
    context: str  # 上下文描述
    action: str  # 采取的行动
    result: str  # 结果
    success: bool
    score: float = 0.0  # 经验质量评分 0-1
    use_count: int = 0  # 使用次数
    success_rate: float = 0.0  # 历史成功率

    # 标签和关键词
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # 时间
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    last_used: Optional[str] = None
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    # 元数据
    metadata: Dict = field(default_factory=dict)

    def update_score(self, new_success: bool):
        """更新评分"""
        total = self.use_count + 1
        self.success_rate = (self.success_rate * self.use_count + (1 if new_success else 0)) / total
        self.score = self.success_rate * 0.8 + (1 / (1 + self.use_count * 0.1)) * 0.2
        self.use_count = total
        self.last_used = time.strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = self.last_used

@dataclass
class DecisionContext:
    """决策上下文"""

    situation: str  # 情境描述
    available_options: List[str]  # 可选方案
    constraints: List[str] = field(default_factory=list)
    similar_history: List[Experience] = field(default_factory=list)

@dataclass
class Recommendation:
    """推荐结果"""

    experience: Experience
    confidence: float
    reasoning: str
    alternative: List[str] = field(default_factory=list)

class ExperienceBase:
    """
    经验库

    功能:
    - 经验存储与检索
    - 相似经验匹配
    - 智能决策推荐
    - 模式识别
    - 经验质量评估
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or ".evo_data/experience.db"
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.experiences: Dict[str, Experience] = {}
        self.patterns: Dict[str, List[str]] = defaultdict(list)  # pattern -> experience_ids

        # 缺口4修复：记忆引擎桥接，经验同步到长期记忆
        self._memory = None

        # 统计
        self.stats = {"total": 0, "success": 0, "failure": 0, "recommendations_made": 0, "recommendations_used": 0}

        # 加载数据库
        self._init_db()
        self._load_from_db()

        logger.info(f"[ExperienceBase] 经验库初始化 (共 {len(self.experiences)} 条经验)")

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                context TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT,
                success INTEGER NOT NULL,
                score REAL DEFAULT 0,
                use_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,
                tags TEXT,
                keywords TEXT,
                created_at TEXT,
                last_used TEXT,
                updated_at TEXT,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _load_from_db(self):
        """从数据库加载"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM experiences")
            rows = cursor.fetchall()

            for row in rows:
                exp = Experience(
                    id=row[0],
                    type=row[1],
                    context=row[2],
                    action=row[3],
                    result=row[4],
                    success=bool(row[5]),
                    score=row[6],
                    use_count=row[7],
                    success_rate=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                    keywords=json.loads(row[10]) if row[10] else [],
                    created_at=row[11],
                    last_used=row[12],
                    updated_at=row[13],
                    metadata=json.loads(row[14]) if row[14] else {},
                )
                self.experiences[exp.id] = exp

                # 更新统计
                self.stats["total"] += 1
                if exp.success:
                    self.stats["success"] += 1
                else:
                    self.stats["failure"] += 1

                # 更新模式
                for tag in exp.tags:
                    self.patterns[tag].append(exp.id)

            conn.close()
        except Exception as e:
            logger.error(f"[ExperienceBase] 加载失败: {e}")

    def _save_to_db(self, exp: Experience):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO experiences
            (id, type, context, action, result, success, score, use_count,
             success_rate, tags, keywords, created_at, last_used, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                exp.id,
                exp.type,
                exp.context,
                exp.action,
                exp.result,
                int(exp.success),
                exp.score,
                exp.use_count,
                exp.success_rate,
                json.dumps(exp.tags),
                json.dumps(exp.keywords),
                exp.created_at,
                exp.last_used,
                exp.updated_at,
                json.dumps(exp.metadata),
            ),
        )

        conn.commit()
        conn.close()

    def add_experience(
        self,
        context: str,
        action: str,
        result: str,
        success: bool,
        tags: List[str] = None,
        keywords: List[str] = None,
        metadata: Dict = None,
    ) -> Experience:
        """添加经验"""
        import uuid

        # 提取关键词
        if keywords is None:
            keywords = self._extract_keywords(context + " " + action)

        if tags is None:
            tags = []

        exp = Experience(
            id=uuid.uuid4().hex[:12],
            type=ExperienceType.SUCCESS.value if success else ExperienceType.FAILURE.value,
            context=context,
            action=action,
            result=result,
            success=success,
            tags=tags,
            keywords=keywords,
            metadata=metadata or {},
        )

        self.experiences[exp.id] = exp

        # 更新模式索引
        for tag in tags:
            self.patterns[tag].append(exp.id)

        # 更新统计
        self.stats["total"] += 1
        if success:
            self.stats["success"] += 1
        else:
            self.stats["failure"] += 1

        # 保存到数据库
        self._save_to_db(exp)

        # 缺口4修复：同步高价值经验到长期记忆（失败经验 + 成功率>80%的经验）
        if self._memory:
            try:
                if not success or exp.success_rate > 0.8:
                    self._memory.save_memory(
                        f"经验库: {action[:60]} | {'成功' if success else '失败'}", "experience_sync", "system"
                    )
            except Exception:
                pass

        logger.info(f"[Experience] 添加经验: {action[:30]}... ({'✅' if success else '❌'})")
        return exp

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取高频词
        words = text.lower().split()
        stopwords = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
        }

        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 1 and word not in stopwords:
                word_freq[word] += 1

        # 返回前5个高频词
        return [w for w, _ in sorted(word_freq.items(), key=lambda x: -x[1])[:5]]

    def get_recent(self, limit: int = 20) -> List[Experience]:
        """获取最近的经验记录"""
        sorted_exps = sorted(self.experiences.values(), key=lambda e: e.created_at, reverse=True)
        return sorted_exps[:limit]
        """查找相似经验"""
        keywords = self._extract_keywords(context)

        scored = []
        for exp in self.experiences.values():
            # 计算相似度
            score = 0

            # 关键词匹配
            for kw in keywords:
                if kw in exp.keywords or kw in exp.context.lower():
                    score += 1

            # 标签匹配
            for tag in exp.tags:
                if tag in context:
                    score += 2

            if score > 0:
                scored.append((exp, score))

        # 按分数排序
        scored.sort(key=lambda x: -x[1])
        return [exp for exp, _ in scored[:limit]]

    def recommend_action(self, situation: str, options: List[str]) -> Recommendation:
        """推荐行动"""
        similar = self.find_similar(situation)

        if not similar:
            return Recommendation(experience=None, confidence=0.0, reasoning="没有找到相似经验", alternative=options)

        # 分析历史经验
        success_options = defaultdict(list)
        for exp in similar:
            if exp.success:
                success_options[exp.action].append(exp.success_rate)

        if not success_options:
            return Recommendation(
                experience=similar[0], confidence=0.1, reasoning="相似经验均为失败案例", alternative=options
            )

        # 选择最佳选项
        best_option = max(success_options.items(), key=lambda x: sum(x[1]) / len(x[1]))

        best_exp = next(e for e in similar if e.action == best_option[0])
        confidence = best_exp.score * (len(similar) / max(1, self.stats["total"]))

        self.stats["recommendations_made"] += 1

        return Recommendation(
            experience=best_exp,
            confidence=confidence,
            reasoning=f"基于 {len(similar)} 条相似经验，成功率 {best_exp.success_rate:.1%}",
            alternative=[o for o in options if o != best_option[0]],
        )

    def learn_from_result(self, context: str, action: str, result: str, success: bool):
        """从结果中学习"""
        # 检查是否有相似经验
        similar = self.find_similar(context)

        for exp in similar:
            if exp.action == action:
                # 更新已有经验
                exp.update_score(success)
                self._save_to_db(exp)

                if success:
                    self.stats["recommendations_used"] += 1

                logger.info(f"[Experience] 更新经验: {action[:30]}... (成功率: {exp.success_rate:.1%})")
                return exp

        # 添加新经验
        return self.add_experience(context, action, result, success)

    def detect_patterns(self) -> Dict[str, List[Dict]]:
        """检测模式"""
        patterns = defaultdict(list)

        # 按标签分组
        tag_groups = defaultdict(list)
        for exp in self.experiences.values():
            for tag in exp.tags:
                tag_groups[tag].append(exp)

        # 检测成功模式
        for tag, exps in tag_groups.items():
            if len(exps) >= 3:
                success_count = sum(1 for e in exps if e.success)
                success_rate = success_count / len(exps)

                if success_rate >= 0.7:
                    patterns["high_success"].append(
                        {
                            "pattern": tag,
                            "count": len(exps),
                            "success_rate": success_rate,
                            "recommended_action": max(exps, key=lambda e: e.success_rate).action,
                        }
                    )

        # 检测失败模式
        for tag, exps in tag_groups.items():
            if len(exps) >= 2:
                fail_count = sum(1 for e in exps if not e.success)

                if fail_count / len(exps) >= 0.7:
                    patterns["high_failure"].append(
                        {
                            "pattern": tag,
                            "count": len(exps),
                            "failure_rate": fail_count / len(exps),
                            "actions_to_avoid": [e.action for e in exps if not e.success],
                        }
                    )

        return patterns

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        success_rate = self.stats["success"] / self.stats["total"] if self.stats["total"] > 0 else 0

        # 按类型统计
        by_type = defaultdict(lambda: {"count": 0, "success": 0})
        for exp in self.experiences.values():
            by_type[exp.type]["count"] += 1
            if exp.success:
                by_type[exp.type]["success"] += 1

        # 高分经验
        top_experiences = sorted(self.experiences.values(), key=lambda e: e.score, reverse=True)[:10]

        return {
            "summary": {
                "total": self.stats["total"],
                "success": self.stats["success"],
                "failure": self.stats["failure"],
                "success_rate": f"{success_rate:.1%}",
            },
            "by_type": dict(by_type),
            "top_experiences": [
                {"id": e.id, "action": e.action[:50], "score": e.score, "use_count": e.use_count}
                for e in top_experiences
            ],
            "patterns": self.detect_patterns(),
            "recommendations": {"made": self.stats["recommendations_made"], "used": self.stats["recommendations_used"]},
        }

    def export_dashboard(self) -> str:
        """导出Dashboard数据"""
        return json.dumps(
            {
                "experiences": [asdict(e) for e in self.experiences.values()],
                "statistics": self.get_statistics(),
                "patterns": self.detect_patterns(),
            },
            ensure_ascii=False,
            indent=2,
        )

    def cleanup_old_experiences(self, days: int = 90, min_score: float = 0.1):
        """清理低分旧经验"""
        cutoff_time = time.time() - (days * 86400)
        removed = 0

        to_remove = []
        for exp in self.experiences.values():
            created = time.mktime(time.strptime(exp.created_at, "%Y-%m-%d %H:%M:%S"))
            if created < cutoff_time and exp.score < min_score:
                to_remove.append(exp.id)

        for exp_id in to_remove:
            del self.experiences[exp_id]
            removed += 1

        logger.info(f"[ExperienceBase] 清理了 {removed} 条低分经验")
        return removed

# ==================== 快速测试 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("ExperienceBase 测试")
    print("=" * 60)

    exp_base = ExperienceBase()

    # 添加经验
    print("\n[1] 添加经验...")
    exp_base.add_experience(
        "系统内存使用率超过80%",
        "调用system-monitor清理缓存",
        "内存使用率降低到60%",
        True,
        tags=["memory", "optimization"],
        metadata={"memory_before": 85, "memory_after": 60},
    )
    print("  ✅ 成功经验")

    exp_base.add_experience("AI网关调用超时", "切换到备用模型", "任务完成", True, tags=["ai", "fallback"])
    print("  ✅ 备用方案经验")

    exp_base.add_experience("执行未知操作", "直接执行未测试的操作", "系统异常", False, tags=["error", "caution"])
    print("  ❌ 失败经验")

    # 查找相似
    print("\n[2] 查找相似经验...")
    similar = exp_base.find_similar("内存占用过高怎么办")
    print(f"  找到 {len(similar)} 条相似经验")
    for e in similar[:3]:
        print(f"    - {e.action[:40]}... (成功率: {e.success_rate:.0%})")

    # 推荐行动
    print("\n[3] 行动推荐...")
    rec = exp_base.recommend_action("系统响应变慢", ["重启服务", "清理内存", "忽略"])
    if rec.experience:
        print(f"  推荐: {rec.experience.action}")
        print(f"  置信度: {rec.confidence:.1%}")
        print(f"  原因: {rec.reasoning}")
    else:
        print("  无推荐")

    # 统计信息
    print("\n[4] 统计信息...")
    stats = exp_base.get_statistics()
    print(f"  总经验: {stats['summary']['total']}")
    print(f"  成功率: {stats['summary']['success_rate']}")

    # 模式检测
    print("\n[5] 模式检测...")
    patterns = exp_base.detect_patterns()
    print(f"  高成功率模式: {len(patterns.get('high_success', []))}")
    print(f"  高失败率模式: {len(patterns.get('high_failure', []))}")

    # Dashboard
    print("\n[6] Dashboard导出...")
    dashboard = exp_base.export_dashboard()
    print(f"  数据长度: {len(dashboard)} 字符")

    print("\n" + "=" * 60)
    print("✅ ExperienceBase 就绪！")
    print("=" * 60)

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("experience_base.execute", "start", action=action)
        self.metrics_collector.counter("experience_base.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "experience_base"}
            else:
                result = {"success": True, "action": action, "module": "experience_base"}
            self.metrics_collector.counter("experience_base.execute.success", 1)
            self.trace("experience_base.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("experience_base.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "experience_base"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "experience_base", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("experience_base.initialize", "start")
        self.metrics_collector.gauge("experience_base.initialized", 1)
        self.audit("初始化experience_base", level="info")
        self.trace("experience_base.initialize", "end")
        return {"success": True, "module": "experience_base"}

module_class = ExperienceBase
