"""
AUTO-EVO-AI V0.1 — 智能体市场
Grade: A (生产级) | Category: AI智能体
职责：智能体市场管理、技能包发布与安装、插件生命周期、版本管理、评分评论
"""
from __future__ import annotations

__module_meta__ = {
        "id": "agent-marketplace",
        "name": "Agent Marketplace",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "package_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "registry",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "packages",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "package_ids",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "registry_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "packages_2",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "results",
                "type": "list[dict]",
                "description": "结果列表"
            },
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "agent_marketplace.task.request"
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
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 智能体市场 Grade: A (生产级) | Category: AI智能体"
    }

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("agent_marketplace")

class PackageStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REMOVED = "removed"

class PackageCategory(Enum):
    AGENT = "agent"
    SKILL = "skill"
    PLUGIN = "plugin"
    TEMPLATE = "template"
    INTEGRATION = "integration"

@dataclass
class PackageVersion:
    """版本信息"""

    version: str
    changelog: str = ""
    released_at: float = field(default_factory=time.time)

@dataclass
class MarketplacePackage:
    """市场包"""

    package_id: str
    name: str
    author: str
    category: PackageCategory
    description: str = ""
    status: PackageStatus = PackageStatus.DRAFT
    versions: list[PackageVersion] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    dependencies: list[PackageDependency] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def latest_version(self) -> str:
        return self.versions[-1].version if self.versions else "0.0.0"

@dataclass
class PackageDependency:
    """包依赖声明"""

    package_id: str
    min_version: str = ""
    max_version: str = ""

class PackageDependencyResolver:
    """包依赖解析器 - 解决包安装顺序、循环依赖检测、版本兼容性"""

    def __init__(self):
        self._resolved: dict[str, str] = {}  # package_id -> resolved_version
        self._resolving: set = set()  # 当前解析栈，用于检测循环依赖

    def resolve(self, package_id: str, registry: dict[str, Package]) -> list[str]:
        """解析包及其所有依赖的安装顺序"""
        if package_id in self._resolved:
            return []
        if package_id in self._resolving:
            logger.warning(f"检测到循环依赖: {package_id}")
            return []
        if package_id not in registry:
            logger.warning(f"依赖包不存在: {package_id}")
            return []
        self._resolving.add(package_id)
        order = []
        pkg = registry[package_id]
        for dep in getattr(pkg, "dependencies", []):
            sub = self.resolve(dep.package_id, registry)
            order.extend(sub)
        self._resolving.discard(package_id)
        self._resolved[package_id] = pkg.version
        order.append(package_id)
        metrics_collector.counter("marketplace_dep_resolved", len(order))
        return order

    def check_conflicts(self, packages: list[Package]) -> list[dict]:
        """检查多个包之间的版本冲突"""
        version_map: dict[str, list[str]] = {}
        for pkg in packages:
            for dep in getattr(pkg, "dependencies", []):
                version_map.setdefault(dep.package_id, []).append(dep.min_version)
        conflicts = []
        for pkg_id, versions in version_map.items():
            unique = set(v for v in versions if v)
            if len(unique) > 1:
                conflicts.append({"package": pkg_id, "required_versions": sorted(unique)})
        return conflicts

    def get_install_plan(self, package_ids: list[str], registry: dict[str, Package]) -> dict:
        """生成完整安装计划，包含依赖"""
        plan = []
        visited = set()
        for pid in package_ids:
            if pid not in visited:
                deps = self.resolve(pid, registry)
                for d in deps:
                    if d not in visited:
                        visited.add(d)
                        plan.append(d)
        return {
            "total": len(plan),
            "order": plan,
            "has_conflicts": len(
                self.check_conflicts([registry.get(p, Package(id=p)) for p in package_ids if p in registry])
            )
            > 0,
        }

@dataclass
class Review:
    """评论"""

    review_id: str
    package_id: str
    user: str
    rating: int
    comment: str = ""
    created_at: float = field(default_factory=time.time)

class PackageDependencyResolver:
    """包依赖解析器 — 检查依赖完整性、解析安装顺序、检测循环依赖"""

    def __init__(self, packages: dict):
        self._packages = packages

    def resolve_install_order(self, package_id: str, target_version: str = "latest") -> dict[str, Any]:
        """解析安装顺序（拓扑排序），返回安装计划"""
        if package_id not in self._packages:
            return {"error": "Package not found"}
        order = []
        visited = set()
        path = []

        def visit(pid: str) -> str | None:
            if pid in path:
                return f"Circular dependency detected: {' -> '.join(path + [pid])}"
            if pid in visited:
                return None
            pkg = self._packages.get(pid)
            if not pkg:
                return f"Dependency not found: {pid}"
            path.append(pid)
            for dep in pkg.dependencies:
                err = visit(dep.package_id)
                if err:
                    return err
            path.pop()
            visited.add(pid)
            order.append({"package_id": pid, "name": pkg.name, "version": pkg.latest_version})
            return None

        err = visit(package_id)
        if err:
            return {"error": err, "package_id": package_id}
        return {"install_order": order, "total": len(order)}

    def check_dependencies(self, package_id: str) -> dict[str, Any]:
        """检查某包的所有依赖是否满足"""
        pkg = self._packages.get(package_id)
        if not pkg:
            return {"error": "Package not found"}
        missing = []
        version_conflicts = []
        for dep in pkg.dependencies:
            dep_pkg = self._packages.get(dep.package_id)
            if not dep_pkg:
                missing.append(dep.package_id)
            elif dep.min_version and self._version_compare(dep_pkg.latest_version, dep.min_version) < 0:
                version_conflicts.append(
                    {
                        "dependency": dep.package_id,
                        "required": f">={dep.min_version}",
                        "available": dep_pkg.latest_version,
                    }
                )
        return {
            "package_id": package_id,
            "total_deps": len(pkg.dependencies),
            "missing": missing,
            "version_conflicts": version_conflicts,
            "satisfied": len(pkg.dependencies) - len(missing) - len(version_conflicts),
        }

    def get_reverse_deps(self, package_id: str) -> list[dict]:
        """获取依赖某包的所有包（反向依赖）"""
        dependents = []
        for pkg in self._packages.values():
            for dep in pkg.dependencies:
                if dep.package_id == package_id:
                    dependents.append({"package_id": pkg.package_id, "name": pkg.name, "version": pkg.latest_version})
        return dependents

    @staticmethod
    def _version_compare(v1: str, v2: str) -> int:
        """比较版本号，返回 -1/0/1"""
        try:
            p1 = [int(x) for x in v1.split(".")]
            p2 = [int(x) for x in v2.split(".")]
            for a, b in zip(p1, p2):
                if a != b:
                    return -1 if a < b else 1
            return 0
        except (ValueError, AttributeError):
            return 0

class MarketplaceSearchEngine:
    """市场搜索引擎 — 支持全文匹配、权重排序、分页"""

    def __init__(self, packages: dict):
        self._packages = packages
        self._field_weights = {"name": 3.0, "tags": 2.0, "description": 1.0, "author": 0.5}

    def search(
        self, query: str, category: str = "", page: int = 1, page_size: int = 20, sort_by: str = "relevance"
    ) -> dict[str, Any]:
        """执行搜索，返回分页结果"""
        query_lower = query.lower()
        scored = []
        for pkg in self._packages.values():
            if category and pkg.category.value != category:
                continue
            if pkg.status not in (PackageStatus.PUBLISHED,):
                continue
            score = self._compute_score(query_lower, pkg)
            if score > 0:
                scored.append((pkg, score))
        # 排序
        if sort_by == "downloads":
            scored.sort(key=lambda x: x[0].downloads, reverse=True)
        elif sort_by == "rating":
            scored.sort(key=lambda x: (x[0].rating, x[0].rating_count), reverse=True)
        elif sort_by == "newest":
            scored.sort(key=lambda x: x[0].created_at, reverse=True)
        else:  # relevance
            scored.sort(key=lambda x: x[1], reverse=True)
        total = len(scored)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = [
            {
                "package_id": p.package_id,
                "name": p.name,
                "author": p.author,
                "category": p.category.value,
                "latest_version": p.latest_version,
                "downloads": p.downloads,
                "rating": p.rating,
                "tags": p.tags,
                "relevance_score": round(s, 2),
            }
            for p, s in scored[start:end]
        ]
        metrics_collector.counter("marketplace_search_total")
        metrics_collector.histogram("marketplace_search_results", total)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, -(-total // page_size)),
            "results": page_results,
        }

    def _compute_score(self, query: str, pkg: MarketplacePackage) -> float:
        """计算搜索相关度分数"""
        score = 0.0
        if query in pkg.name.lower():
            score += self._field_weights["name"] * (2.0 if pkg.name.lower() == query else 1.0)
        if query in pkg.description.lower():
            score += self._field_weights["description"]
        for tag in pkg.tags:
            if query in tag.lower():
                score += self._field_weights["tags"]
                break
        if query in pkg.author.lower():
            score += self._field_weights["author"]
        # 下载量和评分加权
        if score > 0:
            score *= 1 + min(pkg.downloads / 1000, 2)  # 最多2倍下载加权
            score *= 1 + pkg.rating / 10  # 最多1.5倍评分加权
        return score

class AgentMarketplaceManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """智能体市场管理器"""

    MODULE_ID = "agent_marketplace"
    MODULE_NAME = "智能体市场"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._packages: dict[str, MarketplacePackage] = {}
        self._reviews: dict[str, Review] = {}
        self._installed: dict[str, str] = {}  # package_id -> installed_version
        self._pkg_counter: int = 0
        self._rev_counter: int = 0

    def initialize(self) -> None:
        try:
            super().__init__()
            self._search_engine = MarketplaceSearchEngine(self._packages)
            self._install_rate_limit = self._init_rate_limiter("marketplace_install", max_calls=30, window=60)
            self._publish_rate_limit = self._init_rate_limiter("marketplace_publish", max_calls=10, window=60)
            self._circuit_breaker = self._init_circuit_breaker(
                "marketplace_search", failure_threshold=5, recovery_timeout=30
            )
            defaults = [
                (
                    "智能客服Agent",
                    "system",
                    PackageCategory.AGENT,
                    "自动化客服处理，支持多轮对话和知识库检索",
                    ["客服", "NLP"],
                ),
                ("代码生成器", "dev_team", PackageCategory.SKILL, "基于模板的代码生成技能", ["代码", "生成"]),
                ("Slack集成", "ops", PackageCategory.INTEGRATION, "Slack消息通知与命令集成", ["Slack", "通知"]),
            ]
            for name, author, cat, desc, tags in defaults:
                self._pkg_counter += 1
                pkg = MarketplacePackage(
                    package_id=f"pkg_{self._pkg_counter}",
                    name=name,
                    author=author,
                    category=cat,
                    description=desc,
                    tags=tags,
                    status=PackageStatus.PUBLISHED,
                    versions=[PackageVersion(version="1.0.0", changelog="初始发布")],
                )
                self._packages[pkg.package_id] = pkg
            if self._audit:
                self._audit.log("marketplace_initialized", {"packages": len(self._packages)})
            self.stats.success_count += 1
            logger.info("智能体市场初始化完成")
        except Exception as e:
            logger.error(f"市场初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = self.trace("execute")  # 链路追踪span注册
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "publish":
                name = params.get("name", "")
                author = params.get("author", "")
                category = params.get("category", "plugin")
                description = params.get("description", "")
                version = params.get("version", "1.0.0")
                tags = params.get("tags", [])
                if not name or not author:
                    return {"success": False, "error": "Missing: name, author"}
                pkg = self._publish(name, author, category, description, version, tags)
                ok = True
                self.audit("publish_package", f"name={name}, author={author}, category={category}, version={version}")
                return {
                    "success": True,
                    "result": {"package_id": pkg.package_id, "name": pkg.name, "status": pkg.status.value},
                }

            elif action == "search":
                query = params.get("query", "")
                category = params.get("category", "")
                page = params.get("page", 1)
                page_size = params.get("page_size", 20)
                sort_by = params.get("sort_by", "relevance")
                results = self._search_with_engine(query, category, page, page_size, sort_by)
                self.audit(
                    "search_packages", f"query={query}, category={category}, results={len(results.get('items', []))}"
                )
                return {"success": True, "result": results}

            elif action == "install":
                package_id = params.get("package_id", "")
                version = params.get("version", "latest")
                if not package_id:
                    return {"success": False, "error": "Missing: package_id"}
                result = self._install(package_id, version)
                ok = "error" not in result
                self.audit("install_package", f"package_id={package_id}, version={version}, success={ok}")
                return {"success": ok, "result": result}

            elif action == "uninstall":
                package_id = params.get("package_id", "")
                if not package_id:
                    return {"success": False, "error": "Missing: package_id"}
                result = self._uninstall(package_id)
                ok = "error" not in result
                self.audit("uninstall_package", f"package_id={package_id}, success={ok}")
                return {"success": ok, "result": result}

            elif action == "review":
                package_id = params.get("package_id", "")
                user = params.get("user", "")
                rating = params.get("rating", 5)
                comment = params.get("comment", "")
                if not package_id or not user:
                    return {"success": False, "error": "Missing: package_id, user"}
                result = self._add_review(package_id, user, rating, comment)
                ok = "error" not in result
                self.audit("review_package", f"package_id={package_id}, user={user}, rating={rating}")
                return {"success": ok, "result": result}

            elif action == "get_package":
                package_id = params.get("package_id", "")
                if not package_id:
                    return {"success": False, "error": "Missing: package_id"}
                pkg = self._packages.get(package_id)
                if not pkg:
                    return {"success": False, "error": "Package not found"}
                return {
                    "success": True,
                    "result": {
                        "package_id": pkg.package_id,
                        "name": pkg.name,
                        "author": pkg.author,
                        "category": pkg.category.value,
                        "status": pkg.status.value,
                        "latest_version": pkg.latest_version,
                        "downloads": pkg.downloads,
                        "rating": pkg.rating,
                        "rating_count": pkg.rating_count,
                        "tags": pkg.tags,
                    },
                }

            elif action == "get_stats":
                cat_counts = {}
                for p in self._packages.values():
                    c = p.category.value
                    cat_counts[c] = cat_counts.get(c, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total_packages": len(self._packages),
                        "installed": len(self._installed),
                        "by_category": cat_counts,
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "packages": len(self._packages),
            "installed": len(self._installed),
            "reviews": len(self._reviews),
        }

    def shutdown(self) -> None:
        pass  # super().shutdown() removed for sync compatibility

    def _publish(
        self, name: str, author: str, category: str, description: str, version: str, tags: list[str]
    ) -> MarketplacePackage:
        self._pkg_counter += 1
        try:
            cat = PackageCategory(category)
        except ValueError:
            cat = PackageCategory.PLUGIN
        pkg = MarketplacePackage(
            package_id=f"pkg_{self._pkg_counter}",
            name=name,
            author=author,
            category=cat,
            description=description,
            tags=tags,
            status=PackageStatus.PUBLISHED,
            versions=[PackageVersion(version=version, changelog="初始发布")],
        )
        self._packages[pkg.package_id] = pkg
        if self._audit:
            self._audit.log("package_published", {"package_id": pkg.package_id, "name": name})
        self.stats.success_count += 1
        return pkg

    def _search_with_engine(self, query: str, category: str, page: int, page_size: int, sort_by: str) -> dict:
        """使用搜索引擎执行搜索"""
        try:
            return self._circuit_breaker.call(
                lambda: self._search_engine.search(query, category, page, page_size, sort_by)
            )
        except Exception as e:
            logger.warning(f"搜索熔断降级，使用基础搜索: {e}")
            return self._search(query, category)

    def _search(self, query: str, category: str) -> list[dict]:
        results = []
        q = query.lower()
        for pkg in self._packages.values():
            if category and pkg.category.value != category:
                continue
            if (
                q
                and q not in pkg.name.lower()
                and q not in pkg.description.lower()
                and q not in " ".join(pkg.tags).lower()
            ):
                continue
            results.append(
                {
                    "package_id": pkg.package_id,
                    "name": pkg.name,
                    "author": pkg.author,
                    "category": pkg.category.value,
                    "status": pkg.status.value,
                    "latest_version": pkg.latest_version,
                    "downloads": pkg.downloads,
                    "rating": pkg.rating,
                    "tags": pkg.tags,
                }
            )
        self.stats.success_count += 1
        return results

    def _install(self, package_id: str, version: str) -> dict:
        pkg = self._packages.get(package_id)
        if not pkg:
            return {"error": "Package not found"}
        if pkg.status != PackageStatus.PUBLISHED:
            return {"error": f"Package status is {pkg.status.value}, cannot install"}
        ver = version if version != "latest" else pkg.latest_version
        self._installed[package_id] = ver
        pkg.downloads += 1
        if self._audit:
            self._audit.log("package_installed", {"package_id": package_id, "version": ver})
        self.stats.success_count += 1
        return {"package_id": package_id, "version": ver, "installed": True}

    def _uninstall(self, package_id: str) -> dict:
        if package_id not in self._installed:
            return {"error": "Package not installed"}
        ver = self._installed.pop(package_id)
        if self._audit:
            self._audit.log("package_uninstalled", {"package_id": package_id})
        self.stats.success_count += 1
        return {"package_id": package_id, "uninstalled": True, "was_version": ver}

    def _add_review(self, package_id: str, user: str, rating: int, comment: str) -> dict:
        pkg = self._packages.get(package_id)
        if not pkg:
            return {"error": "Package not found"}
        if not 1 <= rating <= 5:
            return {"error": "Rating must be 1-5"}
        self._rev_counter += 1
        review = Review(
            review_id=f"rev_{self._rev_counter}", package_id=package_id, user=user, rating=rating, comment=comment
        )
        self._reviews[review.review_id] = review
        # 重新计算平均评分
        pkg_reviews = [r for r in self._reviews.values() if r.package_id == package_id]
        total = sum(r.rating for r in pkg_reviews)
        pkg.rating = round(total / len(pkg_reviews), 2)
        pkg.rating_count = len(pkg_reviews)
        self.stats.success_count += 1
        return {"review_id": review.review_id, "package_rating": pkg.rating}

module_class = AgentMarketplaceManager
