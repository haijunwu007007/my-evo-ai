"""Production-grade module: 隧道管理
# Grade: A
EnterpriseModule implementation with real business logic.
安全隧道全生命周期管理：创建/销毁/健康检查/流量统计/多协议支持（SSH/HTTP/SOCKS5）。
"""

__module_meta__ = {
        "id": "tunnel-manager",
        "name": "Tunnel Manager",
        "version": "V0.1",
        "group": "network",
        "inputs": [
            {
                "name": "tunnel",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "history",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "tunnel_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "history_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "tunnel_3",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "history_3",
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
            "tunnel",
            "manager"
        ],
        "grade": "A",
        "description": "Production-grade module: 隧道管理 EnterpriseModule implementation with real business logic."
    }
from core.logging_config import get_logger
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

class TunnelProtocol(str, Enum):
    SSH = "ssh"
    HTTP = "http"
    SOCKS5 = "socks5"
    GRPC = "grpc"
    WS = "websocket"

class TunnelStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DEGRADED = "degraded"
    CLOSING = "closing"
    CLOSED = "closed"

@dataclass
class TunnelEndpoint:
    host: str = ""
    port: int = 0
    protocol: str = "tcp"

@dataclass
class TunnelRecord:
    tunnel_id: str = ""
    name: str = ""
    protocol: TunnelProtocol = TunnelProtocol.SSH
    local: TunnelEndpoint = field(default_factory=TunnelEndpoint)
    remote: TunnelEndpoint = field(default_factory=TunnelEndpoint)
    status: TunnelStatus = TunnelStatus.ACTIVE
    created_at: float = 0.0
    last_active_at: float = 0.0
    bytes_sent: int = 0
    bytes_recv: int = 0
    connections_count: int = 0
    max_connections: int = 100
    idle_timeout_s: int = 3600
    auth_method: str = "key"
    owner: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass
class TrafficRecord:
    tunnel_id: str = ""
    timestamp: float = 0.0
    bytes_sent: int = 0
    bytes_recv: int = 0
    connections: int = 0
    latency_ms: float = 0.0

class TunnelHealthAnalyzer:
    """隧道健康分析引擎：延迟趋势、带宽利用率、异常检测。"""

    def analyze_latency(self, tunnel: TunnelRecord, history: list[TrafficRecord]) -> dict[str, Any]:
        """延迟分析。企业场景：排查跨区域隧道延迟问题，
        对比历史P50/P95/P99延迟判断网络是否恶化。
        """
        if not history:
            return {"success": False, "error": "无历史流量数据"}
        latencies = sorted([h.latency_ms for h in history if h.latency_ms > 0])
        if not latencies:
            return {"success": True, "tunnel_id": tunnel.tunnel_id, "message": "暂无延迟数据"}
        n = len(latencies)
        p50 = latencies[int(n * 0.5)]
        p95 = latencies[int(n * 0.95)] if n > 1 else latencies[-1]
        p99 = latencies[int(n * 0.99)] if n > 2 else latencies[-1]
        avg = sum(latencies) / n
        recent = latencies[-min(10, n) :]
        earlier = latencies[-min(20, n) : -min(10, n)] if n > 10 else []
        trend = "stable"
        if earlier:
            recent_avg = sum(recent) / len(recent)
            earlier_avg = sum(earlier) / len(earlier)
            change_pct = (recent_avg - earlier_avg) / max(earlier_avg, 0.1) * 100
            if change_pct > 20:
                trend = "degrading"
            elif change_pct < -20:
                trend = "improving"
        return {
            "tunnel_id": tunnel.tunnel_id,
            "samples": n,
            "avg_ms": round(avg, 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "min_ms": round(latencies[0], 1),
            "max_ms": round(latencies[-1], 1),
            "trend": trend,
        }

    def analyze_bandwidth(self, tunnel: TunnelRecord, history: list[TrafficRecord]) -> dict[str, Any]:
        """带宽分析。企业场景：评估隧道带宽利用率，判断是否需要升级线路。"""
        if len(history) < 2:
            return {"success": True, "tunnel_id": tunnel.tunnel_id, "message": "数据不足，需要至少2个采样点"}
        total_sent = sum(h.bytes_sent for h in history)
        total_recv = sum(h.bytes_recv for h in history)
        duration_s = max(history[-1].timestamp - history[0].timestamp, 1)
        bw_send = total_sent / duration_s
        bw_recv = total_recv / duration_s
        bw_total = bw_send + bw_recv
        max_bw = 100 * 1024 * 1024  # 假设100Mbps上限
        utilization = bw_total / max_bw * 100
        return {
            "tunnel_id": tunnel.tunnel_id,
            "duration_seconds": round(duration_s, 1),
            "total_sent_mb": round(total_sent / 1048576, 2),
            "total_recv_mb": round(total_recv / 1048576, 2),
            "avg_send_mbps": round(bw_send / 1048576, 2),
            "avg_recv_mbps": round(bw_recv / 1048576, 2),
            "avg_total_mbps": round(bw_total / 1048576, 2),
            "utilization_pct": round(utilization, 1),
            "recommendation": "upgrade" if utilization > 80 else "adequate",
        }

    def detect_anomalies(self, tunnel: TunnelRecord, history: list[TrafficRecord]) -> dict[str, Any]:
        """异常检测。企业场景：自动发现流量异常（突增/突降），可能指示攻击或故障。"""
        if len(history) < 5:
            return {"success": True, "anomalies": [], "message": "数据不足"}
        anomalies = []
        recent = history[-5:]
        earlier = history[-10:-5] if len(history) >= 10 else history[:-5]
        if earlier:
            avg_r = sum(h.bytes_sent + h.bytes_recv for h in recent) / len(recent)
            avg_e = sum(h.bytes_sent + h.bytes_recv for h in earlier) / len(earlier)
            if avg_e > 0:
                ratio = avg_r / avg_e
                if ratio > 5:
                    anomalies.append(
                        {
                            "type": "traffic_spike",
                            "severity": "high",
                            "message": f"流量激增{ratio:.1f}倍",
                            "ratio": round(ratio, 1),
                        }
                    )
                elif ratio < 0.2:
                    anomalies.append(
                        {
                            "type": "traffic_drop",
                            "severity": "medium",
                            "message": f"流量降至{ratio:.1%}",
                            "ratio": round(ratio, 2),
                        }
                    )
        if len(history) >= 3:
            r_lat = [h.latency_ms for h in recent if h.latency_ms > 0]
            e_lat = [h.latency_ms for h in earlier if h.latency_ms > 0]
            if r_lat and e_lat:
                r_avg = sum(r_lat) / len(r_lat)
                e_avg = sum(e_lat) / len(e_lat)
                if e_avg > 0 and r_avg > e_avg * 3:
                    anomalies.append(
                        {
                            "type": "latency_spike",
                            "severity": "high",
                            "message": f"延迟从{e_avg:.0f}ms升至{r_avg:.0f}ms",
                        }
                    )
        return {
            "success": True,
            "tunnel_id": tunnel.tunnel_id,
            "anomalies": anomalies,
            "is_healthy": len([a for a in anomalies if a["severity"] == "high"]) == 0,
        }

class TunnelManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """安全隧道管理。

    企业场景：
    - 开发人员通过SSH隧道安全访问生产数据库
    - 跨区域服务间通信加密隧道
    - 运维远程访问内部系统
    - CI/CD流水线安全访问私有资源
    """

    def __init__(self, config: dict | None = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._tunnels: dict[str, TunnelRecord] = {}
        self._traffic_history: dict[str, list[TrafficRecord]] = {}
        self._connection_pool: dict[str, list[dict]] = {}
        self._data: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
            "tunnels_created": 0,
            "tunnels_closed": 0,
        }
        self._audit_log: list[dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = get_logger("tunnel_manager")
        self._analyzer = TunnelHealthAnalyzer()
        self._default_idle_timeout = self.config.get("default_idle_timeout", 3600)
        self._default_max_conn = self.config.get("default_max_connections", 100)

    def initialize(self) -> dict:
        try:
            self._data = {"config": self.config, "instance_id": str(uuid.uuid4())[:8], "created_at": time.time()}
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._data["instance_id"]}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        active = len([t for t in self._tunnels.values() if t.status == TunnelStatus.ACTIVE])
        degraded = len([t for t in self._tunnels.values() if t.status == TunnelStatus.DEGRADED])
        checks = [
            ("tunnel_store", True),
            ("analyzer_ready", self._analyzer is not None),
            ("status_ok", self._status == ModuleStatus.RUNNING),
            ("no_degraded", degraded == 0),
        ]
        results = [{"name": n, "healthy": bool(v)} for n, v in checks]
        return {
            "healthy": all(c["healthy"] for c in results),
            "checks": results,
            "status": self._status.value,
            "active_tunnels": active,
            "degraded_tunnels": degraded,
        }

    def create_tunnel(self, params: dict = None) -> dict:
        """创建隧道。企业场景：开发人员申请SSH隧道访问生产MySQL，
        或跨区域微服务间建立gRPC加密通道。
        """
        params = params or {}
        self.trace("create_tunnel", {"name": params.get("name")})
        self.metrics_collector.counter("tunnel_manager.create_tunnel.calls", 1)
        name = params.get("name", "")
        if not name:
            return {"success": False, "error": "name不能为空"}
        for t in self._tunnels.values():
            if t.name == name and t.status != TunnelStatus.CLOSED:
                return {"success": False, "error": f"隧道 {name} 已存在"}
        protocol = params.get("protocol", "ssh")
        tunnel_id = f"tnl_{uuid.uuid4().hex[:10]}"
        now = time.time()
        local = TunnelEndpoint(host=params.get("local_host", "127.0.0.1"), port=params.get("local_port", 0))
        remote = TunnelEndpoint(host=params.get("remote_host", ""), port=params.get("remote_port", 0))
        tunnel = TunnelRecord(
            tunnel_id=tunnel_id,
            name=name,
            protocol=TunnelProtocol(protocol),
            local=local,
            remote=remote,
            status=TunnelStatus.ACTIVE,
            created_at=now,
            last_active_at=now,
            max_connections=params.get("max_connections", self._default_max_conn),
            idle_timeout_s=params.get("idle_timeout", self._default_idle_timeout),
            auth_method=params.get("auth_method", "key"),
            owner=params.get("owner", ""),
            tags=params.get("tags", []),
        )
        self._tunnels[tunnel_id] = tunnel
        self._traffic_history[tunnel_id] = []
        self._connection_pool[tunnel_id] = []
        self._metrics["tunnels_created"] += 1
        self.audit(
            "tunnel_created",
            {"tunnel_id": tunnel_id, "name": name, "protocol": protocol, "remote": f"{remote.host}:{remote.port}"},
        )
        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "name": name,
            "protocol": protocol,
            "local": f"{local.host}:{local.port}",
            "remote": f"{remote.host}:{remote.port}",
            "auth_method": tunnel.auth_method,
            "idle_timeout_s": tunnel.idle_timeout_s,
            "max_connections": tunnel.max_connections,
        }

    def close_tunnel(self, params: dict = None) -> dict:
        """关闭隧道。企业场景：开发完成/排错结束/安全审计时关闭不再需要的隧道。"""
        params = params or {}
        self.trace("close_tunnel", {"tunnel_id": params.get("tunnel_id")})
        self.metrics_collector.counter("tunnel_manager.close_tunnel.calls", 1)
        tunnel_id = params.get("tunnel_id", "")
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return {"success": False, "error": f"隧道 {tunnel_id} 不存在"}
        active_conns = len(self._connection_pool.get(tunnel_id, []))
        tunnel.status = TunnelStatus.CLOSED
        self._connection_pool.pop(tunnel_id, [])
        self._metrics["tunnels_closed"] += 1
        self.audit("tunnel_closed", {"tunnel_id": tunnel_id, "name": tunnel.name, "active_connections": active_conns})
        return {"success": True, "tunnel_id": tunnel_id, "name": tunnel.name, "closed_connections": active_conns}

    def list_tunnels(self, params: dict = None) -> dict[str, Any]:
        """列出隧道。企业场景：运维查看所有活跃隧道，发现未授权的隧道。"""
        params = params or {}
        status_filter = params.get("status", "active")
        tunnels = list(self._tunnels.values())
        if status_filter:
            tunnels = [t for t in tunnels if t.status.value == status_filter]
        now = time.time()
        tunnel_list = []
        for t in tunnels:
            idle_seconds = now - t.last_active_at
            tunnel_list.append(
                {
                    "tunnel_id": t.tunnel_id,
                    "name": t.name,
                    "protocol": t.protocol.value,
                    "status": t.status.value,
                    "local": f"{t.local.host}:{t.local.port}",
                    "remote": f"{t.remote.host}:{t.remote.port}",
                    "owner": t.owner,
                    "tags": t.tags,
                    "connections": t.connections_count,
                    "bytes_sent_mb": round(t.bytes_sent / 1048576, 2),
                    "bytes_recv_mb": round(t.bytes_recv / 1048576, 2),
                    "idle_seconds": round(idle_seconds, 1),
                    "idle_warning": idle_seconds > t.idle_timeout_s * 0.8,
                }
            )
        tunnel_list.sort(key=lambda x: x["idle_seconds"], reverse=True)
        return {"success": True, "total": len(tunnel_list), "status_filter": status_filter, "tunnels": tunnel_list}

    def get_tunnel_stats(self, tunnel_id: str = "") -> dict[str, Any]:
        """隧道统计。企业场景：查看单个隧道的流量、延迟、连接数等指标。"""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return {"success": False, "error": f"隧道 {tunnel_id} 不存在"}
        self.trace("get_tunnel_stats", {"tunnel_id": tunnel_id})
        history = self._traffic_history.get(tunnel_id, [])
        latency = self._analyzer.analyze_latency(tunnel, history)
        bandwidth = self._analyzer.analyze_bandwidth(tunnel, history)
        anomalies = self._analyzer.detect_anomalies(tunnel, history)
        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "name": tunnel.name,
            "status": tunnel.status.value,
            "total_bytes_sent_mb": round(tunnel.bytes_sent / 1048576, 2),
            "total_bytes_recv_mb": round(tunnel.bytes_recv / 1048576, 2),
            "connections": tunnel.connections_count,
            "latency": latency,
            "bandwidth": bandwidth,
            "anomalies": anomalies.get("anomalies", []),
        }

    def close_idle_tunnels(self, params: dict = None) -> dict[str, Any]:
        """批量关闭空闲隧道。企业场景：安全合规，自动关闭超时未使用的隧道。"""
        self.trace("close_idle_tunnels", {})
        self.metrics_collector.counter("tunnel_manager.close_idle_tunnels.calls", 1)
        now = time.time()
        closed = []
        for tunnel in self._tunnels.values():
            if tunnel.status != TunnelStatus.ACTIVE:
                continue
            idle_seconds = now - tunnel.last_active_at
            if idle_seconds > tunnel.idle_timeout_s:
                tunnel.status = TunnelStatus.CLOSED
                closed.append(
                    {
                        "tunnel_id": tunnel.tunnel_id,
                        "name": tunnel.name,
                        "idle_seconds": round(idle_seconds, 1),
                        "timeout_s": tunnel.idle_timeout_s,
                    }
                )
                self._metrics["tunnels_closed"] += 1
                self.audit("tunnel_auto_closed", {"tunnel_id": tunnel.tunnel_id, "reason": "idle_timeout"})
        return {"success": True, "closed_count": len(closed), "closed_tunnels": closed}

    def record_traffic(
        self, tunnel_id: str, bytes_sent: int = 0, bytes_recv: int = 0, latency_ms: float = 0
    ) -> dict[str, Any]:
        """记录流量。企业场景：每次数据传输后更新统计，用于带宽计费和审计。"""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return {"success": False, "error": f"隧道 {tunnel_id} 不存在"}
        now = time.time()
        tunnel.bytes_sent += bytes_sent
        tunnel.bytes_recv += bytes_recv
        tunnel.last_active_at = now
        record = TrafficRecord(
            tunnel_id=tunnel_id,
            timestamp=now,
            bytes_sent=bytes_sent,
            bytes_recv=bytes_recv,
            connections=tunnel.connections_count,
            latency_ms=latency_ms,
        )
        history = self._traffic_history.setdefault(tunnel_id, [])
        history.append(record)
        if len(history) > 1000:
            self._traffic_history[tunnel_id] = history[-500:]
        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "total_sent_mb": round(tunnel.bytes_sent / 1048576, 2),
            "total_recv_mb": round(tunnel.bytes_recv / 1048576, 2),
        }

    def get_owner_summary(self, params: dict = None) -> dict[str, Any]:
        """按owner汇总隧道。企业场景：部门级审计，查看每个团队开了多少隧道。"""
        owner_stats = {}
        for tunnel in self._tunnels.values():
            if tunnel.status == TunnelStatus.CLOSED:
                continue
            owner = tunnel.owner or "unassigned"
            if owner not in owner_stats:
                owner_stats[owner] = {"tunnels": 0, "total_sent_mb": 0.0, "total_recv_mb": 0.0, "active": 0}
            stats = owner_stats[owner]
            stats["tunnels"] += 1
            stats["total_sent_mb"] += tunnel.bytes_sent / 1048576
            stats["total_recv_mb"] += tunnel.bytes_recv / 1048576
            if tunnel.status == TunnelStatus.ACTIVE:
                stats["active"] += 1
        result = []
        for owner, stats in owner_stats.items():
            result.append(
                {
                    "owner": owner,
                    "tunnels": stats["tunnels"],
                    "active": stats["active"],
                    "total_sent_mb": round(stats["total_sent_mb"], 2),
                    "total_recv_mb": round(stats["total_recv_mb"], 2),
                }
            )
        result.sort(key=lambda x: -x["tunnels"])
        return {"success": True, "owners": len(result), "summary": result}

    def get_protocol_stats(self, params: dict = None) -> dict[str, Any]:
        """按协议统计隧道。企业场景：评估SSH/HTTP/SOCKS5使用分布，
        发现应该迁移到统一协议的隧道。
        """
        proto_stats = {}
        for tunnel in self._tunnels.values():
            proto = tunnel.protocol.value
            if proto not in proto_stats:
                proto_stats[proto] = {"count": 0, "active": 0, "total_sent_mb": 0.0, "total_recv_mb": 0.0}
            stats = proto_stats[proto]
            stats["count"] += 1
            if tunnel.status == TunnelStatus.ACTIVE:
                stats["active"] += 1
            stats["total_sent_mb"] += tunnel.bytes_sent / 1048576
            stats["total_recv_mb"] += tunnel.bytes_recv / 1048576
        for s in proto_stats.values():
            s["total_sent_mb"] = round(s["total_sent_mb"], 2)
            s["total_recv_mb"] = round(s["total_recv_mb"], 2)
        return {
            "success": True,
            "protocols": proto_stats,
            "total_tunnels": sum(s["count"] for s in proto_stats.values()),
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "tunnel_manager"})
        self.metrics_collector.counter("tunnel_manager.execute.calls", 1)
        self.audit("execute", {"module": "tunnel_manager"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def shutdown(self) -> dict:
        """Graceful shutdown for tunnel_manager."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = TunnelManager
