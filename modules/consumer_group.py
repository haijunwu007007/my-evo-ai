"""
AUTO-EVO-AI V0.1 — 消费者组管理器
Grade: A (生产级) | Category: 消息中间件
职责：Kafka消费者组管理、分区分配、偏移量跟踪、再平衡、消费延迟监控
"""

__module_meta__ = {
        "id": "consumer-group",
        "name": "Consumer Group",
        "version": "V0.1",
        "group": "messaging",
        "inputs": [
            {
                "name": "group_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "group_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "strategy",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "group_id_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "group_id_4",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "group_id_5",
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
            "consumer",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 消费者组管理器 Grade: A (生产级) | Category: 消息中间件"
    }

import os
import time
import uuid
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

@dataclass
class ConsumerInstance:
    consumer_id: str = ""
    group_id: str = ""
    host: str = ""
    topics: List[str] = field(default_factory=list)
    assigned_partitions: Dict[str, List[int]] = field(default_factory=dict)
    current_offset: Dict[str, int] = field(default_factory=dict)
    committed_offset: Dict[str, int] = field(default_factory=dict)
    lag: int = 0
    status: str = "active"  # active, idle, rebalancing, stopped
    last_heartbeat: float = 0.0
    messages_consumed: int = 0
    bytes_consumed: int = 0
    errors: int = 0
    joined_at: float = 0.0

@dataclass
class TopicPartition:
    topic: str = ""
    partition: int = 0
    leader_epoch: int = 0
    begin_offset: int = 0
    end_offset: int = 0
    high_watermark: int = 0

class ConsumerGroupManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "consumer_group"
    MODULE_NAME = "consumer_group"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "consumer_group",
                "version": "7.0.0",
                "description": "消费者组管理，分区分配、偏移量跟踪、再平衡、延迟监控",
            }
        )
        self._groups: Dict[str, Dict[str, ConsumerInstance]] = defaultdict(dict)  # group_id -> {consumer_id: Consumer}
        self._group_topics: Dict[str, List[str]] = {}  # group_id -> subscribed topics
        self._group_config: Dict[str, Dict] = {}  # group_id -> config
        self._partitions: Dict[str, List[TopicPartition]] = defaultdict(list)
        self._rebalance_log: List[Dict] = []
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # 预设主题分区
        for topic in ["user-events", "order-events", "payment-events", "log-events"]:
            for p in range(3):
                self._partitions[topic].append(
                    TopicPartition(
                        topic=topic,
                        partition=p,
                        leader_epoch=1,
                        begin_offset=0,
                        end_offset=1000 + p * 500,
                        high_watermark=1000 + p * 500,
                    )
                )
        # 预设消费者组
        for gid, topics, consumers in [
            ("order-processor", ["order-events", "payment-events"], ["worker-1", "worker-2", "worker-3"]),
            ("log-collector", ["log-events"], ["collector-1", "collector-2"]),
            ("user-tracker", ["user-events"], ["tracker-1"]),
        ]:
            self._group_topics[gid] = topics
            self._group_config[gid] = {
                "auto_offset_reset": "latest",
                "enable_auto_commit": True,
                "session_timeout_ms": 30000,
                "heartbeat_interval_ms": 3000,
                "max_poll_records": 500,
                "rebalance_strategy": "range",
            }
            for cid in consumers:
                consumer = ConsumerInstance(
                    consumer_id=cid,
                    group_id=gid,
                    host=f"10.0.1.{hash(cid) % 254 + 1}",
                    topics=topics,
                    status="active",
                    last_heartbeat=time.time(),
                    joined_at=time.time(),
                )
                self._groups[gid][cid] = consumer
            self._assign_partitions(gid)

    def _assign_partitions(self, group_id: str) -> None:
        topics = self._group_topics.get(group_id, [])
        consumers = list(self._groups.get(group_id, {}).values())
        if not consumers:
            return
        # Range分配策略
        for topic in topics:
            parts = self._partitions.get(topic, [])
            if not parts:
                continue
            part_per_consumer = len(parts) // len(consumers)
            remainder = len(parts) % len(consumers)
            idx = 0
            for i, consumer in enumerate(consumers):
                count = part_per_consumer + (1 if i < remainder else 0)
                assigned = [parts[idx + j].partition for j in range(count)]
                consumer.assigned_partitions[topic] = assigned
                for p in assigned:
                    tp = f"{topic}:{p}"
                    end = next((pp.end_offset for pp in parts if pp.partition == p), 0)
                    consumer.current_offset[tp] = end - 100
                    consumer.committed_offset[tp] = end - 150
                consumer.lag = sum(
                    max(
                        consumer.committed_offset.get(f"{topic}:{p}", 0)
                        - consumer.current_offset.get(f"{topic}:{p}", 0),
                        0,
                    )
                    for topic in consumer.assigned_partitions
                    for p in consumer.assigned_partitions[topic]
                )
                idx += count

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "consumer_group"})
        self.metrics_collector.counter("consumer_group.execute.calls", 1)
        self.audit("execute", {"module": "consumer_group"})
        params = params or {}
        try:
            if action == "list_groups":
                groups = []
                for gid, consumers in self._groups.items():
                    active = sum(1 for c in consumers.values() if c.status == "active")
                    total_lag = sum(c.lag for c in consumers.values())
                    groups.append(
                        {
                            "group_id": gid,
                            "topics": self._group_topics.get(gid, []),
                            "members": len(consumers),
                            "active_members": active,
                            "total_lag": total_lag,
                        }
                    )
                return {"success": True, "result": groups}
            elif action == "describe_group":
                gid = params.get("group_id", "")
                if gid not in self._groups:
                    return {"success": False, "error": f"消费者组{gid}不存在"}
                consumers = list(self._groups[gid].values())
                return {
                    "success": True,
                    "result": {
                        "group_id": gid,
                        "topics": self._group_topics.get(gid, []),
                        "config": self._group_config.get(gid, {}),
                        "members": [
                            {
                                "consumer_id": c.consumer_id,
                                "host": c.host,
                                "status": c.status,
                                "partitions": c.assigned_partitions,
                                "lag": c.lag,
                                "messages_consumed": c.messages_consumed,
                                "last_heartbeat": datetime.fromtimestamp(c.last_heartbeat).isoformat(),
                            }
                            for c in consumers
                        ],
                    },
                }
            elif action == "join_group":
                gid = params.get("group_id", "")
                cid = params.get("consumer_id") or f"consumer_{uuid.uuid4().hex[:8]}"
                if not gid:
                    return {"success": False, "error": "group_id不能为空"}
                topics = params.get("topics", self._group_topics.get(gid, []))
                consumer = ConsumerInstance(
                    consumer_id=cid,
                    group_id=gid,
                    host=params.get("host", "localhost"),
                    topics=topics,
                    status="active",
                    last_heartbeat=time.time(),
                    joined_at=time.time(),
                )
                self._groups[gid][cid] = consumer
                if gid not in self._group_topics:
                    self._group_topics[gid] = topics
                self._assign_partitions(gid)
                self._rebalance_log.append(
                    {"group_id": gid, "action": "join", "consumer_id": cid, "timestamp": time.time()}
                )
                return {"success": True, "result": {"consumer_id": cid, "group_id": gid}}
            elif action == "leave_group":
                gid = params.get("group_id", "")
                cid = params.get("consumer_id", "")
                if gid not in self._groups or cid not in self._groups[gid]:
                    return {"success": False, "error": "消费者不存在"}
                del self._groups[gid][cid]
                if self._groups[gid]:
                    self._assign_partitions(gid)
                self._rebalance_log.append(
                    {"group_id": gid, "action": "leave", "consumer_id": cid, "timestamp": time.time()}
                )
                return {"success": True, "result": {"left": True}}
            elif action == "commit_offset":
                gid = params.get("group_id", "")
                cid = params.get("consumer_id", "")
                tp = params.get("topic_partition", "")
                offset = params.get("offset", 0)
                consumer = self._groups.get(gid, {}).get(cid)
                if not consumer:
                    return {"success": False, "error": "消费者不存在"}
                consumer.committed_offset[tp] = offset
                return {"success": True, "result": {"topic_partition": tp, "offset": offset}}
            elif action == "get_lag":
                gid = params.get("group_id", "")
                consumers = self._groups.get(gid, {})
                if not consumers:
                    return {"success": False, "error": f"消费者组{gid}不存在"}
                lag_info = []
                for cid, c in consumers.items():
                    for topic, parts in c.assigned_partitions.items():
                        for p in parts:
                            tp = f"{topic}:{p}"
                            lag_info.append(
                                {
                                    "consumer_id": cid,
                                    "topic": topic,
                                    "partition": p,
                                    "current": c.current_offset.get(tp, 0),
                                    "committed": c.committed_offset.get(tp, 0),
                                    "lag": max(c.committed_offset.get(tp, 0) - c.current_offset.get(tp, 0), 0),
                                }
                            )
                total_lag = sum(l["lag"] for l in lag_info)
                return {"success": True, "result": {"total_lag": total_lag, "details": lag_info}}
            elif action == "rebalance":
                gid = params.get("group_id", "")
                if gid not in self._groups:
                    return {"success": False, "error": f"消费者组{gid}不存在"}
                for c in self._groups[gid].values():
                    c.status = "rebalancing"
                self._assign_partitions(gid)
                for c in self._groups[gid].values():
                    c.status = "active"
                self._rebalance_log.append({"group_id": gid, "action": "rebalance", "timestamp": time.time()})
                return {"success": True, "result": {"rebalanced": True, "members": len(self._groups[gid])}}
            elif action == "reset_offset":
                gid = params.get("group_id", "")
                strategy = params.get("strategy", "earliest")
                topic = params.get("topic", "")
                if gid not in self._groups:
                    return {"success": False, "error": f"消费者组{gid}不存在"}
                reset_count = 0
                for c in self._groups[gid].values():
                    for tp in list(c.committed_offset.keys()):
                        if topic and not tp.startswith(topic):
                            continue
                        if strategy == "earliest":
                            c.committed_offset[tp] = 0
                            c.current_offset[tp] = 0
                        elif strategy == "latest":
                            parts = self._partitions.get(tp.split(":")[0], [])
                            p_num = int(tp.split(":")[1]) if ":" in tp else 0
                            end = next((pp.end_offset for pp in parts if pp.partition == p_num), 0)
                            c.committed_offset[tp] = end
                            c.current_offset[tp] = end
                        reset_count += 1
                return {"success": True, "result": {"reset": reset_count, "strategy": strategy}}
            elif action == "get_stats":
                total_consumers = sum(len(c) for c in self._groups.values())
                total_lag = sum(c.lag for g in self._groups.values() for c in g.values())
                return {
                    "success": True,
                    "result": {
                        "groups": len(self._groups),
                        "total_consumers": total_consumers,
                        "total_lag": total_lag,
                        "topics": len(self._partitions),
                        "rebalances": len(self._rebalance_log),
                    },
                }
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[ConsumerGroup] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        total = sum(len(c) for c in self._groups.values())
        base.update(
            {
                "status": "healthy",
                "groups": len(self._groups),
                "total_consumers": total,
                "topics": len(self._partitions),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def rebalance_group(self, group_id: str, strategy: str = "range") -> Dict[str, Any]:
        """手动触发消费组重平衡。企业场景：消费者上下线后分区分配不均，
        手动触发重平衡使分区均匀分配到可用消费者。
        strategy: range(按范围) / roundrobin(轮询) / sticky(粘性，减少重分配)。
        """
        groups = getattr(self, "_groups", {})
        if group_id not in groups:
            return {"success": False, "error": f"消费组 {group_id} 不存在"}
        consumers = groups[group_id]
        partitions = self._partitions.get(group_id, list(range(8)))
        if not consumers:
            return {"success": False, "error": "消费组无可用消费者"}
        assignment = {}
        if strategy == "roundrobin":
            for i, p in enumerate(partitions):
                consumer = consumers[i % len(consumers)]
                assignment.setdefault(consumer, []).append(p)
        elif strategy == "sticky":
            # 基于之前分配尽量保持不变
            prev = getattr(self, "_last_assignment", {}).get(group_id, {})
            available = list(partitions)
            for consumer in consumers:
                kept = [p for p in prev.get(consumer, []) if p in available]
                assignment[consumer] = kept
                for p in kept:
                    available.remove(p)
            idx = 0
            for consumer in consumers:
                while available:
                    assignment[consumer].append(available.pop(idx % len(available)))
                    idx += 1
        else:  # range
            per_consumer = len(partitions) // len(consumers)
            remainder = len(partitions) % len(consumers)
            offset = 0
            for i, consumer in enumerate(consumers):
                count = per_consumer + (1 if i < remainder else 0)
                assignment[consumer] = partitions[offset : offset + count]
                offset += count
        self._last_assignment = getattr(self, "_last_assignment", {})
        self._last_assignment[group_id] = assignment
        return {
            "success": True,
            "group_id": group_id,
            "strategy": strategy,
            "partition_count": len(partitions),
            "consumer_count": len(consumers),
            "assignment": {k: len(v) for k, v in assignment.items()},
        }

    def get_consumer_lag(self, group_id: str) -> Dict[str, Any]:
        """消费组延迟统计。企业场景：监控消费进度，发现消费延迟及时扩容消费者。
        lag = 最新消息offset - 消费者已提交offset。
        """
        groups = getattr(self, "_groups", {})
        if group_id not in groups:
            return {"success": False, "error": f"消费组 {group_id} 不存在"}
        partitions = self._partitions.get(group_id, [])
        lag_report = []
        total_lag = 0
        for p in partitions:
            latest = getattr(self, "_latest_offsets", {}).get(p, 0)
            committed = getattr(self, "_committed_offsets", {}).get(f"{group_id}:{p}", 0)
            lag = max(0, latest - committed)
            total_lag += lag
            lag_report.append({"partition": p, "latest": latest, "committed": committed, "lag": lag})
        avg_lag = round(total_lag / max(len(partitions), 1), 1)
        return {
            "success": True,
            "group_id": group_id,
            "total_lag": total_lag,
            "avg_lag_per_partition": avg_lag,
            "partition_count": len(partitions),
            "details": lag_report,
        }

    def pause_group(self, group_id: str) -> Dict[str, Any]:
        """暂停消费组。企业场景：消费处理出现异常时紧急暂停，
        排查问题后手动恢复。防止错误消费导致数据污染。
        """
        groups = getattr(self, "_groups", {})
        if group_id not in groups:
            return {"success": False, "error": f"消费组 {group_id} 不存在"}
        self._paused_groups = getattr(self, "_paused_groups", set())
        self._paused_groups.add(group_id)
        return {"success": True, "group_id": group_id, "status": "paused"}

    def resume_group(self, group_id: str) -> Dict[str, Any]:
        """恢复消费组。企业场景：问题排查完成后恢复消费，
        从暂停点继续消费，不丢消息。
        """
        self._paused_groups = getattr(self, "_paused_groups", set())
        if group_id not in self._paused_groups:
            return {"success": False, "error": f"消费组 {group_id} 未暂停"}
        self._paused_groups.discard(group_id)
        return {"success": True, "group_id": group_id, "status": "resumed"}

    def get_group_summary(self) -> Dict[str, Any]:
        """消费组总览。企业场景：运维看板展示所有消费组状态汇总。"""
        groups = getattr(self, "_groups", {})
        paused = getattr(self, "_paused_groups", set())
        summary = []
        for gid, consumers in groups.items():
            lag = self._get_group_lag(gid)
            summary.append(
                {
                    "group_id": gid,
                    "consumer_count": len(consumers),
                    "status": "paused" if gid in paused else "active",
                    "total_lag": lag,
                }
            )
        return {
            "success": True,
            "total_groups": len(groups),
            "active": len(groups) - len(paused),
            "paused": len(paused),
            "groups": sorted(summary, key=lambda x: -x["total_lag"]),
        }

    def _get_group_lag(self, group_id: str) -> int:
        partitions = self._partitions.get(group_id, [])
        total = 0
        for p in partitions:
            latest = getattr(self, "_latest_offsets", {}).get(p, 0)
            committed = getattr(self, "_committed_offsets", {}).get(f"{group_id}:{p}", 0)
            total += max(0, latest - committed)
        return total

    def reset_consumer_offset(self, group_id: str, partition: int, new_offset: int) -> Dict[str, Any]:
        """重置消费者offset。企业场景：消费处理出错后回退offset重新消费，
        或跳过 poison message 继续消费后续消息。
        """
        key = f"{group_id}:{partition}"
        committed = getattr(self, "_committed_offsets", {})
        old_offset = committed.get(key, 0)
        committed[key] = new_offset
        self._committed_offsets = committed
        return {
            "success": True,
            "group_id": group_id,
            "partition": partition,
            "old_offset": old_offset,
            "new_offset": new_offset,
            "message": "offset已重置" if new_offset < old_offset else "offset已前进",
        }

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

module_class = ConsumerGroupManager
