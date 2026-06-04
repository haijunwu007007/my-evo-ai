"""
# Grade: A
AUTO-EVO-AI V0.1 — Agent Market (智能体市场)
============================================
企业级智能体市场，负责技能/插件发布、版本管理、依赖解析、安全审计与安装部署。
支持技能评分、搜索发现、权限控制与灰度发布。

继承: EnterpriseModule
"""

__module_meta__ = {
        "id": "agent-market",
        "name": "Agent Market",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "source_code",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "skill_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "skill",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "all_skills",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "category",
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
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "agent_market.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "engine",
            "manager",
            "multi-agent",
            "agent"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Agent Market (智能体市场) ============================================"
    }
from typing import Tuple

import time
import json
import hashlib
from core.logging_config import get_logger
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("agent.market")

class SkillStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class SkillCategory(Enum):
    COMMUNICATION = "communication"
    DATA_ANALYSIS = "data_analysis"
    AUTOMATION = "automation"
    SECURITY = "security"
    AI_ML = "ai_ml"
    DEVOPS = "devops"
    INTEGRATION = "integration"
    PRODUCTIVITY = "productivity"

class SecurityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class SkillAuthor:
    author_id: str = ""
    name: str = ""
    email: str = ""
    reputation_score: float = 0.0
    skills_count: int = 0

    def to_dict(self) -> dict:
        return {
            "author_id": self.author_id,
            "name": self.name,
            "email": self.email,
            "reputation_score": self.reputation_score,
            "skills_count": self.skills_count,
        }

@dataclass
class SkillVersion:
    version: str = "1.0.0"
    changelog: str = ""
    released_at: float = field(default_factory=time.time)
    download_count: int = 0
    size_bytes: int = 0
    checksum_sha256: str = ""
    min_platform_version: str = ""
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "changelog": self.changelog,
            "released_at": self.released_at,
            "download_count": self.download_count,
            "size_bytes": self.size_bytes,
            "dependencies": self.dependencies,
        }

@dataclass
class SkillReview:
    review_id: str = ""
    reviewer_id: str = ""
    rating: int = 5  # 1-5
    comment: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "reviewer_id": self.reviewer_id,
            "rating": self.rating,
            "comment": self.comment,
        }

@dataclass
class Skill:
    skill_id: str = ""
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.AUTOMATION
    author: SkillAuthor = field(default_factory=SkillAuthor)
    status: SkillStatus = SkillStatus.DRAFT
    tags: list[str] = field(default_factory=list)
    versions: list[SkillVersion] = field(default_factory=list)
    reviews: list[SkillReview] = field(default_factory=list)
    download_count: int = 0
    install_count: int = 0
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    license_type: str = "MIT"
    homepage: str = ""
    repository: str = ""
    icon_url: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def latest_version(self) -> SkillVersion | None:
        return self.versions[-1] if self.versions else None

    @property
    def avg_rating(self) -> float:
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 2)

    @property
    def review_count(self) -> int:
        return len(self.reviews)

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "author": self.author.to_dict(),
            "status": self.status.value,
            "tags": self.tags,
            "latest_version": self.latest_version.version if self.latest_version else None,
            "download_count": self.download_count,
            "install_count": self.install_count,
            "avg_rating": self.avg_rating,
            "review_count": self.review_count,
            "security_level": self.security_level.value,
            "license_type": self.license_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

# ============================================================
# 安全审计引擎
# ============================================================

class SecurityAuditor:
    """技能安全审计引擎"""

    HIGH_RISK_PATTERNS = [
        "subprocess.run",
        "os.system",
        "eval(",
        "exec(",
        "__import__",
        "ctypes",
        "shutil.rmtree",
        "os.remove",
        "os.unlink",
        "open(",
        "requests.post",
    ]

    NETWORK_PATTERNS = ["requests.get", "requests.post", "urllib", "socket", "http.client", "websocket", "ftplib"]

    FILE_PATTERNS = ["open(", "Path(", "os.path", "shutil", "tempfile"]

    def audit(self, source_code: str, skill_name: str = "") -> dict:
        """执行安全审计"""
        findings = []
        risk_score = 0.0

        # 高危模式检测
        high_risk_count = 0
        for pattern in self.HIGH_RISK_PATTERNS:
            count = source_code.count(pattern)
            if count > 0:
                high_risk_count += count
                findings.append(
                    {
                        "severity": "HIGH",
                        "pattern": pattern,
                        "count": count,
                        "message": f"检测到高危模式: {pattern} (出现{count}次)",
                    }
                )
                risk_score += 0.15 * count

        # 网络访问检测
        net_count = 0
        for pattern in self.NETWORK_PATTERNS:
            count = source_code.count(pattern)
            if count > 0:
                net_count += count
                findings.append(
                    {"severity": "MEDIUM", "pattern": pattern, "count": count, "message": f"检测到网络访问: {pattern}"}
                )
                risk_score += 0.05 * count

        # 文件操作检测
        file_count = 0
        for pattern in self.FILE_PATTERNS:
            count = source_code.count(pattern)
            if count > 0:
                file_count += count
        if file_count > 5:
            findings.append(
                {
                    "severity": "LOW",
                    "pattern": "file_operations",
                    "count": file_count,
                    "message": f"检测到大量文件操作 ({file_count}次)",
                }
            )
            risk_score += 0.05

        risk_score = min(1.0, risk_score)
        if risk_score >= 0.5:
            security_level = SecurityLevel.CRITICAL
        elif risk_score >= 0.3:
            security_level = SecurityLevel.HIGH
        elif risk_score >= 0.1:
            security_level = SecurityLevel.MEDIUM
        else:
            security_level = SecurityLevel.LOW

        return {
            "skill_name": skill_name,
            "risk_score": round(risk_score, 4),
            "security_level": security_level.value,
            "findings": findings,
            "high_risk_count": high_risk_count,
            "network_access": net_count > 0,
            "file_operations": file_count > 0,
            "passed": risk_score < 0.5,
        }

# ============================================================
# 搜索引擎
# ============================================================

class SkillSearchEngine:
    """技能搜索引擎"""

    def __init__(self):
        self._index: dict[str, list[str]] = defaultdict(list)  # token -> [skill_ids]

    def index_skill(self, skill: Skill):
        """索引技能"""
        tokens = self._tokenize(f"{skill.name} {skill.description} {' '.join(skill.tags)}")
        for token in tokens:
            if skill.skill_id not in self._index[token]:
                self._index[token].append(skill.skill_id)

    def search(
        self,
        query: str,
        all_skills: dict[str, Skill],
        category: SkillCategory | None = None,
        min_rating: float = 0.0,
        sort_by: str = "relevance",
        limit: int = 20,
    ) -> list[Skill]:
        """搜索技能"""
        tokens = self._tokenize(query)
        scores: dict[str, float] = defaultdict(float)

        for token in tokens:
            for sid in self._index.get(token, []):
                scores[sid] += 1.0

        # 应用过滤器
        results = []
        for sid, score in scores.items():
            skill = all_skills.get(sid)
            if not skill:
                continue
            if skill.status != SkillStatus.PUBLISHED:
                continue
            if category and skill.category != category:
                continue
            if skill.avg_rating < min_rating:
                continue
            # 综合评分 = 搜索相关性 + 评分权重 + 下载权重
            final_score = score + skill.avg_rating * 0.5 + min(skill.download_count / 1000, 1.0) * 0.3
            results.append((skill, final_score))

        if sort_by == "rating":
            results.sort(key=lambda x: x[0].avg_rating, reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda x: x[0].download_count, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x[0].created_at, reverse=True)
        else:
            results.sort(key=lambda x: x[1], reverse=True)

        return [skill for skill, _ in results[:limit]]

    def _tokenize(self, text: str) -> list[str]:
        """分词"""
        words = text.lower().replace("_", " ").replace("-", " ").split()
        return [w.strip() for w in words if len(w) > 1]

# ============================================================
class SkillVersionManager:
    """技能版本管理器 - 处理技能包的语义化版本控制与兼容性检查。

    企业场景：技能市场需要管理数百个技能的多版本共存，
    支持语义化版本(SemVer)、向后兼容性校验、灰度发布回滚。
    """

    def __init__(self):
        self._versions: dict[str, list[dict]] = defaultdict(list)
        self._install_records: dict[str, dict] = {}

    def register_version(self, skill_id: str, version: str, changelog: str = "", breaking: bool = False):
        """注册新版本"""
        major, minor, patch = self._parse_version(version)
        entry = {
            "version": version,
            "major": major,
            "minor": minor,
            "patch": patch,
            "changelog": changelog,
            "breaking": breaking,
            "published_at": datetime.now().isoformat(),
        }
        self._versions[skill_id].append(entry)
        self._versions[skill_id].sort(key=lambda v: (v["major"], v["minor"], v["patch"]))

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """解析语义化版本号"""
        parts = version.lstrip("v").split(".")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2].split("-")[0]) if len(parts) > 2 else 0,
        )

    def get_compatible_versions(self, skill_id: str, constraint: str) -> list[str]:
        """获取满足约束的版本列表（支持^和~前缀）"""
        all_versions = self._versions.get(skill_id, [])
        if not all_versions:
            return []
        if constraint.startswith("^"):
            base = self._parse_version(constraint[1:])
            return [
                v["version"]
                for v in all_versions
                if v["major"] == base[0] and (v["major"], v["minor"], v["patch"]) >= (base[0], base[1], base[2])
            ]
        elif constraint.startswith("~"):
            base = self._parse_version(constraint[1:])
            return [v["version"] for v in all_versions if v["major"] == base[0] and v["minor"] == base[1]]
        else:
            return [v["version"] for v in all_versions if v["version"].startswith(constraint)]

    def check_breaking_changes(self, skill_id: str, from_ver: str, to_ver: str) -> list[dict]:
        """检查两个版本间是否存在破坏性变更"""
        versions = self._versions.get(skill_id, [])
        from_parsed = self._parse_version(from_ver)
        to_parsed = self._parse_version(to_ver)
        changes = []
        for v in versions:
            vp = (v["major"], v["minor"], v["patch"])
            if from_parsed <= vp <= to_parsed and v.get("breaking"):
                changes.append(
                    {
                        "version": v["version"],
                        "changelog": v.get("changelog", ""),
                        "breaking": True,
                    }
                )
        return changes

    def rollback(self, skill_id: str, target_version: str) -> dict:
        """执行版本回滚"""
        versions = self._versions.get(skill_id, [])
        target = next((v for v in versions if v["version"] == target_version), None)
        if not target:
            return {"success": False, "error": f"版本 {target_version} 不存在"}
        self._install_records[skill_id] = {
            "version": target_version,
            "installed_at": datetime.now().isoformat(),
            "action": "rollback",
        }
        return {"success": True, "rolled_back_to": target_version}

# 主模块: AgentMarket
# ============================================================

class AgentMarket(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """智能体市场 — 技能发布与分发"""

    def __init__(self, config: dict | None = None):

        super().__init__(module_name="agent_market", version="6.39.0", config=config)
        self._skills: dict[str, Skill] = {}
        self._authors: dict[str, SkillAuthor] = {}
        self._auditor = SecurityAuditor()
        self._search = SkillSearchEngine()
        self._installations: dict[str, dict[str, str]] = defaultdict(dict)  # user -> {skill_id: version}
        self._stats = {
            "total_skills": 0,
            "published_skills": 0,
            "total_downloads": 0,
            "total_installs": 0,
            "total_reviews": 0,
            "total_audits": 0,
        }

    async def initialize(self) -> None:
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentMarket 智能体市场初始化完成")

    # === 技能管理 ===

    async def publish_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        author_id: str,
        author_name: str,
        category: SkillCategory,
        source_code: str = "",
        version: str = "1.0.0",
        tags: list[str] | None = None,
        license_type: str = "MIT",
        homepage: str = "",
        repository: str = "",
    ) -> Result:
        """发布新技能"""
        if skill_id in self._skills:
            return Result(success=False, message=f"技能 {skill_id} 已存在")

        # 安全审计
        audit = self._auditor.audit(source_code, name)
        self._stats["total_audits"] += 1

        if not audit["passed"]:
            await self._audit_log("skill_rejected_security", f"技能 {name} 安全审计未通过: risk={audit['risk_score']}")
            return Result(success=False, message=f"安全审计未通过: risk_score={audit['risk_score']}", data=audit)

        # 创建作者
        if author_id not in self._authors:
            author = SkillAuthor(author_id=author_id, name=author_name)
            self._authors[author_id] = author
        self._authors[author_id].skills_count += 1

        # 创建技能
        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            category=category,
            author=self._authors[author_id],
            status=SkillStatus.PUBLISHED,
            tags=tags or [],
            security_level=SecurityLevel(audit["security_level"]),
            license_type=license_type,
            homepage=homepage,
            repository=repository,
            versions=[SkillVersion(version=version, changelog="初始发布", released_at=time.time())],
        )
        self._skills[skill_id] = skill
        self._search.index_skill(skill)
        self._stats["total_skills"] += 1
        self._stats["published_skills"] += 1

        await self._audit_log("publish_skill", f"发布技能: {name} ({skill_id})")

        return Result(success=True, message="技能发布成功", data={**skill.to_dict(), "security_audit": audit})

    async def update_skill_version(
        self, skill_id: str, version: str, changelog: str = "", source_code: str = ""
    ) -> Result:
        """更新技能版本"""
        skill = self._skills.get(skill_id)
        if not skill:
            return Result(success=False, message=f"技能 {skill_id} 不存在")

        # 安全审计
        if source_code:
            audit = self._auditor.audit(source_code, skill.name)
            self._stats["total_audits"] += 1
            skill.security_level = SecurityLevel(audit["security_level"])
            if not audit["passed"]:
                return Result(success=False, message="新版本安全审计未通过", data=audit)

        new_ver = SkillVersion(version=version, changelog=changelog, released_at=time.time())
        skill.versions.append(new_ver)
        skill.updated_at = time.time()
        await self._audit_log("update_version", f"更新版本: {skill_id} -> {version}")
        return Result(success=True, data=skill.to_dict())

    async def deprecate_skill(self, skill_id: str, reason: str = "") -> Result:
        skill = self._skills.get(skill_id)
        if not skill:
            return Result(success=False, message=f"技能 {skill_id} 不存在")
        skill.status = SkillStatus.DEPRECATED
        skill.updated_at = time.time()
        await self._audit_log("deprecate_skill", f"弃用技能: {skill_id}, 原因: {reason}")
        return Result(success=True, message=f"技能 {skill_id} 已标记为弃用")

    # === 搜索与发现 ===

    async def search_skills(
        self,
        query: str,
        category: SkillCategory | None = None,
        min_rating: float = 0.0,
        sort_by: str = "relevance",
        limit: int = 20,
    ) -> Result:
        results = self._search.search(query, self._skills, category, min_rating, sort_by, limit)
        return Result(
            success=True, data={"skills": [s.to_dict() for s in results], "count": len(results), "query": query}
        )

    async def get_skill(self, skill_id: str) -> Result:
        skill = self._skills.get(skill_id)
        if not skill:
            return Result(success=False, message=f"技能 {skill_id} 不存在")
        return Result(success=True, data=skill.to_dict())

    async def list_skills(
        self, category: SkillCategory | None = None, status: SkillStatus | None = None, limit: int = 50
    ) -> Result:
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if status:
            skills = [s for s in skills if s.status == status]
        skills.sort(key=lambda s: s.updated_at, reverse=True)
        return Result(success=True, data={"skills": [s.to_dict() for s in skills[:limit]], "count": len(skills)})

    async def get_trending(self, period_days: int = 7, limit: int = 10) -> Result:
        """获取热门技能"""
        cutoff = time.time() - period_days * 86400
        trending = [s for s in self._skills.values() if s.status == SkillStatus.PUBLISHED and s.updated_at >= cutoff]
        trending.sort(key=lambda s: s.download_count + s.install_count, reverse=True)
        return Result(success=True, data={"trending": [s.to_dict() for s in trending[:limit]]})

    # === 安装管理 ===

    async def install_skill(self, user_id: str, skill_id: str, version: str | None = None) -> Result:
        skill = self._skills.get(skill_id)
        if not skill:
            return Result(success=False, message=f"技能 {skill_id} 不存在")
        if skill.status not in (SkillStatus.PUBLISHED,):
            return Result(success=False, message=f"技能状态不允许安装: {skill.status.value}")
        ver = version or (skill.latest_version.version if skill.latest_version else "1.0.0")
        self._installations[user_id][skill_id] = ver
        skill.install_count += 1
        self._stats["total_installs"] += 1
        return Result(success=True, message=f"已安装 {skill_id} v{ver}")

    async def get_user_installations(self, user_id: str) -> Result:
        installs = self._installations.get(user_id, {})
        details = []
        for sid, ver in installs.items():
            skill = self._skills.get(sid)
            if skill:
                details.append({"skill_id": sid, "name": skill.name, "version": ver})
        return Result(success=True, data={"installations": details, "count": len(details)})

    # === 评分管理 ===

    async def add_review(self, skill_id: str, reviewer_id: str, rating: int, comment: str = "") -> Result:
        if not (1 <= rating <= 5):
            return Result(success=False, message="评分必须在1-5之间")
        skill = self._skills.get(skill_id)
        if not skill:
            return Result(success=False, message=f"技能 {skill_id} 不存在")
        review = SkillReview(
            review_id=hashlib.md5(f"{skill_id}:{reviewer_id}:{time.time()}".encode()).hexdigest()[:16],
            reviewer_id=reviewer_id,
            rating=rating,
            comment=comment,
        )
        skill.reviews.append(review)
        self._stats["total_reviews"] += 1
        return Result(success=True, data=review.to_dict())

    # === 健康检查 ===

    async def execute(self, action: str, params: dict | None = None) -> dict[str, Any]:
        """统一执行入口 — 技能市场路由"""
        _ = self.trace("execute")
        metrics_collector.counter("agent_market_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        if action == "health":
            hr = self.health_check()
            return hr.to_dict() if hasattr(hr, "to_dict") else {"status": "healthy"}
        elif action == "stats":
            skills = self._skills if hasattr(self, "_skills") else {}
            return {"success": True, "result": {"total_skills": len(skills)}}
        return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> HealthReport:
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING,
            checks={"skill_store": True, "search_engine": True, "security_auditor": True},
            stats=ModuleStats(total_operations=sum(self._stats.values())),
        )

    async def get_module_stats(self) -> Result:
        return Result(success=True, data=self._stats)

    def generate_marketplace_report(self) -> dict[str, Any]:
        """生成市场报告：技能分类统计、评分分布、活跃度趋势、下载排行"""
        skills = self._skills if hasattr(self, "_skills") else {}
        categories: dict[str, int] = {}
        ratings: dict[int, int] = {}
        total_reviews = 0
        total_downloads = 0
        for sid, skill in skills.items():
            cat = getattr(skill, "category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
            avg_r = getattr(skill, "avg_rating", lambda: 0)()
            bucket = int(avg_r)
            ratings[bucket] = ratings.get(bucket, 0) + 1
            total_reviews += getattr(skill, "review_count", 0)
            total_downloads += getattr(skill, "download_count", 0)
        return {
            "total_skills": len(skills),
            "categories": categories,
            "rating_distribution": ratings,
            "total_reviews": total_reviews,
            "total_downloads": total_downloads,
            "avg_marketplace_rating": round(
                sum(getattr(s, "avg_rating", lambda: 0)() for s in skills.values()) / max(len(skills), 1), 2
            ),
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_market."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentMarket
