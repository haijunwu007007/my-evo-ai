"""
AUTO-EVO-AI V0.1 — AgentSeek智能体搜索
Grade: A (生产级) | Category: AI智能体
职责：智能体发现、能力检索、Agent推荐、匹配评估、生态目录
"""

__module_meta__ = {
    "id": "agentseek",
    "name": "Agentseek",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "query_tags", "type": "string", "required": True, "description": ""},
        {"name": "agent_tags", "type": "string", "required": True, "description": ""},
        {"name": "query_desc", "type": "string", "required": True, "description": ""},
        {"name": "agent_desc", "type": "string", "required": True, "description": ""},
        {"name": "query", "type": "string", "required": True, "description": ""},
        {"name": "candidates", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "agentseek", "manager", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — AgentSeek智能体搜索 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import logging
import re
from typing import Any, Dict, List, Optional, Set
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
logger = logging.getLogger("agentseek")

class AgentCategory(Enum):
    AUTOMATION = "automation"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    SECURITY = "security"
    DEVOPS = "devops"
    DATA = "data"
    CREATIVE = "creative"
    GENERAL = "general"

@dataclass
class AgentProfile:
    """Agent档案"""

    agent_id: str
    name: str
    description: str
    category: AgentCategory
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    quality_score: float = 0.0
    usage_count: int = 0
    registered_at: float = field(default_factory=time.time)

@dataclass
class MatchResult:
    """匹配结果"""

    agent: AgentProfile
    score: float
    matched_capabilities: List[str]
    missing_capabilities: List[str]

class AgentMatchingEngine(object):
    """Agent匹配引擎 — 多维度相似度计算和排序"""

    def __init__(self):
        self._search_history: List[Dict] = []

    def compute_similarity(
        self, query_tags: Set[str], agent_tags: Set[str], query_desc: str = "", agent_desc: str = ""
    ) -> float:
        """计算查询与Agent的多维度相似度（Jaccard + 文本匹配）"""
        if not query_tags and not query_desc:
            return 0.0
        tag_score = 0.0
        if query_tags and agent_tags:
            tag_score = (
                len(query_tags & agent_tags) / len(query_tags | agent_tags) if (query_tags | agent_tags) else 0.0
            )
        text_score = 0.0
        if query_desc and agent_desc:
            q_words = set(query_desc.lower().split())
            a_words = set(agent_desc.lower().split())
            common = q_words & a_words
            text_score = len(common) / max(len(q_words), 1)
        return round(tag_score * 0.7 + text_score * 0.3, 4)

    def rank_agents(self, query: Dict, candidates: List[Dict]) -> List[Dict]:
        """对候选Agent按相似度排序"""
        query_tags = set(query.get("tags", []))
        query_desc = query.get("description", "")
        scored = []
        for agent in candidates:
            agent_tags = set(agent.get("tags", []))
            agent_desc = agent.get("description", "")
            score = self.compute_similarity(query_tags, agent_tags, query_desc, agent_desc)
            scored.append({**agent, "match_score": score})
        scored.sort(key=lambda x: -x["match_score"])
        self._search_history.append(
            {
                "query": query.get("description", "")[:50],
                "results": len(scored),
                "top_score": scored[0]["match_score"] if scored else 0,
            }
        )
        return scored[: query.get("limit", 20)]

    def get_search_stats(self) -> Dict:
        return {
            "total_searches": len(self._search_history),
            "avg_results": round(
                sum(s["results"] for s in self._search_history) / max(len(self._search_history), 1), 1
            ),
        }

    def build_tf_idf_index(self, agents: List[Dict]) -> Dict[str, Dict[str, float]]:
        """构建Agent描述的TF-IDF索引用于语义搜索"""
        from collections import Counter

        doc_count = len(agents)
        word_doc_freq: Dict[str, int] = Counter()
        doc_tokens: Dict[str, List[str]] = {}
        for agent in agents:
            desc = agent.get("description", "").lower()
            tags = agent.get("tags", [])
            tokens = desc.split() + [t.lower() for t in tags]
            doc_tokens[agent.get("agent_id", "")] = tokens
            for word in set(tokens):
                word_doc_freq[word] += 1
        index: Dict[str, Dict[str, float]] = {}
        for agent_id, tokens in doc_tokens.items():
            tf = Counter(tokens)
            total = len(tokens)
            scores = {}
            for word, count in tf.items():
                idf = doc_count / max(word_doc_freq[word], 1)
                scores[word] = round((count / max(total, 1)) * idf, 4)
            index[agent_id] = scores
        return index

    def semantic_search(self, query: str, tf_idf_index: Dict[str, Dict[str, float]], top_k: int = 10) -> List[Dict]:
        """基于TF-IDF的语义搜索"""
        q_words = query.lower().split()
        q_counter = Counter(q_words)
        scores: Dict[str, float] = {}
        for agent_id, word_scores in tf_idf_index.items():
            score = 0.0
            for word, q_count in q_counter.items():
                if word in word_scores:
                    score += q_count * word_scores[word]
            if score > 0:
                scores[agent_id] = round(score, 4)
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [{"agent_id": aid, "relevance_score": score} for aid, score in ranked]

    def analyze_ecosystem(self, agents: List[Dict]) -> Dict:
        """分析Agent生态系统 — 能力分布、成熟度、覆盖度"""
        all_capabilities: Dict[str, int] = {}
        quality_scores = []
        categories: Dict[str, int] = {}
        for agent in agents:
            for cap in agent.get("tags", agent.get("capabilities", [])):
                all_capabilities[cap] = all_capabilities.get(cap, 0) + 1
            quality_scores.append(agent.get("quality_score", 0))
            cat = agent.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        top_capabilities = sorted(all_capabilities.items(), key=lambda x: -x[1])[:10]
        coverage = len(set(c for c in all_capabilities if all_capabilities[c] >= 2)) / max(len(all_capabilities), 1)
        return {
            "total_agents": len(agents),
            "total_unique_capabilities": len(all_capabilities),
            "top_capabilities": [{"name": c, "count": n} for c, n in top_capabilities],
            "category_distribution": categories,
            "average_quality": round(avg_quality, 3),
            "redundancy_coverage": round(coverage, 4),
        }

    def find_compatible_agents(self, agent_id: str, agents: List[Dict], shared_tags_threshold: int = 2) -> List[Dict]:
        """发现兼容/可协作的Agent — 基于共享能力和互补性"""
        target = None
        for a in agents:
            if a.get("agent_id") == agent_id:
                target = a
                break
        if not target:
            return []
        target_tags = set(target.get("tags", target.get("capabilities", [])))
        compatible = []
        for a in agents:
            if a.get("agent_id") == agent_id:
                continue
            a_tags = set(a.get("tags", a.get("capabilities", [])))
            shared = target_tags & a_tags
            complementary = target_tags ^ a_tags
            if len(shared) >= shared_tags_threshold:
                compatible.append(
                    {
                        "agent_id": a.get("agent_id", ""),
                        "name": a.get("name", ""),
                        "shared_capabilities": list(shared),
                        "complementary_capabilities": list(complementary),
                        "shared_count": len(shared),
                        "compatibility_score": round(len(shared) / max(len(target_tags | a_tags), 1), 4),
                    }
                )
        compatible.sort(key=lambda x: -x["compatibility_score"])
        return compatible[:10]

    def build_capability_graph(self, agents: List[Dict]) -> Dict:
        """构建能力关联图 — 发现能力之间的共现关系"""
        from collections import defaultdict

        co_occurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for agent in agents:
            caps = agent.get("tags", agent.get("capabilities", []))
            for i, c1 in enumerate(caps):
                for c2 in caps[i + 1 :]:
                    co_occurrence[c1][c2] += 1
                    co_occurrence[c2][c1] += 1
        # 找出最紧密的能力对
        pairs = []
        seen = set()
        for c1, neighbors in co_occurrence.items():
            for c2, count in neighbors.items():
                pair = tuple(sorted([c1, c2]))
                if pair not in seen:
                    seen.add(pair)
                    pairs.append({"capability_1": c1, "capability_2": c2, "co_occurrence": count})
        pairs.sort(key=lambda x: -x["co_occurrence"])
        return {"total_capabilities": len(co_occurrence), "strongest_pairs": pairs[:20]}

class AgentseekManager(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """AgentSeek - 智能体发现与推荐"""

    MODULE_ID = "agentseek"
    MODULE_NAME = "AgentSeek"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._agents: Dict[str, AgentProfile] = {}
        self._counter: int = 0
        self._matching_engine = AgentMatchingEngine()

    def initialize(self) -> None:
        try:
            pass
            # super().initialize() removed for sync compatibility
            defaults = [
                (
                    "NLP分析Agent",
                    "自然语言处理与分析",
                    AgentCategory.ANALYSIS,
                    ["nlp", "sentiment", "text_analysis"],
                    ["NLP", "文本"],
                ),
                (
                    "安全扫描Agent",
                    "安全漏洞扫描与检测",
                    AgentCategory.SECURITY,
                    ["vuln_scan", "security_audit", "pen_test"],
                    ["安全", "扫描"],
                ),
                (
                    "DevOps Agent",
                    "CI/CD流水线与部署管理",
                    AgentCategory.DEVOPS,
                    ["deploy", "ci_cd", "monitoring"],
                    ["DevOps", "部署"],
                ),
                (
                    "数据清洗Agent",
                    "数据质量检测与清洗",
                    AgentCategory.DATA,
                    ["data_clean", "etl", "quality_check"],
                    ["数据", "ETL"],
                ),
                (
                    "客服Agent",
                    "智能客服与问答",
                    AgentCategory.COMMUNICATION,
                    ["chat", "faq", "dialogue"],
                    ["客服", "对话"],
                ),
                (
                    "代码审查Agent",
                    "代码质量审查与建议",
                    AgentCategory.DEVOPS,
                    ["code_review", "lint", "refactor"],
                    ["代码", "审查"],
                ),
            ]
            for name, desc, cat, caps, tags in defaults:
                self._counter += 1
                profile = AgentProfile(
                    agent_id=f"agent_{self._counter}",
                    name=name,
                    description=desc,
                    category=cat,
                    capabilities=caps,
                    tags=tags,
                    quality_score=round(0.7 + hash(name) % 30 / 100, 2),
                    usage_count=hash(name) % 500,
                )
                self._agents[profile.agent_id] = profile
            if self._audit:
                self._audit.log("agentseek_initialized", {"agents": len(self._agents)})
            self.stats.success_count += 1
            logger.info("AgentSeek初始化完成")
        except Exception as e:
            logger.error(f"AgentSeek初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("agentseek_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "search":
                query = params.get("query", "")
                capabilities = params.get("capabilities", [])
                category = params.get("category", "")
                limit = params.get("limit", 10)
                results = self._search(query, capabilities, category, limit)
                return {"success": True, "result": results}

            elif action == "recommend":
                required_caps = params.get("required_capabilities", [])
                preferred_category = params.get("category", "")
                if not required_caps:
                    return {"success": False, "error": "Missing: required_capabilities"}
                results = self._recommend(required_caps, preferred_category)
                return {"success": True, "result": results}

            elif action == "advanced_search":
                results = self._advanced_search(params)
                return {"success": True, "result": results}

            elif action == "search_stats":
                return {"success": True, "result": self._search_stats()}

            elif action == "ecosystem_analysis":
                all_agents = [
                    {
                        "agent_id": a.agent_id,
                        "name": a.name,
                        "tags": a.capabilities,
                        "category": a.category,
                        "description": a.description,
                        "quality_score": a.quality_score,
                    }
                    for a in self._agents.values()
                ]
                return {"success": True, "result": self._matching_engine.analyze_ecosystem(all_agents)}

            elif action == "find_compatible":
                all_agents = [
                    {"agent_id": a.agent_id, "tags": a.capabilities, "description": a.description}
                    for a in self._agents.values()
                ]
                return {
                    "success": True,
                    "result": self._matching_engine.find_compatible_agents(params.get("agent_id", ""), all_agents),
                }

            elif action == "register":
                name = params.get("name", "")
                description = params.get("description", "")
                category = params.get("category", "general")
                capabilities = params.get("capabilities", [])
                tags = params.get("tags", [])
                author = params.get("author", "")
                if not name:
                    return {"success": False, "error": "Missing: name"}
                self._counter += 1
                try:
                    cat = AgentCategory(category)
                except ValueError:
                    cat = AgentCategory.GENERAL
                profile = AgentProfile(
                    agent_id=f"agent_{self._counter}",
                    name=name,
                    description=description,
                    category=cat,
                    capabilities=capabilities,
                    tags=tags,
                    author=author,
                )
                self._agents[profile.agent_id] = profile
                ok = True
                if self._audit:
                    self._audit.log("agent_registered", {"agent_id": profile.agent_id, "name": name})
                return {"success": True, "result": {"agent_id": profile.agent_id, "name": name, "category": cat.value}}

            elif action == "get_agent":
                agent_id = params.get("agent_id", "")
                if not agent_id:
                    return {"success": False, "error": "Missing: agent_id"}
                agent = self._agents.get(agent_id)
                if not agent:
                    return {"success": False, "error": "Agent not found"}
                return {
                    "success": True,
                    "result": {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "description": agent.description,
                        "category": agent.category.value,
                        "capabilities": agent.capabilities,
                        "quality_score": agent.quality_score,
                        "usage_count": agent.usage_count,
                    },
                }

            elif action == "get_stats":
                cat_counts = {}
                for a in self._agents.values():
                    c = a.category.value
                    cat_counts[c] = cat_counts.get(c, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total_agents": len(self._agents),
                        "by_category": cat_counts,
                        "avg_quality": round(
                            sum(a.quality_score for a in self._agents.values()) / max(len(self._agents), 1), 3
                        ),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "agents": len(self._agents),
        }

    def shutdown(self) -> None:
        pass  # super().shutdown() removed for sync compatibility

    def analyze_agent_ecosystem(self) -> Dict[str, Any]:
        """分析Agent生态系统：能力分布、协作密度、覆盖缺口"""
        registry = self._registry if hasattr(self, "_registry") else {}
        if not registry:
            return {"total_agents": 0, "ecosystem": {}}
        cap_map: Dict[str, int] = {}
        for agent_id, agent_data in registry.items():
            caps = agent_data.get("capabilities", []) if isinstance(agent_data, dict) else []
            for cap in caps:
                cap_map[cap] = cap_map.get(cap, 0) + 1
        sorted_caps = sorted(cap_map.items(), key=lambda x: -x[1])
        total_agents = len(registry)
        multi_cap = sum(1 for a in registry.values() if len(a.get("capabilities", [])) > 3) if registry else 0
        return {
            "total_agents": total_agents,
            "unique_capabilities": len(cap_map),
            "top_capabilities": [{"capability": c, "agent_count": n} for c, n in sorted_caps[:15]],
            "multi_capability_agents": multi_cap,
            "avg_capabilities_per_agent": round(sum(cap_map.values()) / max(total_agents, 1), 1),
        }

    def _search(self, query: str, capabilities: List[str], category: str, limit: int) -> List[Dict]:
        results = []
        q = query.lower()
        for agent in self._agents.values():
            if category and agent.category.value != category:
                continue
            score = 0.0
            if q:
                if q in agent.name.lower():
                    score += 3
                if q in agent.description.lower():
                    score += 2
                if any(q in t.lower() for t in agent.tags):
                    score += 1
                if any(q in c.lower() for c in agent.capabilities):
                    score += 2
            if capabilities:
                matched = sum(1 for c in capabilities if c in agent.capabilities)
                score += matched * 2
            if score > 0:
                results.append(
                    {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "description": agent.description,
                        "category": agent.category.value,
                        "capabilities": agent.capabilities,
                        "quality_score": agent.quality_score,
                        "relevance_score": round(score, 2),
                    }
                )
        results.sort(key=lambda x: -x["relevance_score"])
        self.stats.success_count += 1
        return results[:limit]

    def _recommend(self, required_caps: List[str], category: str) -> List[Dict]:
        matches = []
        for agent in self._agents.values():
            if category and agent.category.value != category:
                continue
            matched = [c for c in required_caps if c in agent.capabilities]
            missing = [c for c in required_caps if c not in agent.capabilities]
            if matched:
                score = len(matched) / len(required_caps) * 0.6 + agent.quality_score * 0.4
                matches.append(
                    {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "match_score": round(score, 3),
                        "matched_capabilities": matched,
                        "missing_capabilities": missing,
                        "quality_score": agent.quality_score,
                    }
                )
        matches.sort(key=lambda x: -x["match_score"])
        self.stats.success_count += 1
        return matches

    def _advanced_search(self, query: Dict) -> List[Dict]:
        """使用匹配引擎的高级搜索"""
        candidates = [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "tags": a.capabilities,
                "description": a.description,
                "quality_score": a.quality_score,
            }
            for a in self._agents.values()
        ]
        return self._matching_engine.rank_agents(query, candidates)

    def _search_stats(self) -> Dict:
        """搜索统计"""
        return {
            "total_agents": len(self._agents),
            "by_category": self._count_by_category(),
            "engine_stats": self._matching_engine.get_search_stats(),
        }

    def _count_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for a in self._agents.values():
            cat = a.category.value if hasattr(a.category, "value") else str(a.category)
            counts[cat] = counts.get(cat, 0) + 1
        return counts

module_class = AgentseekManager
