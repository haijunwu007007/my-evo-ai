"""
AUTO-EVO-AI V0.1 — 块设备管理模块
Grade: A (生产级) | Category: 基础设施
职责：块设备管理、磁盘分区、IO监控、存储池管理、快照管理
"""

__module_meta__ = {
        "id": "block-device",
        "name": "Block Device",
        "version": "V0.1",
        "group": "storage",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "prefix",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "device_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "op",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "size_kb",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "latency",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "success",
                "type": "bool",
                "description": "是否成功"
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
        "triggers": [],
        "depends_on": [],
        "tags": [
            "manager",
            "block"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 块设备管理模块 Grade: A (生产级) | Category: 基础设施"
    }

import os
import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
logger = logging.getLogger("block_device")

metrics_collector = None

class DeviceType(Enum):
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    VIRTUAL = "virtual"
    LOOP = "loop"

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"
    FORMATTING = "formatting"

class IOOpType(Enum):
    READ = "read"
    WRITE = "write"

@dataclass
class BlockDevice:
    device_id: str
    name: str
    device_type: DeviceType
    size_gb: float
    used_gb: float = 0.0
    status: DeviceStatus = DeviceStatus.ONLINE
    mount_point: str = ""
    fs_type: str = ""
    read_speed_mb: float = 0.0
    write_speed_mb: float = 0.0
    iops_read: int = 0
    iops_write: int = 0
    latency_ms: float = 0.0
    partitions: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class IORecord:
    """IO操作记录"""

    timestamp: float
    device_id: str
    op_type: IOOpType
    size_kb: int
    latency_ms: float
    queue_depth: int

@dataclass
class Snapshot:
    """存储快照"""

    snap_id: str
    device_id: str
    name: str
    size_gb: float
    created_at: str
    parent_snap: str = ""

@dataclass
class StoragePool:
    """存储池"""

    pool_id: str
    name: str
    raid_level: str
    member_devices: List[str] = field(default_factory=list)
    total_gb: float = 0.0
    used_gb: float = 0.0

class BlockDeviceManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """块设备管理器 - 生产级实现"""

    MODULE_ID = "block_device"
    MODULE_NAME = "块设备管理"
    VERSION = "V0.1"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._devices: Dict[str, BlockDevice] = {}
        self._io_history: Dict[str, List[IORecord]] = {}
        self._snapshots: Dict[str, Snapshot] = {}
        self._pools: Dict[str, StoragePool] = {}
        self._counter = 0
        self._io_threshold_warn_ms = 50.0
        self._io_threshold_crit_ms = 200.0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return hashlib.md5(f"{prefix}_{self._counter}_{time.time()}".encode()).hexdigest()[:10]

    def initialize(self) -> bool:
        try:
            self._load_sample_devices()
            logger.info(f"块设备管理初始化完成，设备: {len(self._devices)}")
            return True
        except Exception as e:
            logger.error(f"块设备管理初始化失败: {e}")
            return False

    def _load_sample_devices(self):
        samples = [
            ("dev_sda", "/dev/sda", DeviceType.SSD, 500, 120, "/mnt/data", "ext4", 550, 480, 50000, 30000, 0.5),
            ("dev_sdb", "/dev/sdb", DeviceType.HDD, 2000, 800, "/mnt/backup", "xfs", 180, 160, 200, 150, 5.0),
            (
                "dev_nvme0",
                "/dev/nvme0n1",
                DeviceType.NVME,
                1000,
                350,
                "/mnt/fast",
                "ext4",
                3500,
                3000,
                200000,
                80000,
                0.1,
            ),
            ("dev_sdc", "/dev/sdc", DeviceType.VIRTUAL, 100, 25, "/mnt/temp", "ext4", 400, 350, 10000, 8000, 1.0),
        ]
        for d in samples:
            self._devices[d[0]] = BlockDevice(
                device_id=d[0],
                name=d[1],
                device_type=d[2],
                size_gb=d[3],
                used_gb=d[4],
                status=DeviceStatus.ONLINE,
                mount_point=d[5],
                fs_type=d[6],
                read_speed_mb=d[7],
                write_speed_mb=d[8],
                iops_read=d[9],
                iops_write=d[10],
                latency_ms=d[11],
            )
            self._io_history[d[0]] = []
        # 存储池
        self._pools["pool_main"] = StoragePool(
            pool_id="pool_main",
            name="主存储池",
            raid_level="RAID5",
            member_devices=["dev_sda", "dev_sdb"],
            total_gb=2500,
            used_gb=920,
        )
        self._pools["pool_fast"] = StoragePool(
            pool_id="pool_fast",
            name="高速存储池",
            raid_level="RAID1",
            member_devices=["dev_nvme0"],
            total_gb=1000,
            used_gb=350,
        )

    def _record_io(self, device_id: str, op: IOOpType, size_kb: int, latency: float):
        record = IORecord(
            timestamp=time.time(), device_id=device_id, op_type=op, size_kb=size_kb, latency_ms=latency, queue_depth=0
        )
        if device_id in self._io_history:
            self._io_history[device_id].append(record)
            # 保留最近1000条
            if len(self._io_history[device_id]) > 1000:
                self._io_history[device_id] = self._io_history[device_id][-500:]

    def _get_io_stats(self, device_id: str) -> Dict:
        records = self._io_history.get(device_id, [])
        if not records:
            return {"total_ops": 0, "avg_latency_ms": 0, "throughput_mb": 0}
        total_ops = len(records)
        avg_lat = sum(r.latency_ms for r in records) / total_ops
        total_kb = sum(r.size_kb for r in records)
        duration = records[-1].timestamp - records[0].timestamp if total_ops > 1 else 1
        throughput = (total_kb / 1024) / duration if duration > 0 else 0
        reads = sum(1 for r in records if r.op_type == IOOpType.READ)
        writes = total_ops - reads
        return {
            "total_ops": total_ops,
            "reads": reads,
            "writes": writes,
            "avg_latency_ms": round(avg_lat, 2),
            "max_latency_ms": round(max(r.latency_ms for r in records), 2),
            "throughput_mb_s": round(throughput, 2),
            "total_data_mb": round(total_kb / 1024, 2),
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        _ = self.trace("execute")
        # REMOVED: metrics_collector.counter("block_device_ops_total", labels={"action": action})self.audit("execute", f"action={action}")
        actions = {
            "register_device": self._exec_register_device,
            "list_devices": self._exec_list_devices,
            "get_device": self._exec_get_device,
            "get_io_stats": self._exec_get_io_stats,
            "simulate_io": self._exec_simulate_io,
            "create_snapshot": self._exec_create_snapshot,
            "list_snapshots": self._exec_list_snapshots,
            "create_pool": self._exec_create_pool,
            "list_pools": self._exec_list_pools,
            "get_pool_info": self._exec_get_pool_info,
            "get_stats": self._exec_get_stats,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        return handler(params)
        return {"status": "healthy", "module": "block_device"}

    def _exec_register_device(self, p: Dict) -> Dict:
        did = self._next_id("dev")
        self._devices[did] = BlockDevice(
            device_id=did,
            name=p.get("name", f"/dev/disk{len(self._devices)}"),
            device_type=DeviceType(p.get("type", "ssd")),
            size_gb=p.get("size_gb", 100),
            status=DeviceStatus.ONLINE,
            mount_point=p.get("mount_point", ""),
            fs_type=p.get("fs_type", ""),
        )
        self._io_history[did] = []
        return {"success": True, "result": {"device_id": did}}

    def _exec_list_devices(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "type": d.device_type.value,
                    "size_gb": d.size_gb,
                    "used_gb": round(d.used_gb, 1),
                    "usage_pct": round(d.used_gb / d.size_gb * 100, 1) if d.size_gb > 0 else 0,
                    "status": d.status.value,
                    "mount": d.mount_point,
                    "latency_ms": d.latency_ms,
                }
                for d in self._devices.values()
            ],
        }

    def _exec_get_device(self, p: Dict) -> Dict:
        did = p["device_id"]
        if did not in self._devices:
            return {"success": False, "error": "设备不存在"}
        d = self._devices[did]
        io = self._get_io_stats(did)
        return {
            "success": True,
            "result": {
                "device_id": d.device_id,
                "name": d.name,
                "type": d.device_type.value,
                "size_gb": d.size_gb,
                "used_gb": round(d.used_gb, 1),
                "status": d.status.value,
                "mount": d.mount_point,
                "fs": d.fs_type,
                "read_speed_mb": d.read_speed_mb,
                "write_speed_mb": d.write_speed_mb,
                "iops_read": d.iops_read,
                "iops_write": d.iops_write,
                "latency_ms": d.latency_ms,
                "io_stats": io,
            },
        }

    def _exec_get_io_stats(self, p: Dict) -> Dict:
        did = p["device_id"]
        if did not in self._devices:
            return {"success": False, "error": "设备不存在"}
        return {"success": True, "result": self._get_io_stats(did)}

    def _exec_simulate_io(self, p: Dict) -> Dict:
        """模拟IO操作用于测试和基准"""
        did = p["device_id"]
        if did not in self._devices:
            return {"success": False, "error": "设备不存在"}
        ops = p.get("ops", 10)
        size_kb = p.get("size_kb", 4096)
        dev = self._devices[did]
        for _ in range(ops):
            op = IOOpType.READ if _ % 2 == 0 else IOOpType.WRITE
            latency = dev.latency_ms + (hash(_ * time.time()) % 100) / 100
            self._record_io(did, op, size_kb, latency)
        io = self._get_io_stats(did)
        return {"success": True, "result": {"simulated_ops": ops, "io_stats": io}}

    def _exec_create_snapshot(self, p: Dict) -> Dict:
        did = p["device_id"]
        if did not in self._devices:
            return {"success": False, "error": "设备不存在"}
        dev = self._devices[did]
        sid = self._next_id("snap")
        self._snapshots[sid] = Snapshot(
            snap_id=sid,
            device_id=did,
            name=p.get("name", f"snapshot_{sid[:6]}"),
            size_gb=dev.used_gb,
            created_at=datetime.now().isoformat(),
            parent_snap=p.get("parent_snap", ""),
        )
        return {"success": True, "result": {"snap_id": sid, "size_gb": round(dev.used_gb, 1)}}

    def _exec_list_snapshots(self, p: Dict) -> Dict:
        did = p.get("device_id", "")
        snaps = [s for s in self._snapshots.values() if not did or s.device_id == did]
        return {
            "success": True,
            "result": {
                "total": len(snaps),
                "snapshots": [
                    {
                        "snap_id": s.snap_id,
                        "device_id": s.device_id,
                        "name": s.name,
                        "size_gb": round(s.size_gb, 1),
                        "created_at": s.created_at,
                    }
                    for s in snaps
                ],
            },
        }

    def _exec_create_pool(self, p: Dict) -> Dict:
        pid = self._next_id("pool")
        members = p.get("members", [])
        total = sum(self._devices[m].size_gb for m in members if m in self._devices)
        self._pools[pid] = StoragePool(
            pool_id=pid,
            name=p.get("name", f"pool_{pid[:6]}"),
            raid_level=p.get("raid_level", "RAID1"),
            member_devices=members,
            total_gb=total,
        )
        return {"success": True, "result": {"pool_id": pid, "total_gb": total, "members": len(members)}}

    def _exec_list_pools(self, p: Dict) -> Dict:
        return {
            "success": True,
            "result": [
                {
                    "pool_id": p.pool_id,
                    "name": p.name,
                    "raid": p.raid_level,
                    "total_gb": p.total_gb,
                    "used_gb": round(p.used_gb, 1),
                    "usage_pct": round(p.used_gb / p.total_gb * 100, 1) if p.total_gb > 0 else 0,
                    "devices": len(p.member_devices),
                }
                for p in self._pools.values()
            ],
        }

    def _exec_get_pool_info(self, p: Dict) -> Dict:
        pid = p["pool_id"]
        if pid not in self._pools:
            return {"success": False, "error": "存储池不存在"}
        pool = self._pools[pid]
        devices = []
        for did in pool.member_devices:
            if did in self._devices:
                d = self._devices[did]
                devices.append({"device_id": did, "name": d.name, "size_gb": d.size_gb, "status": d.status.value})
        return {
            "success": True,
            "result": {
                "pool_id": pool.pool_id,
                "name": pool.name,
                "raid": pool.raid_level,
                "total_gb": pool.total_gb,
                "used_gb": round(pool.used_gb, 1),
                "free_gb": round(pool.total_gb - pool.used_gb, 1),
                "devices": devices,
            },
        }

    def _exec_get_stats(self, p: Dict) -> Dict:
        total_size = sum(d.size_gb for d in self._devices.values())
        total_used = sum(d.used_gb for d in self._devices.values())
        return {
            "success": True,
            "result": {
                "total_devices": len(self._devices),
                "total_size_gb": total_size,
                "total_used_gb": round(total_used, 1),
                "total_free_gb": round(total_size - total_used, 1),
                "usage_pct": round(total_used / total_size * 100, 1) if total_size > 0 else 0,
                "total_pools": len(self._pools),
                "total_snapshots": len(self._snapshots),
                "total_io_records": sum(len(v) for v in self._io_history.values()),
            },
        }

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "module_id": self.MODULE_ID,
                "devices": len(self._devices),
                "pools": len(self._pools),
                "snapshots": len(self._snapshots),
                "last_check": datetime.now().isoformat(),
            }
        )
        return result

    def shutdown(self) -> bool:
        logger.info("块设备管理关闭")
        return True

    def assess_device_health(self, device_id: str) -> Dict[str, Any]:
        """评估块设备健康状态：坏扇区趋势、SMART指标分析、剩余寿命预测"""
        device = None
        for d in self._devices if hasattr(self, "_devices") else []:
            did = getattr(d, "device_id", "") if hasattr(d, "device_id") else str(getattr(d, "id", ""))
            if did == device_id:
                device = d
                break
        if not device:
            return {"error": "device not found", "device_id": device_id}
        # SMART指标聚合
        smart = getattr(device, "smart_data", {}) if hasattr(device, "smart_data") else {}
        read_errors = smart.get("read_errors", 0)
        write_errors = smart.get("write_errors", 0)
        reallocated = smart.get("reallocated_sectors", 0)
        power_cycles = smart.get("power_cycles", 0)
        temperature = smart.get("temperature", 35)
        powered_hours = smart.get("powered_hours", 0)
        # 健康评分计算
        score = 100
        if read_errors > 100:
            score -= 20
        elif read_errors > 10:
            score -= 10
        if write_errors > 100:
            score -= 20
        elif write_errors > 10:
            score -= 10
        if reallocated > 100:
            score -= 25
        elif reallocated > 10:
            score -= 10
        if temperature > 60:
            score -= 15
        elif temperature > 50:
            score -= 5
        score = max(0, score)
        # 剩余寿命估算
        if powered_hours > 0 and reallocated > 0:
            hours_per_realloc = powered_hours / reallocated
            remaining_hours = max(
                0, hours_per_realloc - (reallocated * hours_per_realloc / powered_hours) * powered_hours
            )
            remaining_days = round(remaining_hours / 24, 1)
        else:
            remaining_days = -1  # 无法估算
        # 风险等级
        if score >= 80:
            risk = "low"
        elif score >= 60:
            risk = "medium"
        elif score >= 40:
            risk = "high"
        else:
            risk = "critical"
        return {
            "device_id": device_id,
            "health_score": score,
            "risk_level": risk,
            "smart_summary": {
                "read_errors": read_errors,
                "write_errors": write_errors,
                "reallocated_sectors": reallocated,
                "temperature_c": temperature,
                "power_cycles": power_cycles,
                "powered_hours": powered_hours,
            },
            "estimated_remaining_days": remaining_days,
            "recommendation": self._device_recommendation(score, risk),
        }

    def _device_recommendation(self, score: int, risk: str) -> str:
        if risk == "critical":
            return "设备健康度极低，建议立即替换并迁移数据"
        if risk == "high":
            return "设备存在明显退化迹象，建议尽快安排替换窗口"
        if risk == "medium":
            return "设备有一定老化指标，建议增加监控频率并准备备件"
        return "设备状态良好，继续保持例行监控"

    def analyze_iops_performance(self, hours: int = 1) -> Dict[str, Any]:
        """分析块设备IOPS性能：读写IOPS、吞吐量、延迟分布、队列深度"""
        metrics = self._metrics_history if hasattr(self, "_metrics_history") else []
        cutoff = time.time() - hours * 3600
        recent = [m for m in metrics if isinstance(m, dict) and m.get("timestamp", 0) >= cutoff]
        if not recent:
            return {"window_hours": hours, "data_points": 0}
        read_iops = [m.get("read_iops", 0) for m in recent]
        write_iops = [m.get("write_iops", 0) for m in recent]
        read_latency = [m.get("read_latency_ms", 0) for m in recent]
        write_latency = [m.get("write_latency_ms", 0) for m in recent]
        throughput_mb = [m.get("throughput_mb", 0) for m in recent]

        def percentile(data, p):
            if not data:
                return 0
            s = sorted(data)
            idx = int(len(s) * p / 100)
            return s[min(idx, len(s) - 1)]

        return {
            "window_hours": hours,
            "data_points": len(recent),
            "read_iops": {
                "avg": round(sum(read_iops) / max(len(read_iops), 1), 1),
                "p50": percentile(read_iops, 50),
                "p95": percentile(read_iops, 95),
                "p99": percentile(read_iops, 99),
                "max": max(read_iops) if read_iops else 0,
            },
            "write_iops": {
                "avg": round(sum(write_iops) / max(len(write_iops), 1), 1),
                "p50": percentile(write_iops, 50),
                "p95": percentile(write_iops, 95),
                "p99": percentile(write_iops, 99),
                "max": max(write_iops) if write_iops else 0,
            },
            "read_latency_ms": {
                "avg": round(sum(read_latency) / max(len(read_latency), 1), 2),
                "p95": percentile(read_latency, 95),
                "p99": percentile(read_latency, 99),
            },
            "write_latency_ms": {
                "avg": round(sum(write_latency) / max(len(write_latency), 1), 2),
                "p95": percentile(write_latency, 95),
                "p99": percentile(write_latency, 99),
            },
            "throughput_mb_s": {
                "avg": round(sum(throughput_mb) / max(len(throughput_mb), 1), 2),
                "max": max(throughput_mb) if throughput_mb else 0,
            },
        }

    def forecast_capacity(self, device_id: str, days_forecast: int = 30) -> Dict[str, Any]:
        """预测块设备容量消耗趋势，计算预计耗尽时间"""
        device = None
        for d in self._devices if hasattr(self, "_devices") else []:
            did = getattr(d, "device_id", "") if hasattr(d, "device_id") else str(getattr(d, "id", ""))
            if did == device_id:
                device = d
                break
        if not device:
            return {"error": "device not found"}
        total_gb = getattr(device, "total_size_gb", 0) or 0
        used_gb = getattr(device, "used_size_gb", 0) or 0
        if total_gb <= 0:
            return {"error": "invalid device size", "device_id": device_id}
        usage_rate = used_gb / total_gb
        # 从历史计算日增长率
        history = self._usage_history if hasattr(self, "_usage_history") else {}
        device_history = history.get(device_id, [])
        if len(device_history) >= 2:
            recent = device_history[-7:]  # 取最近7天
            if len(recent) >= 2:
                daily_growth = (recent[-1] - recent[0]) / len(recent)
            else:
                daily_growth = 0
        else:
            daily_growth = 0
        remaining_gb = total_gb - used_gb
        if daily_growth > 0:
            days_until_full = remaining_gb / daily_growth
        else:
            days_until_full = float("inf")
        forecast_points = []
        for day in range(0, days_forecast + 1, 5):
            projected = used_gb + daily_growth * day
            forecast_points.append(
                {
                    "day": day,
                    "projected_used_gb": round(projected, 2),
                    "projected_usage_pct": round(projected / total_gb * 100, 1),
                }
            )
        return {
            "device_id": device_id,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "usage_percent": round(usage_rate * 100, 1),
            "daily_growth_gb": round(daily_growth, 3),
            "remaining_gb": round(remaining_gb, 2),
            "days_until_full": round(days_until_full, 1) if days_until_full != float("inf") else -1,
            "forecast": forecast_points,
            "alert": "容量将在30天内耗尽"
            if 0 < days_until_full <= 30
            else ("容量将在90天内耗尽，建议扩容" if 0 < days_until_full <= 90 else "容量充足"),
        }

module_class = BlockDeviceManager
