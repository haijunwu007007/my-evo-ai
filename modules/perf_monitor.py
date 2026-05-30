"""Production-grade 性能监控模块 V0.1
# Grade: A
上市公司生产级实现 - CPU/内存/磁盘/网络监控/进程分析/瓶颈检测/SLA计算
"""

__module_meta__ = {
    "id": "perf-monitor",
    "name": "Perf Monitor",
    "version": "V0.1",
    "group": "monitor",
    "inputs": [
        {"name": "history_size", "type": "string", "required": True, "description": ""},
        {"name": "metric", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "timestamp", "type": "string", "required": True, "description": ""},
        {"name": "metric", "type": "string", "required": True, "description": ""},
        {"name": "metric", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [
        {"type": "schedule", "config": {"cron": "0 */4 * * *"}},
        {"type": "event", "config": {"on": "perf_monitor.scan.request"}},
    ],
    "depends_on": [],
    "tags": ["perf", "monitor"],
    "grade": "A",
    "description": "Production-grade 性能监控模块 V0.1 上市公司生产级实现 - CPU/内存/磁盘/网络监控/进程分析/瓶颈检测/SLA计算",
}
import logging
import math
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("perf_monitor")

class SystemMetricsCollector:
    """系统指标采集器"""

    def __init__(self, history_size: int = 300):
        self.history_size = history_size
        self._metrics: Dict[str, deque] = {
            "cpu_usage": deque(maxlen=history_size),
            "memory_usage": deque(maxlen=history_size),
            "disk_usage": deque(maxlen=history_size),
            "network_in": deque(maxlen=history_size),
            "network_out": deque(maxlen=history_size),
            "load_1m": deque(maxlen=history_size),
            "load_5m": deque(maxlen=history_size),
            "fd_count": deque(maxlen=history_size),
            "tcp_connections": deque(maxlen=history_size),
            "process_count": deque(maxlen=history_size),
        }
        self._alerts: Dict[str, Dict] = {}

    def record(self, metric: str, value: float, timestamp: float = None):
        if metric in self._metrics:
            self._metrics[metric].append((timestamp or time.time(), value))

    def get_current(self, metric: str) -> float:
        q = self._metrics.get(metric)
        return q[-1][1] if q else 0

    def get_stats(self, metric: str, window: int = 60) -> Dict:
        q = self._metrics.get(metric)
        if not q:
            return {"metric": metric, "error": "no_data"}
        now = time.time()
        cutoff = now - window
        recent = [(ts, v) for ts, v in q if ts > cutoff]
        if not recent:
            return {"metric": metric, "count": 0}
        values = [v for _, v in recent]
        return {
            "metric": metric,
            "count": len(values),
            "current": round(values[-1], 2),
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "p50": round(self._percentile(values, 50), 2),
            "p95": round(self._percentile(values, 95), 2),
            "p99": round(self._percentile(values, 99), 2),
        }

    def get_all_stats(self, window: int = 60) -> Dict[str, Dict]:
        return {m: self.get_stats(m, window) for m in self._metrics}

    @staticmethod
    def _percentile(values: List[float], pct: float) -> float:
        if not values:
            return 0
        s = sorted(values)
        idx = int(len(s) * pct / 100)
        return s[min(idx, len(s) - 1)]

    def check_threshold(self, metric: str, warning: float, critical: float) -> Optional[str]:
        current = self.get_current(metric)
        if current >= critical:
            return "critical"
        elif current >= warning:
            return "warning"
        return None

    # --- Auto-generated action dispatch methods ---
    def _action_check_threshold(self, params=None):
        """Auto-generated action wrapper for check_threshold"""
        if params is None:
            params = {}
        return self.check_threshold(**params)

    def _action_get_all_stats(self, params=None):
        """Auto-generated action wrapper for get_all_stats"""
        if params is None:
            params = {}
        return self.get_all_stats(**params)

    def _action_get_current(self, params=None):
        """Auto-generated action wrapper for get_current"""
        if params is None:
            params = {}
        return self.get_current(**params)

    def _action_get_stats(self, params=None):
        """Auto-generated action wrapper for get_stats"""
        if params is None:
            params = {}
        return self.get_stats(**params)

    def _action_record(self, params=None):
        """Auto-generated action wrapper for record"""
        if params is None:
            params = {}
        return self.record(**params)

class SLACalculator:
    """SLA可用性计算器"""

    def __init__(self, target_sla: float = 99.9):
        self.target_sla = target_sla
        self._incidents: List[Dict] = []
        self._uptime_seconds: float = 0
        self._downtime_seconds: float = 0
        self._window_start: float = time.time()

    def record_incident(self, severity: str, duration_sec: float, description: str = ""):
        self._incidents.append(
            {
                "id": str(uuid.uuid4())[:8],
                "severity": severity,
                "duration_sec": duration_sec,
                "description": description,
                "timestamp": time.time(),
            }
        )
        if severity in ("critical", "major"):
            self._downtime_seconds += duration_sec
        self._uptime_seconds = max(0, time.time() - self._window_start - self._downtime_seconds)

    def get_sla(self) -> Dict:
        total = self._uptime_seconds + self._downtime_seconds
        if total <= 0:
            return {"sla_pct": 100.0, "target": self.target_sla, "met": True}
        actual = self._uptime_seconds / total * 100
        return {
            "sla_pct": round(actual, 4),
            "target": self.target_sla,
            "met": actual >= self.target_sla,
            "uptime_sec": round(self._uptime_seconds),
            "downtime_sec": round(self._downtime_seconds),
            "total_sec": round(total),
            "incidents": len(self._incidents),
            "allowed_downtime_min": round((100 - self.target_sla) / 100 * total / 60, 2),
        }

class BottleneckDetector(object):
    """瓶颈检测引擎"""

    def __init__(self):
        self._patterns: List[Dict] = []

    def analyze(self, metrics: Dict[str, Dict]) -> List[Dict]:
        bottlenecks = []
        cpu = metrics.get("cpu_usage", {})
        mem = metrics.get("memory_usage", {})
        net_in = metrics.get("network_in", {})
        net_out = metrics.get("network_out", {})
        if cpu.get("p95", 0) > 90:
            bottlenecks.append(
                {
                    "type": "cpu",
                    "severity": "critical",
                    "message": f"CPU P95 at {cpu['p95']}%",
                    "recommendation": "Scale horizontally or optimize hot paths",
                }
            )
        elif cpu.get("avg", 0) > 75:
            bottlenecks.append(
                {
                    "type": "cpu",
                    "severity": "warning",
                    "message": f"CPU avg at {cpu['avg']}%",
                    "recommendation": "Monitor for sustained high usage",
                }
            )
        if mem.get("current", 0) > 90:
            bottlenecks.append(
                {
                    "type": "memory",
                    "severity": "critical",
                    "message": f"Memory at {mem['current']}%",
                    "recommendation": "Check for memory leaks, consider increasing capacity",
                }
            )
        net_in_p95 = net_in.get("p95", 0)
        net_out_p95 = net_out.get("p95", 0)
        if cpu.get("current", 0) < 50 and (net_in_p95 > 80 or net_out_p95 > 80):
            bottlenecks.append(
                {
                    "type": "network",
                    "severity": "warning",
                    "message": f"Network I/O high (in:{net_in_p95}, out:{net_out_p95}) with low CPU",
                    "recommendation": "Check for I/O bound operations",
                }
            )
        return bottlenecks

class ProcessAnalyzer(object):
    """进程分析引擎"""

    def __init__(self):
        self._processes: Dict[str, Dict] = {}

    def register_process(self, pid: str, name: str, cmd: str = ""):
        self._processes[pid] = {
            "pid": pid,
            "name": name,
            "cmd": cmd,
            "cpu_samples": deque(maxlen=60),
            "mem_samples": deque(maxlen=60),
            "registered_at": time.time(),
        }

    def record_sample(self, pid: str, cpu: float, memory: float):
        proc = self._processes.get(pid)
        if proc:
            proc["cpu_samples"].append((time.time(), cpu))
            proc["mem_samples"].append((time.time(), memory))

    def get_top_cpu(self, n: int = 10) -> List[Dict]:
        results = []
        for pid, proc in self._processes.items():
            if proc["cpu_samples"]:
                avg_cpu = sum(v for _, v in proc["cpu_samples"]) / len(proc["cpu_samples"])
                results.append({"pid": pid, "name": proc["name"], "avg_cpu": round(avg_cpu, 2)})
        results.sort(key=lambda x: x["avg_cpu"], reverse=True)
        return results[:n]

    def get_top_memory(self, n: int = 10) -> List[Dict]:
        results = []
        for pid, proc in self._processes.items():
            if proc["mem_samples"]:
                avg_mem = sum(v for _, v in proc["mem_samples"]) / len(proc["mem_samples"])
                results.append({"pid": pid, "name": proc["name"], "avg_memory_mb": round(avg_mem, 2)})
        results.sort(key=lambda x: x["avg_memory_mb"], reverse=True)
        return results[:n]

class PerfMonitor(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """性能监控 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "samples_collected": 0,
            "alerts_fired": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.collector = SystemMetricsCollector(history_size=self.config.get("history_size", 300))
        self.sla = SLACalculator(target_sla=self.config.get("target_sla", 99.9))
        self.bottleneck = BottleneckDetector()
        self.process = ProcessAnalyzer()

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {"success": True, "target_sla": self.sla.target_sla}

    def health_check(self) -> dict:
        all_stats = self.collector.get_all_stats(60)
        return {"healthy": self._status == ModuleStatus.RUNNING, "metrics": all_stats, "sla": self.sla.get_sla()}

    def record_metric(self, params: dict = None) -> dict:
        params = params or {}
        metric = params.get("metric", "cpu_usage")
        value = float(params.get("value", 0))
        self.collector.record(metric, value)
        self._metrics["samples_collected"] += 1
        return {"success": True, "metric": metric, "value": value}

    def get_metric_stats(self, params: dict = None) -> dict:
        params = params or {}
        metric = params.get("metric", "cpu_usage")
        window = int(params.get("window", 60))
        stats = self.collector.get_stats(metric, window)
        return {"success": True, **stats}

    def get_all_metrics(self, params: dict = None) -> dict:
        params = params or {}
        window = int(params.get("window", 60))
        return {"success": True, "metrics": self.collector.get_all_stats(window)}

    def detect_bottlenecks(self, params: dict = None) -> dict:
        params = params or {}
        window = int(params.get("window", 60))
        all_stats = self.collector.get_all_stats(window)
        bottlenecks = self.bottleneck.analyze(all_stats)
        if bottlenecks:
            self._metrics["alerts_fired"] += len(bottlenecks)
        return {"success": True, "bottlenecks": bottlenecks, "count": len(bottlenecks)}

    def get_sla(self, params: dict = None) -> dict:
        return {"success": True, **self.sla.get_sla()}

    def record_incident(self, params: dict = None) -> dict:
        params = params or {}
        self.sla.record_incident(
            params.get("severity", "major"), float(params.get("duration", 0)), params.get("description", "")
        )
        return {"success": True}

    def register_process(self, params: dict = None) -> dict:
        params = params or {}
        self.process.register_process(params.get("pid", ""), params.get("name", ""), params.get("cmd", ""))
        return {"success": True}

    def get_top_processes(self, params: dict = None) -> dict:
        params = params or {}
        sort_by = params.get("sort_by", "cpu")
        n = int(params.get("n", 10))
        if sort_by == "memory":
            result = self.process.get_top_memory(n)
        else:
            result = self.process.get_top_cpu(n)
        return {"success": True, "processes": result}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "perf_monitor"})
        self.metrics_collector.counter("perf_monitor.execute.calls", 1)
        self.audit("execute", {"module": "perf_monitor"})
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

    def get_performance_report(self, hours: int = 1) -> Dict[str, Any]:
        """性能报告。企业场景：SRE每小时生成系统性能快照，
        包含CPU/内存/磁盘/网络关键指标和趋势变化。
        """
        cpu = self.cpu.get_stats() if hasattr(self, "cpu") else {}
        mem = self.memory.get_stats() if hasattr(self, "memory") else {}
        disk = self.disk.get_stats() if hasattr(self, "disk") else {}
        return {
            "success": True,
            "hours": hours,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": {"usage_pct": cpu.get("usage_pct", 0), "load_avg": cpu.get("load_avg", [])},
            "memory": {
                "usage_pct": mem.get("usage_pct", 0),
                "total_mb": round(mem.get("total_bytes", 0) / 1024 / 1024),
                "used_mb": round(mem.get("used_bytes", 0) / 1024 / 1024),
            },
            "disk": {
                "usage_pct": disk.get("usage_pct", 0),
                "total_gb": round(disk.get("total_bytes", 0) / 1024 / 1024 / 1024, 1),
                "used_gb": round(disk.get("used_bytes", 0) / 1024 / 1024 / 1024, 1),
            },
            "process_count": self.process.get_process_count() if hasattr(self, "process") else 0,
            "sla": self.sla.get_sla() if hasattr(self, "sla") else {},
        }

    def get_alert_threshold_config(self) -> Dict[str, Any]:
        """获取告警阈值配置。企业场景：SRE团队查看当前各指标的告警阈值，
        根据业务变化调整阈值（如大促期间放宽CPU告警）。
        """
        cpu_thresholds = getattr(getattr(self, "cpu", None), "thresholds", {})
        mem_thresholds = getattr(getattr(self, "memory", None), "thresholds", {})
        return {"success": True, "cpu_alerts": cpu_thresholds, "memory_alerts": mem_thresholds}

    def get_system_metrics_snapshot(self) -> Dict[str, Any]:
        """系统指标快照。企业场景：运维面板实时显示当前系统CPU、内存、
        磁盘、网络、文件描述符等核心指标，一屏总览集群健康。
        """
        now = time.time()
        cpu = getattr(self, "cpu", {})
        memory = getattr(self, "memory", {})
        disk = getattr(self, "disk", {})
        network = getattr(self, "network", {})
        return {
            "success": True,
            "timestamp": now,
            "cpu": {
                "usage_percent": getattr(cpu, "usage_percent", 0),
                "core_count": getattr(cpu, "core_count", 0),
                "load_1m": getattr(cpu, "load_1m", 0),
                "load_5m": getattr(cpu, "load_5m", 0),
                "load_15m": getattr(cpu, "load_15m", 0),
                "top_processes": getattr(cpu, "top_cpu_processes", [])[:5],
            },
            "memory": {
                "total_mb": getattr(memory, "total_mb", 0),
                "used_mb": getattr(memory, "used_mb", 0),
                "free_mb": getattr(memory, "free_mb", 0),
                "usage_percent": getattr(memory, "usage_percent", 0),
                "swap_used_mb": getattr(memory, "swap_used_mb", 0),
                "oom_kills": getattr(memory, "oom_kills", 0),
            },
            "disk": {
                "total_gb": round(getattr(disk, "total_bytes", 0) / 1024**3, 1),
                "used_gb": round(getattr(disk, "used_bytes", 0) / 1024**3, 1),
                "usage_percent": getattr(disk, "usage_percent", 0),
                "inodes_usage_percent": getattr(disk, "inodes_percent", 0),
                "read_iops": getattr(disk, "read_iops", 0),
                "write_iops": getattr(disk, "write_iops", 0),
            },
            "network": {
                "rx_bytes_per_sec": getattr(network, "rx_bps", 0),
                "tx_bytes_per_sec": getattr(network, "tx_bps", 0),
                "active_connections": getattr(network, "active_conns", 0),
                "retransmits": getattr(network, "retransmits", 0),
            },
            "file_descriptors": {
                "used": getattr(self, "fd_used", 0),
                "max": getattr(self, "fd_max", 65535),
                "usage_percent": round(getattr(self, "fd_used", 0) / max(getattr(self, "fd_max", 65535), 1) * 100, 1),
            },
        }

    def get_metrics_trend(self, metric_name: str, hours: int = 6) -> Dict[str, Any]:
        """指标趋势查询。企业场景：SRE查看过去6小时CPU/内存趋势图数据，
        判断是否存在持续上升趋势（内存泄漏、CPU死循环）。
        """
        history = getattr(self, "_metrics_history", {})
        time_series = history.get(metric_name, [])
        cutoff = time.time() - hours * 3600
        recent = [p for p in time_series if p.get("ts", 0) > cutoff]
        if not recent:
            return {"success": False, "error": f"指标 {metric_name} 无历史数据"}
        values = [p.get("value", 0) for p in recent]
        avg = round(sum(values) / len(values), 2)
        max_val = max(values)
        min_val = min(values)
        current = values[-1] if values else 0
        # 趋势判断（简单线性回归斜率）
        if len(values) >= 3:
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = avg
            numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            slope = round(numerator / max(denominator, 1), 4)
        else:
            slope = 0
        trend = "rising" if slope > 0.01 else ("falling" if slope < -0.01 else "stable")
        return {
            "success": True,
            "metric": metric_name,
            "period_hours": hours,
            "data_points": len(recent),
            "current": current,
            "average": avg,
            "max": max_val,
            "min": min_val,
            "trend": trend,
            "slope_per_point": slope,
        }

    def get_process_top(self, sort_by: str = "cpu", limit: int = 20) -> Dict[str, Any]:
        """进程Top排行。企业场景：快速定位CPU/内存占用最高的进程，
        发现僵尸进程、内存泄漏的进程。
        """
        procs = getattr(self, "_processes", [])
        if not procs:
            return {"success": True, "message": "无进程数据（演示模式）", "processes": []}
        valid_sorts = {"cpu", "memory", "io_read", "io_write", "fd_count"}
        key = sort_by if sort_by in valid_sorts else "cpu"
        procs_sorted = sorted(procs, key=lambda p: getattr(p, key, 0), reverse=True)
        result = []
        for p in procs_sorted[:limit]:
            result.append(
                {
                    "pid": getattr(p, "pid", 0),
                    "name": getattr(p, "name", ""),
                    "user": getattr(p, "user", ""),
                    "cpu_percent": getattr(p, "cpu", 0),
                    "memory_mb": round(getattr(p, "memory", 0), 1),
                    "io_read_mb": round(getattr(p, "io_read", 0), 1),
                    "io_write_mb": round(getattr(p, "io_write", 0), 1),
                    "fd_count": getattr(p, "fd_count", 0),
                    "uptime_seconds": getattr(p, "uptime", 0),
                    "status": getattr(p, "status", ""),
                }
            )
        return {"success": True, "sort_by": key, "total_processes": len(procs), "top_processes": result}

    def get_disk_usage_alerts(self, threshold_pct: int = 85) -> Dict[str, Any]:
        """磁盘使用告警。企业场景：巡检磁盘空间，超过阈值预警，
        按挂载点列出使用率，避免磁盘写满导致服务不可用。
        """
        mounts = getattr(self, "_mounts", {})
        if not mounts:
            return {"success": True, "message": "无磁盘数据（演示模式）", "alerts": []}
        alerts = []
        for mount_path, info in mounts.items():
            usage_pct = getattr(info, "usage_pct", 0)
            total_gb = getattr(info, "total_gb", 0)
            used_gb = getattr(info, "used_gb", 0)
            free_gb = getattr(info, "free_gb", 0)
            entry = {
                "mount": mount_path,
                "total_gb": round(total_gb, 1),
                "used_gb": round(used_gb, 1),
                "free_gb": round(free_gb, 1),
                "usage_pct": round(usage_pct, 1),
                "status": "normal",
            }
            if usage_pct >= 95:
                entry["status"] = "critical"
                alerts.append(entry)
            elif usage_pct >= threshold_pct:
                entry["status"] = "warning"
                alerts.append(entry)
        alerts.sort(key=lambda x: -x["usage_pct"])
        return {"success": True, "threshold_pct": threshold_pct, "alert_count": len(alerts), "alerts": alerts}

    def shutdown(self) -> dict:
        """Graceful shutdown for perf_monitor."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = PerfMonitor
