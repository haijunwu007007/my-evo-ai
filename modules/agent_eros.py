"""
# Grade: A
AUTO-EVO-AI V0.1 — Agent Eros (关系管理引擎)
================================================
企业级智能体，负责实体关系建模、社交网络分析、关系强度评估与动态演化追踪。
支持多维度关系建模（血缘/协作/竞争/依赖/层级），内置关系图谱分析算法。

继承: EnterpriseModule
依赖: networkx, numpy (可选)
"""

__module_meta__ = {
        "id": "agent-eros",
        "name": "Agent Eros",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "custom_weights",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "source",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "target",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "interaction_type",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metadata",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "source_2",
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
                "name": "success",
                "type": "bool",
                "description": "是否成功"
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
                    "on": "agent_eros.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "multi-agent",
            "agent"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Agent Eros (关系管理引擎) ================================================"
    }

import time
import json
import hashlib
from core.logging_config import get_logger
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("agent.eros")

# ============================================================
# 数据模型
# ============================================================

class RelationType(Enum):
    """关系类型枚举"""

    BLOOD = "blood"  # 血缘关系
    COLLABORATION = "collab"  # 协作关系
    COMPETITION = "compet"  # 竞争关系
    DEPENDENCY = "depend"  # 依赖关系
    HIERARCHY = "hierarchy"  # 层级关系
    COMMUNICATION = "comm"  # 通信关系
    TEMPORAL = "temporal"  # 时序关系
    CAUSAL = "causal"  # 因果关系

class RelationStrength(Enum):
    """关系强度等级"""

    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CRITICAL = 4
    CORE = 5

@dataclass
class Entity:
    """实体定义"""

    entity_id: str
    entity_type: str = "default"
    name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "attributes": self.attributes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }

@dataclass
class Relation:
    """关系定义"""

    relation_id: str = ""
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.COLLABORATION
    strength: float = 0.5
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # 关系生存时间，None表示永久

    def __post_init__(self):
        if not self.relation_id:
            raw = f"{self.source_id}:{self.target_id}:{self.relation_type.value}:{self.created_at}"
            self.relation_id = hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl

    def to_dict(self) -> Dict:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "weight": self.weight,
            "attributes": self.attributes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ttl": self.ttl,
        }

@dataclass
class Community:
    """社区检测结果"""

    community_id: str = ""
    members: List[str] = field(default_factory=list)
    cohesion: float = 0.0
    density: float = 0.0
    central_entity: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "community_id": self.community_id,
            "members": self.members,
            "cohesion": self.cohesion,
            "density": self.density,
            "central_entity": self.central_entity,
            "detected_at": self.detected_at,
        }

# ============================================================
# 关系强度评估器
# ============================================================

class RelationStrengthEvaluator(object):
    """关系强度评估引擎 — 基于多因子加权模型"""

    # 默认因子权重
    DEFAULT_WEIGHTS = {
        "interaction_frequency": 0.25,
        "recency": 0.20,
        "mutual_connections": 0.15,
        "duration": 0.15,
        "interaction_diversity": 0.10,
        "response_latency": 0.10,
        "reciprocity": 0.05,
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()
        self._interaction_log: Dict[str, List[Dict]] = defaultdict(list)
        self._decay_half_life = 7 * 86400  # 7天衰减半衰期

    def _validate_weights(self):
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"权重总和为{total:.3f}，非标准值，已自动归一化")
            for k in self.weights:
                self.weights[k] /= total

    def record_interaction(
        self, source: str, target: str, interaction_type: str = "default", metadata: Optional[Dict] = None
    ):
        """记录一次交互事件"""
        event = {"timestamp": time.time(), "type": interaction_type, "metadata": metadata or {}}
        key = f"{source}->{target}"
        self._interaction_log[key].append(event)
        # 限制日志条目数防止内存溢出
        if len(self._interaction_log[key]) > 10000:
            self._interaction_log[key] = self._interaction_log[key][-5000:]
        # 记录反向交互用于互惠性评估
        rev_key = f"{target}->{source}"
        self._interaction_log[rev_key].append(
            {"timestamp": time.time(), "type": f"reverse_{interaction_type}", "metadata": {"original_key": key}}
        )

    def evaluate_strength(self, source: str, target: str) -> float:
        """评估两实体间关系强度 [0.0, 1.0]"""
        fwd_key = f"{source}->{target}"
        bwd_key = f"{target}->{source}"

        fwd_events = self._interaction_log.get(fwd_key, [])
        bwd_events = self._interaction_log.get(bwd_key, [])
        all_events = fwd_events + bwd_events

        if not all_events:
            return 0.0

        now = time.time()
        scores = {}

        # 1. 交互频率得分
        n_days = max(1, (now - min(e["timestamp"] for e in all_events)) / 86400)
        freq_score = min(1.0, len(fwd_events) / (n_days * 5))  # 每天5次为满分
        scores["interaction_frequency"] = freq_score

        # 2. 时效性得分（指数衰减）
        recent_hours = 168  # 最近7天
        recent_events = [e for e in fwd_events if now - e["timestamp"] < recent_hours * 3600]
        recency_score = min(1.0, len(recent_events) / 20)
        scores["recency"] = recency_score

        # 3. 共同连接数
        mutual = len(bwd_events)
        mutual_score = min(1.0, mutual / 10)
        scores["mutual_connections"] = mutual_score

        # 4. 持续时长
        duration_days = n_days
        duration_score = min(1.0, duration_days / 90)  # 90天满分
        scores["duration"] = duration_score

        # 5. 交互多样性
        types = set(e["type"] for e in fwd_events if not e["type"].startswith("reverse_"))
        diversity_score = min(1.0, len(types) / 5)
        scores["interaction_diversity"] = diversity_score

        # 6. 响应延迟
        response_pairs = self._find_response_pairs(fwd_events, bwd_events)
        if response_pairs:
            avg_latency = sum(lat for _, lat in response_pairs) / len(response_pairs)
            latency_score = max(0.0, 1.0 - avg_latency / 3600)  # 1小时内满分
        else:
            latency_score = 0.0
        scores["response_latency"] = latency_score

        # 7. 互惠性
        if len(fwd_events) > 0:
            reciprocity = min(1.0, len(bwd_events) / len(fwd_events))
        else:
            reciprocity = 0.0
        scores["reciprocity"] = reciprocity

        # 加权计算
        final_score = 0.0
        for factor, weight in self.weights.items():
            final_score += scores.get(factor, 0.0) * weight

        return round(min(1.0, max(0.0, final_score)), 4)

    def _find_response_pairs(self, fwd: List[Dict], bwd: List[Dict]) -> List[Tuple[float, float]]:
        """找到请求-响应对，返回 (请求时间, 响应延迟)"""
        pairs = []
        for f_event in fwd:
            for b_event in bwd:
                if b_event["timestamp"] > f_event["timestamp"]:
                    latency = b_event["timestamp"] - f_event["timestamp"]
                    if latency < 86400:  # 24小时内
                        pairs.append((f_event["timestamp"], latency))
                        break
        return pairs

    def batch_evaluate(self, pairs: List[Tuple[str, str]]) -> Dict[str, float]:
        """批量评估多对实体的关系强度"""
        results = {}
        for source, target in pairs:
            key = f"{source}:{target}"
            results[key] = self.evaluate_strength(source, target)
        return results

    def set_decay_half_life(self, seconds: float):
        """设置衰减半衰期"""
        self._decay_half_life = max(3600, seconds)  # 最小1小时
        logger.info(f"衰减半衰期设置为 {seconds / 3600:.1f} 小时")

# ============================================================
# 社区检测引擎
# ============================================================

class CommunityDetector(object):
    """社区检测引擎 — 基于标签传播算法"""

    def __init__(self, max_iterations: int = 100, convergence_threshold: float = 0.99):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

    def detect(self, entities: Dict[str, Entity], relations: Dict[str, Relation]) -> List[Community]:
        """执行社区检测，返回社区列表"""
        if not entities:
            return []

        # 构建邻接表
        adjacency: Dict[str, Dict[str, float]] = defaultdict(dict)
        for rel in relations.values():
            if rel.source_id in entities and rel.target_id in entities:
                adjacency[rel.source_id][rel.target_id] = rel.weight * rel.strength
                adjacency[rel.target_id][rel.source_id] = rel.weight * rel.strength

        # 初始化标签
        labels: Dict[str, str] = {eid: eid for eid in entities}

        for iteration in range(self.max_iterations):
            changed = 0
            entity_list = list(entities.keys())

            # 随机遍历顺序
            import random

            (entity_list)

            for eid in entity_list:
                neighbors = adjacency.get(eid, {})
                if not neighbors:
                    continue

                # 统计邻居标签频率（加权）
                label_scores: Dict[str, float] = defaultdict(float)
                for nid, weight in neighbors.items():
                    label = labels.get(nid, nid)
                    label_scores[label] += weight

                if label_scores:
                    best_label = max(label_scores, key=label_scores.get)
                    if labels[eid] != best_label:
                        labels[eid] = best_label
                        changed += 1

            # 检查收敛
            total = len(entities)
            stability = 1.0 - (changed / total) if total > 0 else 1.0
            if stability >= self.convergence_threshold:
                logger.info(f"社区检测在第{iteration + 1}轮收敛 (稳定性: {stability:.4f})")
                break

        # 构建社区结果
        groups: Dict[str, List[str]] = defaultdict(list)
        for eid, label in labels.items():
            groups[label].append(eid)

        communities = []
        for i, (label, members) in enumerate(groups.items()):
            if len(members) < 2:
                continue

            cohesion = self._calc_cohesion(members, adjacency)
            density = self._calc_density(members, adjacency)
            central = self._find_central_entity(members, adjacency)

            community = Community(
                community_id=f"comm_{i + 1}_{hashlib.md5(label.encode()).hexdigest()[:8]}",
                members=members,
                cohesion=cohesion,
                density=density,
                central_entity=central,
            )
            communities.append(community)

        # 按凝聚度排序
        communities.sort(key=lambda c: c.cohesion, reverse=True)
        logger.info(f"检测到 {len(communities)} 个社区")
        return communities

    def _calc_cohesion(self, members: List[str], adjacency: Dict[str, Dict[str, float]]) -> float:
        """计算社区凝聚度"""
        if len(members) < 2:
            return 0.0
        total_weight = 0.0
        edge_count = 0
        for i, m1 in enumerate(members):
            for m2 in members[i + 1 :]:
                w = adjacency.get(m1, {}).get(m2, 0.0)
                total_weight += w
                if w > 0:
                    edge_count += 1
        max_edges = len(members) * (len(members) - 1) / 2
        if max_edges == 0:
            return 0.0
        return round(total_weight / max_edges, 4)

    def _calc_density(self, members: List[str], adjacency: Dict[str, Dict[str, float]]) -> float:
        """计算社区密度"""
        if len(members) < 2:
            return 0.0
        edge_count = 0
        for i, m1 in enumerate(members):
            for m2 in members[i + 1 :]:
                if adjacency.get(m1, {}).get(m2, 0.0) > 0:
                    edge_count += 1
        max_edges = len(members) * (len(members) - 1) / 2
        return round(edge_count / max_edges, 4) if max_edges > 0 else 0.0

    def _find_central_entity(self, members: List[str], adjacency: Dict[str, Dict[str, float]]) -> str:
        """找到社区中心实体（度中心性最高）"""
        if not members:
            return ""
        scores = {}
        for m in members:
            scores[m] = sum(adjacency.get(m, {}).values())
        return max(scores, key=scores.get) if scores else members[0]

# ============================================================
class RelationGraphAnalyzer(object):
    """关系图谱分析器 - 计算关系网络的结构指标和演化趋势。

    企业场景：组织网络分析(ONA)、供应链依赖分析、社交关系挖掘。
    计算节点中心度、社区发现、桥接节点识别、关系衰减预测。
    """

    def __init__(self):
        self._adjacency: Dict[str, Dict[str, RelationStrength]] = defaultdict(dict)
        self._entity_attrs: Dict[str, Dict] = {}

    def add_relation(self, source: str, target: str, rel_type: RelationType, strength: RelationStrength):
        """添加关系边"""
        self._adjacency[source][target] = strength
        self._entity_attrs.setdefault(source, {"types": set()})["types"].add(rel_type.value)

    def degree_centrality(self) -> Dict[str, float]:
        """计算所有节点的度中心度"""
        if not self._adjacency:
            return {}
        n = len(self._adjacency)
        max_deg = n - 1
        return {node: len(neighbors) / max_deg for node, neighbors in self._adjacency.items()}

    def find_bridges(self) -> List[Dict]:
        """识别桥接节点 - 连接不同社区的枢纽"""
        bridges = []
        centrality = self.degree_centrality()
        for node, neighbors in self._adjacency.items():
            if len(neighbors) < 2:
                continue
            neighbor_degrees = [centrality.get(n, 0) for n in neighbors]
            avg_neighbor_deg = sum(neighbor_degrees) / len(neighbor_degrees)
            if centrality.get(node, 0) < avg_neighbor_deg * 0.5:
                bridges.append(
                    {
                        "node": node,
                        "connections": len(neighbors),
                        "betweenness_score": avg_neighbor_deg - centrality.get(node, 0),
                    }
                )
        return sorted(bridges, key=lambda b: b["betweenness_score"], reverse=True)

    def community_detect(self) -> List[List[str]]:
        """简单的标签传播社区发现"""
        labels = {node: node for node in self._adjacency}
        for _ in range(10):  # 最多迭代10轮
            changed = False
            for node in self._adjacency:
                if not self._adjacency[node]:
                    continue
                neighbor_labels = [labels[n] for n in self._adjacency[node] if n in labels]
                if not neighbor_labels:
                    continue
                from collections import Counter

                most_common = Counter(neighbor_labels).most_common(1)[0][0]
                if labels[node] != most_common:
                    labels[node] = most_common
                    changed = True
            if not changed:
                break
        communities = defaultdict(list)
        for node, label in labels.items():
            communities[label].append(node)
        return list(communities.values())

    def predict_decay(self, source: str, target: str, days: int = 30) -> Dict:
        """预测关系衰减概率 - 基于交互频率的时间衰减模型"""
        strength = self._adjacency.get(source, {}).get(target)
        if not strength:
            return {"probability": 1.0, "remaining_days": 0}
        base_rate = {
            RelationStrength.WEAK: 0.05,
            RelationStrength.MODERATE: 0.02,
            RelationStrength.STRONG: 0.005,
            RelationStrength.CRITICAL: 0.001,
            RelationStrength.CORE: 0.0,
        }
        daily_decay = base_rate.get(strength, 0.01)
        survival_prob = (1 - daily_decay) ** days
        return {"probability": 1 - survival_prob, "remaining_days": int(-1 / daily_decay * 0.1)}

# 主模块: AgentEros
# ============================================================

class AgentEros(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    Eros智能体 — 关系管理引擎

    功能:
    - 实体注册与管理
    - 多类型关系创建与维护
    - 关系强度动态评估
    - 社区发现与聚类
    - 关系路径搜索
    - 关系演化追踪
    - 关系风险评估
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(module_name="agent_eros", version="6.39.0", config=config)
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._source_index: Dict[str, Set[str]] = defaultdict(set)
        self._target_index: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[RelationType, Set[str]] = defaultdict(set)
        self._evaluator = RelationStrengthEvaluator()
        self._community_detector = CommunityDetector()
        self._communities: List[Community] = []
        self._community_cache_ts: float = 0
        self._community_cache_ttl: float = 300  # 5分钟缓存
        self._stats = {
            "total_entities_created": 0,
            "total_relations_created": 0,
            "total_relations_removed": 0,
            "total_strength_evaluations": 0,
            "total_community_detections": 0,
            "total_path_searches": 0,
        }

    async def initialize(self) -> None:
        """初始化模块"""
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentEros 关系管理引擎初始化完成")

    # ========================================================
    # 实体管理
    # ========================================================

    async def register_entity(
        self,
        entity_id: str,
        entity_type: str = "default",
        name: str = "",
        attributes: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Result:
        """注册新实体"""
        try:
            if entity_id in self._entities:
                return Result(success=False, message=f"实体 {entity_id} 已存在", data={"entity_id": entity_id})

            entity = Entity(
                entity_id=entity_id,
                entity_type=entity_type,
                name=name or entity_id,
                attributes=attributes or {},
                tags=tags or [],
            )
            self._entities[entity_id] = entity
            self._stats["total_entities_created"] += 1
            self._invalidate_community_cache()

            await self._audit_log("register_entity", f"注册实体: {entity_id} ({entity_type})")

            return Result(success=True, message="实体注册成功", data=entity.to_dict())

        except Exception as e:
            logger.error(f"注册实体失败: {e}")
            return Result(success=False, message=f"注册实体失败: {str(e)}")

    async def get_entity(self, entity_id: str) -> Result:
        """获取实体详情"""
        entity = self._entities.get(entity_id)
        if not entity:
            return Result(success=False, message=f"实体 {entity_id} 不存在")
        return Result(success=True, data=entity.to_dict())

    async def list_entities(
        self, entity_type: Optional[str] = None, tag: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> Result:
        """列出实体"""
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        if tag:
            entities = [e for e in entities if tag in e.tags]
        total = len(entities)
        page = entities[offset : offset + limit]
        return Result(
            success=True,
            data={"entities": [e.to_dict() for e in page], "total": total, "limit": limit, "offset": offset},
        )

    async def remove_entity(self, entity_id: str, cascade: bool = False) -> Result:
        """移除实体"""
        if entity_id not in self._entities:
            return Result(success=False, message=f"实体 {entity_id} 不存在")

        if cascade:
            # 级联删除关联关系
            rel_ids = list(self._source_index.get(entity_id, set())) + list(self._target_index.get(entity_id, set()))
            for rid in rel_ids:
                await self._remove_relation_internal(rid)

        del self._entities[entity_id]
        self._invalidate_community_cache()

        await self._audit_log("remove_entity", f"移除实体: {entity_id}, cascade={cascade}")
        return Result(success=True, message=f"实体 {entity_id} 已移除")

    # ========================================================
    # 关系管理
    # ========================================================

    async def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.COLLABORATION,
        strength: float = 0.5,
        weight: float = 1.0,
        attributes: Optional[Dict] = None,
        ttl: Optional[float] = None,
    ) -> Result:
        """创建关系"""
        try:
            if source_id not in self._entities:
                return Result(success=False, message=f"源实体 {source_id} 不存在")
            if target_id not in self._entities:
                return Result(success=False, message=f"目标实体 {target_id} 不存在")
            if source_id == target_id:
                return Result(success=False, message="不能创建自环关系")
            if not (0.0 <= strength <= 1.0):
                return Result(success=False, message="强度值必须在 [0.0, 1.0] 范围内")

            relation = Relation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                strength=strength,
                weight=weight,
                attributes=attributes or {},
                ttl=ttl,
            )

            self._relations[relation.relation_id] = relation
            self._source_index[source_id].add(relation.relation_id)
            self._target_index[target_id].add(relation.relation_id)
            self._type_index[relation_type].add(relation.relation_id)
            self._stats["total_relations_created"] += 1
            self._invalidate_community_cache()

            await self._audit_log("create_relation", f"创建关系: {source_id} -> {target_id} ({relation_type.value})")

            return Result(success=True, message="关系创建成功", data=relation.to_dict())

        except Exception as e:
            logger.error(f"创建关系失败: {e}")
            return Result(success=False, message=f"创建关系失败: {str(e)}")

    async def remove_relation(self, relation_id: str) -> Result:
        """移除关系"""
        return await self._remove_relation_internal(relation_id)

    async def _remove_relation_internal(self, relation_id: str) -> Result:
        """内部关系移除"""
        rel = self._relations.get(relation_id)
        if not rel:
            return Result(success=False, message=f"关系 {relation_id} 不存在")

        self._source_index.get(rel.source_id, set()).discard(relation_id)
        self._target_index.get(rel.target_id, set()).discard(relation_id)
        self._type_index.get(rel.relation_type, set()).discard(relation_id)
        del self._relations[relation_id]
        self._stats["total_relations_removed"] += 1
        self._invalidate_community_cache()
        return Result(success=True, message="关系已移除")

    async def update_relation_strength(
        self, relation_id: str, delta: float = 0.0, absolute: Optional[float] = None
    ) -> Result:
        """更新关系强度"""
        rel = self._relations.get(relation_id)
        if not rel:
            return Result(success=False, message=f"关系 {relation_id} 不存在")

        if absolute is not None:
            rel.strength = max(0.0, min(1.0, absolute))
        else:
            rel.strength = max(0.0, min(1.0, rel.strength + delta))

        rel.updated_at = time.time()

        await self._audit_log("update_strength", f"更新关系强度: {relation_id} -> {rel.strength:.4f}")

        return Result(success=True, data={"strength": rel.strength})

    async def get_entity_relations(
        self, entity_id: str, relation_type: Optional[RelationType] = None, direction: str = "both"
    ) -> Result:
        """获取实体的所有关系"""
        if entity_id not in self._entities:
            return Result(success=False, message=f"实体 {entity_id} 不存在")

        rel_ids = set()
        if direction in ("out", "both"):
            rel_ids.update(self._source_index.get(entity_id, set()))
        if direction in ("in", "both"):
            rel_ids.update(self._target_index.get(entity_id, set()))

        relations = [self._relations[rid] for rid in rel_ids if rid in self._relations]
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]

        # 过滤过期关系
        relations = [r for r in relations if not r.is_expired]

        return Result(success=True, data={"relations": [r.to_dict() for r in relations], "count": len(relations)})

    # ========================================================
    # 关系强度评估
    # ========================================================

    async def evaluate_relation_strength(self, source_id: str, target_id: str) -> Result:
        """评估两实体间关系强度"""
        strength = self._evaluator.evaluate_strength(source_id, target_id)
        self._stats["total_strength_evaluations"] += 1

        return Result(
            success=True,
            data={
                "source_id": source_id,
                "target_id": target_id,
                "strength": strength,
                "level": self._strength_to_level(strength),
            },
        )

    async def record_interaction(
        self, source_id: str, target_id: str, interaction_type: str = "default", metadata: Optional[Dict] = None
    ) -> Result:
        """记录交互事件"""
        self._evaluator.record_interaction(source_id, target_id, interaction_type, metadata)
        return Result(success=True, message="交互事件已记录")

    def _strength_to_level(self, strength: float) -> str:
        """将数值强度转为等级描述"""
        if strength >= 0.8:
            return "核心关系(CORE)"
        elif strength >= 0.6:
            return "关键关系(CRITICAL)"
        elif strength >= 0.4:
            return "强关系(STRONG)"
        elif strength >= 0.2:
            return "中等关系(MODERATE)"
        else:
            return "弱关系(WEAK)"

    # ========================================================
    # 路径搜索
    # ========================================================

    async def find_shortest_path(
        self, source_id: str, target_id: str, max_depth: int = 6, relation_types: Optional[List[RelationType]] = None
    ) -> Result:
        """BFS最短路径搜索"""
        if source_id not in self._entities or target_id not in self._entities:
            return Result(success=False, message="源或目标实体不存在")

        if source_id == target_id:
            return Result(success=True, data={"path": [source_id], "length": 0})

        self._stats["total_path_searches"] += 1
        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            # 获取邻居
            neighbors = set()
            for rid in self._source_index.get(current, set()):
                rel = self._relations.get(rid)
                if rel and not rel.is_expired:
                    if relation_types is None or rel.relation_type in relation_types:
                        neighbors.add(rel.target_id)
            for rid in self._target_index.get(current, set()):
                rel = self._relations.get(rid)
                if rel and not rel.is_expired:
                    if relation_types is None or rel.relation_type in relation_types:
                        neighbors.add(rel.source_id)

            for neighbor in neighbors:
                if neighbor == target_id:
                    final_path = path + [neighbor]
                    return Result(success=True, data={"path": final_path, "length": len(final_path) - 1})
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return Result(success=False, message=f"在深度{max_depth}内未找到路径")

    # ========================================================
    # 社区检测
    # ========================================================

    async def detect_communities(self, min_size: int = 2, force_refresh: bool = False) -> Result:
        """执行社区检测"""
        now = time.time()
        if not force_refresh and self._communities and now - self._community_cache_ts < self._community_cache_ttl:
            filtered = [c for c in self._communities if len(c.members) >= min_size]
            return Result(
                success=True,
                data={"communities": [c.to_dict() for c in filtered], "count": len(filtered), "cached": True},
            )

        self._communities = self._community_detector.detect(self._entities, self._relations)
        self._community_cache_ts = now
        self._stats["total_community_detections"] += 1

        filtered = [c for c in self._communities if len(c.members) >= min_size]

        await self._audit_log("detect_communities", f"检测到 {len(self._communities)} 个社区")

        return Result(
            success=True, data={"communities": [c.to_dict() for c in filtered], "count": len(filtered), "cached": False}
        )

    def _invalidate_community_cache(self):
        self._communities = []
        self._community_cache_ts = 0

    # ========================================================
    # 关系风险评估
    # ========================================================

    async def assess_risk(self, entity_id: str) -> Result:
        """评估实体关系风险"""
        if entity_id not in self._entities:
            return Result(success=False, message=f"实体 {entity_id} 不存在")

        out_rels = []
        for rid in self._source_index.get(entity_id, set()):
            rel = self._relations.get(rid)
            if rel and not rel.is_expired:
                out_rels.append(rel)

        in_rels = []
        for rid in self._target_index.get(entity_id, set()):
            rel = self._relations.get(rid)
            if rel and not rel.is_expired:
                in_rels.append(rel)

        all_rels = out_rels + in_rels

        if not all_rels:
            return Result(
                success=True,
                data={"entity_id": entity_id, "risk_level": "低", "risk_score": 0.0, "factors": {"isolated": True}},
            )

        risk_score = 0.0
        factors = {}

        # 孤立风险（出度+入度很少）
        factors["degree"] = len(all_rels)
        if len(all_rels) < 3:
            risk_score += 0.3
            factors["low_connectivity"] = True

        # 单点依赖风险
        critical_deps = [r for r in out_rels if r.strength >= 0.8]
        if len(critical_deps) > 0:
            risk_score += 0.2 * len(critical_deps)
            factors["critical_dependencies"] = len(critical_deps)

        # 竞争关系风险
        comp_rels = [r for r in all_rels if r.relation_type == RelationType.COMPETITION]
        if comp_rels:
            risk_score += 0.15 * len(comp_rels)
            factors["competition_count"] = len(comp_rels)

        # 过期关系比例
        expired_count = sum(
            1
            for rid in self._source_index.get(entity_id, set())
            if rid in self._relations and self._relations[rid].is_expired
        )
        total_count = len(self._source_index.get(entity_id, set()))
        if total_count > 0:
            expired_ratio = expired_count / total_count
            risk_score += 0.1 * expired_ratio
            factors["expired_ratio"] = round(expired_ratio, 3)

        risk_score = min(1.0, risk_score)
        if risk_score >= 0.7:
            risk_level = "高"
        elif risk_score >= 0.4:
            risk_level = "中"
        else:
            risk_level = "低"

        return Result(
            success=True,
            data={
                "entity_id": entity_id,
                "risk_level": risk_level,
                "risk_score": round(risk_score, 4),
                "factors": factors,
                "outgoing_relations": len(out_rels),
                "incoming_relations": len(in_rels),
            },
        )

    # ========================================================
    # 图统计
    # ========================================================

    async def get_graph_stats(self) -> Result:
        """获取关系图整体统计"""
        active_rels = [r for r in self._relations.values() if not r.is_expired]
        type_counts = defaultdict(int)
        for rel in active_rels:
            type_counts[rel.relation_type.value] += 1

        avg_strength = 0.0
        if active_rels:
            avg_strength = sum(r.strength for r in active_rels) / len(active_rels)

        # 度分布
        degree_dist: Dict[str, int] = {}
        for eid in self._entities:
            out = len(self._source_index.get(eid, set()))
            inn = len(self._target_index.get(eid, set()))
            degree_dist[eid] = out + inn

        max_degree = max(degree_dist.values()) if degree_dist else 0
        avg_degree = sum(degree_dist.values()) / len(degree_dist) if degree_dist else 0

        return Result(
            success=True,
            data={
                "total_entities": len(self._entities),
                "total_relations": len(self._relations),
                "active_relations": len(active_rels),
                "expired_relations": len(self._relations) - len(active_rels),
                "avg_strength": round(avg_strength, 4),
                "relation_type_distribution": dict(type_counts),
                "max_degree": max_degree,
                "avg_degree": round(avg_degree, 2),
                "communities_detected": len(self._communities),
            },
        )

    # ========================================================
    # 清理与维护
    # ========================================================

    async def cleanup_expired_relations(self) -> Result:
        """清理过期关系"""
        expired_ids = [rid for rid, rel in self._relations.items() if rel.is_expired]
        count = 0
        for rid in expired_ids:
            rel = self._relations[rid]
            self._source_index.get(rel.source_id, set()).discard(rid)
            self._target_index.get(rel.target_id, set()).discard(rid)
            self._type_index.get(rel.relation_type, set()).discard(rid)
            del self._relations[rid]
            count += 1

        if count > 0:
            self._invalidate_community_cache()
            await self._audit_log("cleanup_expired", f"清理 {count} 条过期关系")

        return Result(success=True, message=f"清理了 {count} 条过期关系")

    # ========================================================
    # 健康检查
    # ========================================================

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """统一执行入口 — 社交网络关系分析路由"""
        _ = self.trace("execute")
        metrics_collector.counter("agent_eros_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        if action == "health":
            hr = self.health_check()
            return hr.to_dict() if hasattr(hr, "to_dict") else {"status": "healthy"}
        elif action == "stats":
            return {
                "success": True,
                "result": {
                    "total_nodes": len(self._nodes) if hasattr(self, "_nodes") else 0,
                    "total_edges": len(self._edges) if hasattr(self, "_edges") else 0,
                },
            }
        return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> HealthReport:
        """健康检查"""
        checks = {}
        try:
            checks["entity_store"] = len(self._entities) >= 0
            checks["relation_store"] = len(self._relations) >= 0
            checks["evaluator"] = self._evaluator is not None
            checks["community_detector"] = self._community_detector is not None
            checks["index_consistency"] = self._validate_index_consistency()
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            return HealthReport(
                module_name=self.module_name,
                status=ModuleStatus.UNHEALTHY,
                checks=checks,
                message=f"健康检查异常: {str(e)}",
            )

        all_ok = all(checks.values())
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING if all_ok else ModuleStatus.DEGRADED,
            checks=checks,
            stats=ModuleStats(total_operations=sum(self._stats.values())),
        )

    def _validate_index_consistency(self) -> bool:
        """验证索引一致性"""
        for rid, rel in self._relations.items():
            if rid not in self._source_index.get(rel.source_id, set()):
                return False
            if rid not in self._target_index.get(rel.target_id, set()):
                return False
        return True

    async def get_module_stats(self) -> Result:
        """获取模块统计"""
        return Result(success=True, data=self._stats)

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_eros."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentEros
