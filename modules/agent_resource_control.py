"""
AUTO-EVO-AI V0.1 — Agent Resource Control — 智能体资源管控
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Grade: A
        AUTO EVO AI V0.1 - 智能体集群资源精细化管控模块
Agent Resource Control - 250万级智能体分层池化、硬件监控、资源配额、过载熔断
命名空间: evo.resource.agent.*
"""

__module_meta__ = {
        "id": "agent-resource-control",
        "name": "Agent Resource Control",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "sample_interval",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "cache_size",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metrics",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "callback",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "count",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "seconds",
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
                    "on": "agent_resource_control.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "config",
            "monitor",
            "multi-agent",
            "agent"
        ],
        "grade": "B",
        "description": "AUTO EVO AI V0.1 - 智能体集群资源精细化管控模块 Agent Resource Control - 250万级智能体分层池化、硬件监控、资源配额、过载熔断"
    }

import os
import sys
import json
import time
import logging
from core.logging_config import get_logger
from core.logging_config import get_logger
import threading
import queue
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from abc import ABC, abstractmethod
import copy

# 企业级基类导入
try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin

    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False

# 尝试导入 psutil，获取失败时提供降级方案
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil 未安装，硬件监控功能将受限。请运行: pip install psutil")

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("agent_resource_control.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = get_logger("AgentResourceControl")

# ==================== 枚举定义 ====================

class AgentPoolType(Enum):
    """智能体池类型"""

    LIGHT = "light"  # 轻量任务池（文本处理、简单查询）
    HEAVY = "heavy"  # 重度开发池（代码生成、复杂推理）
    COMPUTE = "compute"  # 运算池（数据分析、模型推理）
    IDLE = "idle"  # 闲置池（休眠中的智能体）
    MAINTENANCE = "maintenance"  # 维护池（待优化的智能体）

class AgentStatus(Enum):
    """智能体状态"""

    ACTIVE = "active"  # 运行中
    IDLE = "idle"  # 空闲
    SLEEPING = "sleeping"  # 休眠中
    BLOCKED = "blocked"  # 被阻塞
    OVERLOADED = "overloaded"  # 过载
    FAILED = "failed"  # 失败
    MAINTENANCE = "maintenance"  # 维护中

class ResourcePriority(Enum):
    """资源优先级"""

    CRITICAL = 0  # 关键任务（最高优先级）
    HIGH = 1  # 高优先级
    NORMAL = 2  # 普通优先级
    LOW = 3  # 低优先级
    BATCH = 4  # 批处理（最低优先级）

class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常（关闭）
    OPEN = "open"  # 熔断（打开）
    HALF_OPEN = "half_open"  # 半开（尝试恢复）

class PerfMode(Enum):
    """性能模式"""

    HIGH_PERFORMANCE = "high_perf"  # 高性能模式
    BALANCED = "balanced"  # 均衡模式
    LOW_PERFORMANCE = "low_perf"  # 低配适配模式
    POWER_SAVING = "power_saving"  # 节能模式

# ==================== 数据类定义 ====================

@dataclass
class HardwareMetrics:
    """硬件资源指标"""

    timestamp: float
    cpu_percent: float = 0.0
    cpu_count: int = 0
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    memory_available: int = 0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    disk_io_percent: float = 0.0
    network_sent: int = 0
    network_recv: int = 0
    # GPU相关（可选）
    gpu_percent: float = 0.0
    gpu_memory_used: int = 0
    gpu_memory_total: int = 0
    gpu_temperature: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get_summary(self) -> str:
        """获取摘要信息"""
        return (
            f"CPU: {self.cpu_percent:.1f}% | "
            f"Memory: {self.memory_used / 1024**3:.2f}/{self.memory_total / 1024**3:.2f}GB "
            f"({self.memory_percent:.1f}%) | "
            f"GPU: {self.gpu_percent:.1f}%"
        )

@dataclass
class AgentInfo:
    """智能体信息"""

    agent_id: str
    pool_type: AgentPoolType = AgentPoolType.LIGHT
    status: AgentStatus = AgentStatus.IDLE
    priority: ResourcePriority = ResourcePriority.NORMAL
    cpu_limit: float = 100.0  # CPU限制百分比
    memory_limit: int = 1024 * 1024 * 1024  # 内存限制（字节）
    gpu_enabled: bool = False
    gpu_limit: float = 100.0  # GPU限制百分比
    current_cpu: float = 0.0
    current_memory: int = 0
    current_gpu: float = 0.0
    task_count: int = 0
    max_tasks: int = 10
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    idle_time: float = 0.0
    total_tasks_completed: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["pool_type"] = self.pool_type.value
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data

@dataclass
class ResourceQuota:
    """资源配额配置"""

    quota_id: str
    name: str
    pool_type: AgentPoolType
    max_agents: int = 100
    max_cpu_percent: float = 100.0
    max_memory_bytes: int = 8 * 1024**3  # 8GB
    max_gpu_percent: float = 100.0
    weight_limit: float = 1.0  # 权重限流系数
    burst_allowance: float = 1.5  # 突发允许系数
    priority_boost: float = 1.0  # 优先级提升系数
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class PoolConfig:
    """池配置"""

    pool_id: str
    pool_type: AgentPoolType
    name: str
    description: str = ""
    min_size: int = 10
    max_size: int = 10000
    initial_size: int = 100
    scale_up_threshold: float = 0.8  # 扩容阈值
    scale_down_threshold: float = 0.3  # 缩容阈值
    scale_up_cooldown: int = 300  # 扩容冷却时间（秒）
    scale_down_cooldown: int = 600  # 缩容冷却时间（秒）
    idle_timeout: int = 300  # 空闲超时时间（秒）
    sleep_after_idle: int = 600  # 空闲多久后休眠（秒）
    wake_up_threshold: float = 0.9  # 唤醒阈值
    auto_scale: bool = True
    enabled: bool = True

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 失败次数阈值
    success_threshold: int = 3  # 成功次数阈值（半开状态）
    timeout: float = 60.0  # 熔断超时时间（秒）
    half_open_max_calls: int = 10  # 半开状态最大调用数
    volume_threshold: int = 20  # 最小请求量阈值

@dataclass
class APIResponse:
    """API响应封装"""

    success: bool
    data: Any = None
    error: str = ""
    code: int = 200

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "code": self.code,
            "timestamp": time.time(),
        }

# ==================== 硬件监控类 ====================

class HardwareMonitor:
    """
    硬件资源实时监控

    监控 CPU、内存、磁盘IO、网络、GPU 等硬件资源使用情况
    支持自定义采样间隔和数据缓存
    """

    def trace(self, *args, **kwargs):
        return "no-op"

    def __init__(self, sample_interval: float = 1.0, cache_size: int = 100):
        """
        初始化硬件监控器

        Args:
            sample_interval: 采样间隔（秒）
            cache_size: 缓存历史数据条数
        """
        self.sample_interval = sample_interval
        self.cache_size = cache_size
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # 历史数据缓存
        self._cpu_history: List[float] = []
        self._memory_history: List[float] = []
        self._disk_history: List[float] = []
        self._metrics_history: List[HardwareMetrics] = []

        # 初始数据获取
        self._current_metrics = self._get_initial_metrics()

        # 回调函数
        self._alert_callbacks: List[Callable[[HardwareMetrics], None]] = []

        logger.info(f"HardwareMonitor 初始化完成，采样间隔: {sample_interval}s")

    def _get_initial_metrics(self) -> HardwareMetrics:
        """获取初始硬件指标"""
        metrics = HardwareMetrics(timestamp=time.time())

        if PSUTIL_AVAILABLE:
            try:
                metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
                metrics.cpu_count = psutil.cpu_count()

                mem = psutil.virtual_memory()
                metrics.memory_total = mem.total
                metrics.memory_used = mem.used
                metrics.memory_percent = mem.percent
                metrics.memory_available = mem.available

                # 磁盘IO
                try:
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        metrics.disk_read_bytes = disk_io.read_bytes
                        metrics.disk_write_bytes = disk_io.write_bytes
                except Exception:
                    pass

                # 网络IO
                try:
                    net_io = psutil.net_io_counters()
                    if net_io:
                        metrics.network_sent = net_io.bytes_sent
                        metrics.network_recv = net_io.bytes_recv
                except Exception:
                    pass

                # GPU监控（如果有）
                try:
                    import subprocess

                    result = subprocess.run(
                        [
                            "nvidia-smi",
                            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        parts = result.stdout.strip().split(",")
                        metrics.gpu_percent = float(parts[0].strip())
                        metrics.gpu_memory_used = int(parts[1].strip()) * 1024 * 1024
                        metrics.gpu_memory_total = int(parts[2].strip()) * 1024 * 1024
                        metrics.gpu_temperature = float(parts[3].strip())
                except Exception:
                    # GPU监控失败，使用默认值
                    metrics.gpu_percent = 0.0

            except Exception as e:
                logger.warning(f"获取硬件指标失败: {e}")

        return metrics

    def start_monitoring(self):
        _ = self.trace("start_monitoring")
        """启动后台监控线程"""
        if self._monitoring:
            logger.warning("硬件监控已在运行")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("硬件监控已启动")

    def stop_monitoring(self):
        """停止后台监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("硬件监控已停止")

    def _monitor_loop(self):
        """监控主循环"""
        last_disk_io = None
        last_network_io = None

        while self._monitoring:
            try:
                metrics = HardwareMetrics(timestamp=time.time())

                if PSUTIL_AVAILABLE:
                    # CPU
                    metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
                    metrics.cpu_count = psutil.cpu_count()

                    # 内存
                    mem = psutil.virtual_memory()
                    metrics.memory_total = mem.total
                    metrics.memory_used = mem.used
                    metrics.memory_percent = mem.percent
                    metrics.memory_available = mem.available

                    # 磁盘IO
                    try:
                        disk_io = psutil.disk_io_counters()
                        if disk_io and last_disk_io:
                            read_delta = disk_io.read_bytes - last_disk_io.read_bytes
                            write_delta = disk_io.write_bytes - last_disk_io.write_bytes
                            total_delta = read_delta + write_delta
                            metrics.disk_read_bytes = disk_io.read_bytes
                            metrics.disk_write_bytes = disk_io.write_bytes
                            # 计算IO百分比（简化计算）
                            metrics.disk_io_percent = min(total_delta / (1024**3) * 100, 100)
                        if disk_io:
                            last_disk_io = disk_io
                    except Exception:
                        pass

                    # 网络IO
                    try:
                        net_io = psutil.net_io_counters()
                        if net_io and last_network_io:
                            sent_delta = net_io.bytes_sent - last_network_io.bytes_sent
                            recv_delta = net_io.bytes_recv - last_network_io.bytes_recv
                            metrics.network_sent = net_io.bytes_sent
                            metrics.network_recv = net_io.bytes_recv
                        if net_io:
                            last_network_io = net_io
                    except Exception:
                        pass

                    # GPU
                    metrics.gpu_percent = self._current_metrics.gpu_percent
                    metrics.gpu_memory_used = self._current_metrics.gpu_memory_used
                    metrics.gpu_memory_total = self._current_metrics.gpu_memory_total
                    metrics.gpu_temperature = self._current_metrics.gpu_temperature

                # 更新当前指标
                with self._lock:
                    self._current_metrics = metrics
                    self._metrics_history.append(metrics)
                    self._cpu_history.append(metrics.cpu_percent)
                    self._memory_history.append(metrics.memory_percent)
                    self._disk_history.append(metrics.disk_io_percent)

                    # 限制缓存大小
                    if len(self._metrics_history) > self.cache_size:
                        self._metrics_history.pop(0)
                    if len(self._cpu_history) > self.cache_size:
                        self._cpu_history.pop(0)
                    if len(self._memory_history) > self.cache_size:
                        self._memory_history.pop(0)
                    if len(self._disk_history) > self.cache_size:
                        self._disk_history.pop(0)

                # 检查告警阈值
                self._check_alerts(metrics)

            except Exception as e:
                logger.error(f"监控循环异常: {e}")

            time.sleep(self.sample_interval)

    def _check_alerts(self, metrics: HardwareMetrics):
        """检查告警条件并触发回调"""
        alert_conditions = []

        # CPU告警
        if metrics.cpu_percent > 90:
            alert_conditions.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent > 80:
            alert_conditions.append(f"CPU使用率偏高: {metrics.cpu_percent:.1f}%")

        # 内存告警
        if metrics.memory_percent > 90:
            alert_conditions.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent > 80:
            alert_conditions.append(f"内存使用率偏高: {metrics.memory_percent:.1f}%")

        # GPU告警
        if metrics.gpu_percent > 95:
            alert_conditions.append(f"GPU使用率过高: {metrics.gpu_percent:.1f}%")
        elif metrics.gpu_percent > 85:
            alert_conditions.append(f"GPU使用率偏高: {metrics.gpu_percent:.1f}%")

        # GPU温度告警
        if metrics.gpu_temperature > 85:
            alert_conditions.append(f"GPU温度过高: {metrics.gpu_temperature:.1f}°C")

        if alert_conditions:
            logger.warning(f"硬件告警: {'; '.join(alert_conditions)}")

        # 触发回调
        for callback in self._alert_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")

    def register_alert_callback(self, callback: Callable[[HardwareMetrics], None]):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def get_current_metrics(self) -> HardwareMetrics:
        """获取当前硬件指标"""
        with self._lock:
            return copy.deepcopy(self._current_metrics)

    def get_metrics_history(self, count: int = 10) -> List[HardwareMetrics]:
        """获取历史指标"""
        with self._lock:
            return self._metrics_history[-count:]

    def get_average_metrics(self, seconds: int = 60) -> HardwareMetrics:
        """获取最近N秒的平均指标"""
        with self._lock:
            cutoff_time = time.time() - seconds
            relevant = [m for m in self._metrics_history if m.timestamp >= cutoff_time]

            if not relevant:
                return self._current_metrics

            avg = HardwareMetrics(timestamp=time.time())
            avg.cpu_percent = sum(m.cpu_percent for m in relevant) / len(relevant)
            avg.cpu_count = self._current_metrics.cpu_count
            avg.memory_percent = sum(m.memory_percent for m in relevant) / len(relevant)
            avg.memory_total = self._current_metrics.memory_total
            avg.memory_used = int(avg.memory_percent / 100 * avg.memory_total)
            avg.memory_available = avg.memory_total - avg.memory_used
            avg.disk_io_percent = sum(m.disk_io_percent for m in relevant) / len(relevant)
            avg.gpu_percent = sum(m.gpu_percent for m in relevant) / len(relevant)
            avg.gpu_memory_total = self._current_metrics.gpu_memory_total
            avg.gpu_memory_used = int(avg.gpu_percent / 100 * avg.gpu_memory_total) if avg.gpu_memory_total else 0

            return avg

    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源状态摘要（用于API响应）"""
        current = self.get_current_metrics()
        avg_60s = self.get_average_metrics(60)

        return {
            "current": current.to_dict(),
            "average_60s": avg_60s.to_dict(),
            "history_count": len(self._metrics_history),
            "is_monitoring": self._monitoring,
            "psutil_available": PSUTIL_AVAILABLE,
        }

# ==================== 资源配额管理类 ====================

class ResourceQuotaManager(object):
    """
    资源配额管理器

    管理不同类型智能体池的资源配额，支持配额查询、修改、权重限流
    """

    def __init__(self):
        self._quotas: Dict[str, ResourceQuota] = {}
        self._lock = threading.RLock()
        self._initialize_default_quotas()
        logger.info("ResourceQuotaManager 初始化完成")

    def _initialize_default_quotas(self):
        """初始化默认配额"""
        default_quotas = [
            ResourceQuota(
                quota_id="quota_light",
                name="轻量任务池配额",
                pool_type=AgentPoolType.LIGHT,
                max_agents=1000000,  # 100万
                max_cpu_percent=40.0,
                max_memory_bytes=2 * 1024**3,  # 2GB
                max_gpu_percent=20.0,
                weight_limit=1.0,
                priority_boost=1.2,
            ),
            ResourceQuota(
                quota_id="quota_heavy",
                name="重度开发池配额",
                pool_type=AgentPoolType.HEAVY,
                max_agents=500000,  # 50万
                max_cpu_percent=80.0,
                max_memory_bytes=8 * 1024**3,  # 8GB
                max_gpu_percent=80.0,
                weight_limit=0.8,
                priority_boost=1.5,
            ),
            ResourceQuota(
                quota_id="quota_compute",
                name="运算池配额",
                pool_type=AgentPoolType.COMPUTE,
                max_agents=100000,  # 10万
                max_cpu_percent=100.0,
                max_memory_bytes=32 * 1024**3,  # 32GB
                max_gpu_percent=100.0,
                weight_limit=0.5,
                priority_boost=2.0,
            ),
            ResourceQuota(
                quota_id="quota_idle",
                name="闲置池配额",
                pool_type=AgentPoolType.IDLE,
                max_agents=1000000,  # 100万
                max_cpu_percent=5.0,
                max_memory_bytes=256 * 1024**2,  # 256MB
                max_gpu_percent=0.0,
                weight_limit=0.1,
            ),
        ]

        for quota in default_quotas:
            self._quotas[quota.quota_id] = quota

    def get_quota(self, quota_id: str) -> Optional[ResourceQuota]:
        """获取配额"""
        with self._lock:
            return copy.deepcopy(self._quotas.get(quota_id))

    def get_quota_by_pool_type(self, pool_type: AgentPoolType) -> Optional[ResourceQuota]:
        """根据池类型获取配额"""
        with self._lock:
            for quota in self._quotas.values():
                if quota.pool_type == pool_type:
                    return copy.deepcopy(quota)
            return None

    def list_quotas(self) -> List[Dict[str, Any]]:
        """列出所有配额"""
        with self._lock:
            return [quota.to_dict() for quota in self._quotas.values()]

    def update_quota(self, quota_id: str, updates: Dict[str, Any]) -> APIResponse:
        """更新配额"""
        with self._lock:
            if quota_id not in self._quotas:
                return APIResponse(success=False, error=f"配额 {quota_id} 不存在", code=404)

            quota = self._quotas[quota_id]
            try:
                for key, value in updates.items():
                    if hasattr(quota, key):
                        setattr(quota, key, value)
                quota.updated_at = time.time()
                logger.info(f"配额 {quota_id} 已更新")
                return APIResponse(success=True, data=quota.to_dict())
            except Exception as e:
                return APIResponse(success=False, error=str(e), code=500)

    def set_pool_limit(
        self,
        pool_type: AgentPoolType,
        max_agents: Optional[int] = None,
        max_cpu: Optional[float] = None,
        max_memory: Optional[int] = None,
        max_gpu: Optional[float] = None,
        weight_limit: Optional[float] = None,
    ) -> APIResponse:
        """设置池资源限制"""
        quota = self.get_quota_by_pool_type(pool_type)
        if not quota:
            return APIResponse(success=False, error=f"池 {pool_type.value} 配额不存在", code=404)

        updates = {}
        if max_agents is not None:
            updates["max_agents"] = max_agents
        if max_cpu is not None:
            updates["max_cpu_percent"] = max_cpu
        if max_memory is not None:
            updates["max_memory_bytes"] = max_memory
        if max_gpu is not None:
            updates["max_gpu_percent"] = max_gpu
        if weight_limit is not None:
            updates["weight_limit"] = weight_limit

        return self.update_quota(quota.quota_id, updates)

    def check_quota_available(
        self,
        pool_type: AgentPoolType,
        requested_cpu: float = 0.0,
        requested_memory: int = 0,
        requested_gpu: float = 0.0,
    ) -> Tuple[bool, str]:
        """检查配额是否足够"""
        quota = self.get_quota_by_pool_type(pool_type)
        if not quota:
            return False, f"池 {pool_type.value} 配额不存在"

        if not quota.enabled:
            return False, f"池 {pool_type.value} 配额已禁用"

        # 这里简化检查，实际应检查当前已使用的资源
        return True, "配额检查通过"

# ==================== 智能体池管理类 ====================

class AgentPool:
    """
    智能体池管理器

    实现250万级智能体分层池化：
    - 轻量任务池（Light Pool）
    - 重度开发池（Heavy Pool）
    - 运算池（Compute Pool）
    - 闲置池（Idle Pool）
    - 维护池（Maintenance Pool）
    """

    def __init__(self, pool_config: PoolConfig, quota_manager: ResourceQuotaManager):
        self.config = pool_config
        self.pool_type = pool_config.pool_type
        self.quota_manager = quota_manager

        # 智能体存储
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = threading.RLock()

        # 任务队列
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()

        # 统计信息
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_response_time": 0.0,
            "scale_events": 0,
        }

        # 定时任务
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        logger.info(f"AgentPool [{pool_config.name}] 初始化完成，最大容量: {pool_config.max_size}")

    def start(self):
        """启动池管理"""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"AgentPool [{self.config.name}] 已启动")

    def stop(self):
        """停止池管理"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info(f"AgentPool [{self.config.name}] 已停止")

    def _cleanup_loop(self):
        """清理循环：处理超时和休眠"""
        while self._running:
            try:
                self._cleanup_idle_agents()
                self._handle_scale()
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
            time.sleep(10)

    def _cleanup_idle_agents(self):
        """清理空闲智能体"""
        current_time = time.time()
        agents_to_sleep = []

        with self._lock:
            for agent_id, agent in self._agents.items():
                if agent.status == AgentStatus.IDLE:
                    agent.idle_time = current_time - agent.last_active

                    # 超时休眠
                    if agent.idle_time >= self.config.sleep_after_idle:
                        agents_to_sleep.append(agent_id)

        # 执行休眠
        for agent_id in agents_to_sleep:
            self.sleep_agent(agent_id)

    def _handle_scale(self):
        """处理自动扩缩容"""
        if not self.config.auto_scale:
            return

        with self._lock:
            current_size = len(self._agents)

            # 计算使用率
            active_count = sum(1 for a in self._agents.values() if a.status == AgentStatus.ACTIVE)
            usage_ratio = active_count / max(current_size, 1)

            # 扩容
            if usage_ratio > self.config.scale_up_threshold and current_size < self.config.max_size:
                new_size = min(current_size + 10, self.config.max_size)
                logger.info(f"池 [{self.config.name}] 扩容: {current_size} -> {new_size}")
                self._stats["scale_events"] += 1

            # 缩容
            elif usage_ratio < self.config.scale_down_threshold and current_size > self.config.min_size:
                new_size = max(current_size - 5, self.config.min_size)
                logger.info(f"池 [{self.config.name}] 缩容: {current_size} -> {new_size}")
                self._stats["scale_events"] += 1

    # ==================== 智能体管理 ====================

    def register_agent(self, agent_id: str, metadata: Dict[str, Any] = None) -> AgentInfo:
        """注册智能体"""
        with self._lock:
            if agent_id in self._agents:
                logger.warning(f"智能体 {agent_id} 已存在")
                return self._agents[agent_id]

            agent = AgentInfo(agent_id=agent_id, pool_type=self.pool_type, metadata=metadata or {})
            self._agents[agent_id] = agent
            logger.debug(f"智能体 {agent_id} 已注册到 {self.config.name}")
            return copy.deepcopy(agent)

    def unregister_agent(self, agent_id: str) -> bool:
        """注销智能体"""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.debug(f"智能体 {agent_id} 已注销")
                return True
            return False

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """获取智能体信息"""
        with self._lock:
            agent = self._agents.get(agent_id)
            return copy.deepcopy(agent) if agent else None

    def list_agents(
        self, status: Optional[AgentStatus] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出智能体"""
        with self._lock:
            agents = list(self._agents.values())

            if status:
                agents = [a for a in agents if a.status == status]

            agents = agents[offset : offset + limit]
            return [a.to_dict() for a in agents]

    def update_agent_quota(
        self,
        agent_id: str,
        cpu_limit: Optional[float] = None,
        memory_limit: Optional[int] = None,
        max_tasks: Optional[int] = None,
    ) -> APIResponse:
        """更新智能体配额"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return APIResponse(success=False, error=f"智能体 {agent_id} 不存在", code=404)

            try:
                if cpu_limit is not None:
                    agent.cpu_limit = cpu_limit
                if memory_limit is not None:
                    agent.memory_limit = memory_limit
                if max_tasks is not None:
                    agent.max_tasks = max_tasks

                logger.info(f"智能体 {agent_id} 配额已更新")
                return APIResponse(success=True, data=agent.to_dict())
            except Exception as e:
                return APIResponse(success=False, error=str(e), code=500)

    # ==================== 休眠/唤醒机制 ====================

    def sleep_agent(self, agent_id: str) -> APIResponse:
        """使智能体进入休眠"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return APIResponse(success=False, error=f"智能体 {agent_id} 不存在", code=404)

            if agent.status == AgentStatus.SLEEPING:
                return APIResponse(success=True, data={"message": "智能体已在休眠状态"})

            if agent.task_count > 0:
                return APIResponse(success=False, error="无法休眠：智能体仍有进行中的任务", code=400)

            agent.status = AgentStatus.SLEEPING
            agent.last_active = time.time()

            logger.info(f"智能体 {agent_id} 已进入休眠")
            return APIResponse(success=True, data=agent.to_dict())

    def wake_agent(self, agent_id: str) -> APIResponse:
        """唤醒休眠的智能体"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return APIResponse(success=False, error=f"智能体 {agent_id} 不存在", code=404)

            if agent.status != AgentStatus.SLEEPING:
                return APIResponse(success=True, data={"message": "智能体未在休眠状态"})

            agent.status = AgentStatus.IDLE
            agent.last_active = time.time()

            logger.info(f"智能体 {agent_id} 已唤醒")
            return APIResponse(success=True, data=agent.to_dict())

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        with self._lock:
            status_counts = defaultdict(int)
            for agent in self._agents.values():
                status_counts[agent.status.value] += 1

            return {
                "pool_type": self.pool_type.value,
                "pool_name": self.config.name,
                "total_agents": len(self._agents),
                "status_distribution": dict(status_counts),
                "config": asdict(self.config),
                "stats": self._stats.copy(),
            }

# ==================== 负载均衡调度器 ====================

class LoadBalancer:
    """
    负载均衡调度器

    支持多种负载均衡策略：
    - 加权轮询（Weighted Round Robin）
    - 最少连接（Least Connections）
    - 资源感知（Resource Aware）
    - 优先级调度（Priority Based）
    """

    class Strategy(Enum):
        WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
        LEAST_CONNECTIONS = "least_connections"
        RESOURCE_AWARE = "resource_aware"
        PRIORITY_BASED = "priority_based"
        RANDOM = "random"

    def __init__(self, strategy: Strategy = Strategy.RESOURCE_AWARE):
        self.strategy = strategy
        self._pools: Dict[AgentPoolType, AgentPool] = {}
        self._lock = threading.RLock()
        self._connection_counts: Dict[str, int] = defaultdict(int)

        logger.info(f"LoadBalancer 初始化完成，策略: {strategy.value}")

    def register_pool(self, pool: AgentPool):
        """注册池"""
        with self._lock:
            self._pools[pool.pool_type] = pool

    def unregister_pool(self, pool_type: AgentPoolType):
        """注销池"""
        with self._lock:
            if pool_type in self._pools:
                del self._pools[pool_type]

    def select_pool(
        self, task_priority: ResourcePriority = ResourcePriority.NORMAL, requires_gpu: bool = False
    ) -> Optional[AgentPool]:
        """选择最佳池"""
        with self._lock:
            # 根据需求筛选候选池
            candidates = []

            for pool_type, pool in self._pools.items():
                if not pool.config.enabled:
                    continue

                # GPU需求检查
                if requires_gpu and pool_type == AgentPoolType.LIGHT:
                    continue

                candidates.append((pool_type, pool))

            if not candidates:
                return None

            # 根据策略选择
            if self.strategy == self.Strategy.WEIGHTED_ROUND_ROBIN:
                return self._select_weighted_round_robin(candidates)
            elif self.strategy == self.Strategy.LEAST_CONNECTIONS:
                return self._select_least_connections(candidates)
            elif self.strategy == self.Strategy.RESOURCE_AWARE:
                return self._select_resource_aware(candidates, requires_gpu)
            elif self.strategy == self.Strategy.PRIORITY_BASED:
                return self._select_priority_based(candidates, task_priority)
            else:
                return candidates[0][1] if candidates else None

    def _select_weighted_round_robin(self, candidates: List[Tuple]) -> AgentPool:
        """加权轮询选择"""
        # 简化实现：轮询选择
        return candidates[0][1]

    def _select_least_connections(self, candidates: List[Tuple]) -> AgentPool:
        """最少连接选择"""
        min_connections = float("inf")
        selected = None

        for pool_type, pool in candidates:
            active_count = sum(1 for a in pool._agents.values() if a.status == AgentStatus.ACTIVE)
            if active_count < min_connections:
                min_connections = active_count
                selected = pool

        return selected

    def _select_resource_aware(self, candidates: List[Tuple], requires_gpu: bool) -> AgentPool:
        """资源感知选择"""
        from .agent_resource_control import HardwareMonitor

        best_pool = None
        best_score = float("-inf")

        for pool_type, pool in candidates:
            # 计算评分
            score = 100.0

            # 活跃度评分
            active_count = sum(1 for a in pool._agents.values() if a.status == AgentStatus.ACTIVE)
            active_ratio = active_count / max(len(pool._agents), 1)
            score -= active_ratio * 50

            # 任务负载评分
            total_tasks = sum(a.task_count for a in pool._agents.values())
            avg_tasks = total_tasks / max(len(pool._agents), 1)
            score -= avg_tasks * 5

            if score > best_score:
                best_score = score
                best_pool = pool

        return best_pool

    def _select_priority_based(self, candidates: List[Tuple], task_priority: ResourcePriority) -> AgentPool:
        """优先级调度选择"""
        # 根据优先级匹配池类型
        priority_pool_map = {
            ResourcePriority.CRITICAL: AgentPoolType.COMPUTE,
            ResourcePriority.HIGH: AgentPoolType.HEAVY,
            ResourcePriority.NORMAL: AgentPoolType.LIGHT,
            ResourcePriority.LOW: AgentPoolType.LIGHT,
            ResourcePriority.BATCH: AgentPoolType.LIGHT,
        }

        target_pool_type = priority_pool_map.get(task_priority, AgentPoolType.LIGHT)

        # 查找匹配的池
        for pool_type, pool in candidates:
            if pool_type == target_pool_type:
                return pool

        # 降级选择
        return candidates[0][1] if candidates else None

    def dispatch_task(self, task: Dict[str, Any]) -> Optional[str]:
        """
        分发任务到最佳智能体

        Args:
            task: 任务信息，包含 priority, requires_gpu, requirements 等

        Returns:
            被分配的智能体ID，或None表示无可用智能体
        """
        priority = ResourcePriority(task.get("priority", "normal"))
        requires_gpu = task.get("requires_gpu", False)

        pool = self.select_pool(priority, requires_gpu)
        if not pool:
            return None

        with pool._lock:
            # 查找可用的智能体
            for agent_id, agent in pool._agents.items():
                if agent.status in (AgentStatus.IDLE, AgentStatus.ACTIVE) and agent.task_count < agent.max_tasks:
                    # 分配任务
                    agent.task_count += 1
                    agent.status = AgentStatus.ACTIVE
                    agent.last_active = time.time()
                    self._connection_counts[agent_id] += 1
                    logger.debug(f"任务已分配给智能体 {agent_id}")
                    return agent_id

        return None

    def get_load_stats(self) -> Dict[str, Any]:
        """获取负载统计"""
        with self._lock:
            stats = {}
            for pool_type, pool in self._pools.items():
                with pool._lock:
                    total = len(pool._agents)
                    active = sum(1 for a in pool._agents.values() if a.status == AgentStatus.ACTIVE)
                    idle = sum(1 for a in pool._agents.values() if a.status == AgentStatus.IDLE)
                    sleeping = sum(1 for a in pool._agents.values() if a.status == AgentStatus.SLEEPING)

                    stats[pool_type.value] = {
                        "total": total,
                        "active": active,
                        "idle": idle,
                        "sleeping": sleeping,
                        "utilization": active / max(total, 1),
                    }

            return {"strategy": self.strategy.value, "pools": stats}

# ==================== 过载熔断器 ====================

class CircuitBreaker:
    """
    过载熔断器

    实现熔断器模式，防止系统过载：
    - CLOSED: 正常状态，统计失败率
    - OPEN: 熔断状态，拒绝请求
    - HALF_OPEN: 半开状态，尝试恢复
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

        self._lock = threading.RLock()
        self._call_history: List[bool] = []

        logger.info(f"CircuitBreaker [{name}] 初始化完成")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器执行调用

        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitOpenException: 熔断器打开时抛出
        """
        with self._lock:
            # 检查熔断状态
            if self.state == CircuitState.OPEN:
                # 检查是否超时
                if self._last_failure_time and time.time() - self._last_failure_time >= self.config.timeout:
                    logger.info(f"CircuitBreaker [{self.name}] 进入半开状态")
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitOpenException(f"CircuitBreaker [{self.name}] is OPEN")

            # 半开状态检查最大调用数
            if self.state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenException(f"CircuitBreaker [{self.name}] half_open max calls reached")
                self._half_open_calls += 1

        # 执行调用
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def _record_success(self):
        """记录成功"""
        with self._lock:
            self._failure_count = 0
            self._success_count += 1
            self._call_history.append(True)

            # 半开状态连续成功切换到关闭
            if self.state == CircuitState.HALF_OPEN and self._success_count >= self.config.success_threshold:
                logger.info(f"CircuitBreaker [{self.name}] 恢复到关闭状态")
                self.state = CircuitState.CLOSED
                self._success_count = 0

            self._trim_history()

    def _record_failure(self):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._success_count = 0
            self._last_failure_time = time.time()
            self._call_history.append(False)

            # 失败次数超阈值切换到打开
            if self.state == CircuitState.CLOSED and self._failure_count >= self.config.failure_threshold:
                logger.warning(f"CircuitBreaker [{self.name}] 打开（失败次数: {self._failure_count}）")
                self.state = CircuitState.OPEN

            self._trim_history()

    def _trim_history(self):
        """修剪历史记录"""
        max_history = max(self.config.volume_threshold * 2, 100)
        if len(self._call_history) > max_history:
            self._call_history = self._call_history[-max_history:]

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计"""
        with self._lock:
            total_calls = len(self._call_history)
            failures = sum(1 for x in self._call_history if not x)
            failure_rate = failures / max(total_calls, 1)

            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_calls": total_calls,
                "failure_rate": failure_rate,
                "last_failure_time": self._last_failure_time,
            }

    def reset(self):
        """重置熔断器"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._call_history.clear()
            logger.info(f"CircuitBreaker [{self.name}] 已重置")

class CircuitOpenException(Exception):
    """熔断器打开异常"""

    pass

# ==================== 低配设备适配器 ====================

class LowPerfAdapter:
    """
    低配设备适配器

    根据设备性能自动调整运行策略：
    - CPU限制
    - 内存限制
    - 并发限制
    - 功能降级
    """

    def __init__(self, perf_mode: PerfMode = PerfMode.BALANCED):
        self.perf_mode = perf_mode
        self._original_settings: Dict[str, Any] = {}

        # 性能配置
        self._perf_configs = {
            PerfMode.HIGH_PERFORMANCE: {
                "cpu_limit_percent": 100,
                "max_concurrent_tasks": 100,
                "cache_size_mb": 1024,
                "enable_gpu": True,
                "feature_flags": ["all"],
            },
            PerfMode.BALANCED: {
                "cpu_limit_percent": 70,
                "max_concurrent_tasks": 50,
                "cache_size_mb": 512,
                "enable_gpu": True,
                "feature_flags": ["core", "advanced"],
            },
            PerfMode.LOW_PERFORMANCE: {
                "cpu_limit_percent": 40,
                "max_concurrent_tasks": 20,
                "cache_size_mb": 256,
                "enable_gpu": False,
                "feature_flags": ["core"],
            },
            PerfMode.POWER_SAVING: {
                "cpu_limit_percent": 20,
                "max_concurrent_tasks": 5,
                "cache_size_mb": 128,
                "enable_gpu": False,
                "feature_flags": ["minimal"],
            },
        }

        self._current_config = self._perf_configs[self.perf_mode].copy()
        logger.info(f"LowPerfAdapter 初始化，性能模式: {perf_mode.value}")

    def set_mode(self, mode: PerfMode) -> APIResponse:
        """设置性能模式"""
        try:
            old_mode = self.perf_mode
            self.perf_mode = mode
            self._current_config = self._perf_configs[mode].copy()

            logger.info(f"性能模式切换: {old_mode.value} -> {mode.value}")
            return APIResponse(success=True, data={"mode": mode.value, "config": self._current_config})
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {"mode": self.perf_mode.value, "config": self._current_config.copy()}

    def apply_low_perf_mode(self) -> APIResponse:
        """应用低配模式"""
        return self.set_mode(PerfMode.LOW_PERFORMANCE)

    def should_use_gpu(self) -> bool:
        """判断是否应使用GPU"""
        return self._current_config.get("enable_gpu", False)

    def get_cpu_limit(self) -> float:
        """获取CPU限制"""
        return self._current_config.get("cpu_limit_percent", 100)

    def get_max_concurrent_tasks(self) -> int:
        """获取最大并发任务数"""
        return self._current_config.get("max_concurrent_tasks", 50)

    def get_feature_flags(self) -> List[str]:
        """获取功能开关"""
        return self._current_config.get("feature_flags", ["core"])

    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        flags = self.get_feature_flags()
        return "all" in flags or feature in flags

class QuotaEnforcer:
    """配额执行器 - 按策略对智能体资源使用进行限额和超额管控。

    企业场景：250万级智能体集群中，防止个别Agent占用过多CPU/内存/网络，
    支持硬限制（直接拒绝）和软限制（降速+告警），以及突发配额借用。
    """

    def __init__(self):
        self._quotas: Dict[str, Dict] = {}  # agent_id -> {resource: {limit, used}}
        self._pool_capacity: Dict[str, float] = {}  # resource -> total capacity
        self._violation_log: deque = deque(maxlen=5000)
        self._borrow_records: Dict[str, Dict] = {}

    def set_quota(self, agent_id: str, resource: str, hard_limit: float, soft_limit: float = None):
        """设置Agent的资源配额"""
        self._quotas.setdefault(agent_id, {})[resource] = {
            "hard_limit": hard_limit,
            "soft_limit": soft_limit or hard_limit * 0.8,
            "used": 0,
            "violation_count": 0,
            "last_check": time.time(),
        }

    def set_pool_capacity(self, resource: str, total: float):
        """设置资源池总容量"""
        self._pool_capacity[resource] = total

    def check_and_consume(self, agent_id: str, resource: str, amount: float) -> Dict:
        """检查并消费配额，返回是否允许"""
        quota = self._quotas.get(agent_id, {}).get(resource)
        if not quota:
            return {"allowed": True, "reason": "no_quota_set"}

        new_used = quota["used"] + amount
        # 硬限制检查
        if new_used > quota["hard_limit"]:
            quota["violation_count"] += 1
            self._violation_log.append(
                {
                    "agent": agent_id,
                    "resource": resource,
                    "attempted": amount,
                    "limit": quota["hard_limit"],
                    "type": "hard_limit",
                    "ts": time.time(),
                }
            )
            return {
                "allowed": False,
                "reason": "hard_limit_exceeded",
                "current": quota["used"],
                "limit": quota["hard_limit"],
            }

        # 软限制告警
        warning = False
        if new_used > quota["soft_limit"]:
            warning = True
            self._violation_log.append(
                {
                    "agent": agent_id,
                    "resource": resource,
                    "attempted": amount,
                    "soft_limit": quota["soft_limit"],
                    "type": "soft_limit",
                    "ts": time.time(),
                }
            )

        quota["used"] = new_used
        quota["last_check"] = time.time()
        return {
            "allowed": True,
            "warning": warning,
            "current": round(new_used, 2),
            "remaining": round(quota["hard_limit"] - new_used, 2),
        }

    def request_burst(self, agent_id: str, resource: str, amount: float, duration_sec: int = 300) -> Dict:
        """请求突发配额借用（从全局池借）"""
        pool_used = sum(q[resource]["used"] for q in self._quotas.values() if resource in q)
        pool_total = self._pool_capacity.get(resource, float("inf"))
        available = pool_total - pool_used
        if available < amount:
            return {"approved": False, "reason": "pool_exhausted", "available": available, "requested": amount}
        # 批准借用
        self._borrow_records[f"{agent_id}:{resource}:{int(time.time())}"] = {
            "agent": agent_id,
            "resource": resource,
            "amount": amount,
            "expires": time.time() + duration_sec,
        }
        return {"approved": True, "amount": amount, "expires_in": duration_sec}

    def get_utilization_report(self) -> Dict:
        """生成资源利用率报告"""
        report = {}
        for resource in self._pool_capacity:
            used = sum(q[resource]["used"] for q in self._quotas.values() if resource in q)
            total = self._pool_capacity[resource]
            report[resource] = {
                "used": round(used, 2),
                "total": total,
                "utilization": round(used / total * 100, 1) if total > 0 else 0,
                "agent_count": len([q for q in self._quotas.values() if resource in q]),
            }
        return report

# ==================== 统一入口控制器 ====================

class AgentResourceController(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    智能体资源控制器 - 统一入口

    整合所有资源管控组件，提供统一的API接口
    命名空间: evo.resource.agent.*
    """

    MODULE_ID = "evo.resource.agent"
    MODULE_NAME = "AgentResourceControl"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__()
        if ENTERPRISE_AVAILABLE:
            EnterpriseModule.__init__(self)
        self.version = "6.28.0"
        self.namespace = "evo.resource.agent"

        # 初始化核心组件
        self.hardware_monitor = HardwareMonitor(sample_interval=1.0)
        self.quota_manager = ResourceQuotaManager()
        self.low_perf_adapter = LowPerfAdapter()
        self.load_balancer = LoadBalancer()

        # 池管理
        self._pools: Dict[AgentPoolType, AgentPool] = {}
        self._initialize_default_pools()

        # 熔断器
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # 审计日志
        self._audit_log: List[Dict] = []
        self._audit_lock = threading.Lock()
        self._max_audit_entries = 10000

        # API限流
        self._rate_limits: Dict[str, Dict] = {}
        self._rate_limit_lock = threading.Lock()

        # 启动
        self.hardware_monitor.start_monitoring()
        for pool in self._pools.values():
            pool.start()

        # 注册池到负载均衡器
        for pool in self._pools.values():
            self.load_balancer.register_pool(pool)

        logger.info(f"AgentResourceController v{self.version} 初始化完成")

    def _initialize_default_pools(self):
        """初始化默认池"""
        pool_configs = [
            PoolConfig(
                pool_id="pool_light",
                pool_type=AgentPoolType.LIGHT,
                name="轻量任务池",
                description="处理文本处理、简单查询等轻量任务",
                min_size=1000,
                max_size=1000000,
                initial_size=10000,
            ),
            PoolConfig(
                pool_id="pool_heavy",
                pool_type=AgentPoolType.HEAVY,
                name="重度开发池",
                description="处理代码生成、复杂推理等重度任务",
                min_size=500,
                max_size=500000,
                initial_size=1000,
            ),
            PoolConfig(
                pool_id="pool_compute",
                pool_type=AgentPoolType.COMPUTE,
                name="运算池",
                description="处理数据分析、模型推理等运算密集任务",
                min_size=100,
                max_size=100000,
                initial_size=200,
            ),
        ]

        for config in pool_configs:
            pool = AgentPool(config, self.quota_manager)
            self._pools[config.pool_type] = pool

    def shutdown(self):
        """关闭控制器"""
        logger.info("正在关闭 AgentResourceController...")

        self.hardware_monitor.stop_monitoring()
        for pool in self._pools.values():
            pool.stop()

        logger.info("AgentResourceController 已关闭")

    # ==================== API 接口实现 ====================

    # GET /api/evo/resource/hardware/status
    def get_hardware_status(self) -> APIResponse:
        """获取硬件资源状态"""
        try:
            data = self.hardware_monitor.get_resource_status()
            return APIResponse(success=True, data=data)
        except Exception as e:
            logger.error(f"获取硬件状态失败: {e}")
            return APIResponse(success=False, error=str(e))

    # PUT /api/evo/resource/pool/limit
    def set_pool_limit(self, pool_type: str, **limits) -> APIResponse:
        """设置池资源限制"""
        try:
            pool_type_enum = AgentPoolType(pool_type)
            return self.quota_manager.set_pool_limit(pool_type_enum, **limits)
        except ValueError:
            return APIResponse(success=False, error=f"无效的池类型: {pool_type}", code=400)
        except Exception as e:
            logger.error(f"设置池限制失败: {e}")
            return APIResponse(success=False, error=str(e))

    # PUT /api/evo/resource/agent/quota
    def update_agent_quota(self, agent_id: str, pool_type: str, **quota) -> APIResponse:
        """更新智能体配额"""
        try:
            pool_type_enum = AgentPoolType(pool_type)
            pool = self._pools.get(pool_type_enum)
            if not pool:
                return APIResponse(success=False, error=f"池 {pool_type} 不存在", code=404)

            return pool.update_agent_quota(agent_id, **quota)
        except ValueError:
            return APIResponse(success=False, error=f"无效的池类型: {pool_type}", code=400)
        except Exception as e:
            logger.error(f"更新智能体配额失败: {e}")
            return APIResponse(success=False, error=str(e))

    # POST /api/evo/resource/agent/sleep
    def sleep_agent(self, agent_id: str, pool_type: str) -> APIResponse:
        """使智能体休眠"""
        try:
            pool_type_enum = AgentPoolType(pool_type)
            pool = self._pools.get(pool_type_enum)
            if not pool:
                return APIResponse(success=False, error=f"池 {pool_type} 不存在", code=404)

            return pool.sleep_agent(agent_id)
        except ValueError:
            return APIResponse(success=False, error=f"无效的池类型: {pool_type}", code=400)
        except Exception as e:
            logger.error(f"智能体休眠失败: {e}")
            return APIResponse(success=False, error=str(e))

    # POST /api/evo/resource/agent/wake
    def wake_agent(self, agent_id: str, pool_type: str) -> APIResponse:
        """唤醒智能体"""
        try:
            pool_type_enum = AgentPoolType(pool_type)
            pool = self._pools.get(pool_type_enum)
            if not pool:
                return APIResponse(success=False, error=f"池 {pool_type} 不存在", code=404)

            return pool.wake_agent(agent_id)
        except ValueError:
            return APIResponse(success=False, error=f"无效的池类型: {pool_type}", code=400)
        except Exception as e:
            logger.error(f"智能体唤醒失败: {e}")
            return APIResponse(success=False, error=str(e))

    # PATCH /api/evo/resource/mode/lowperf
    def set_low_perf_mode(self, enabled: bool = True) -> APIResponse:
        """设置低配设备适配模式"""
        try:
            if enabled:
                return self.low_perf_adapter.apply_low_perf_mode()
            else:
                return self.low_perf_adapter.set_mode(PerfMode.BALANCED)
        except Exception as e:
            logger.error(f"设置低配模式失败: {e}")
            return APIResponse(success=False, error=str(e))

    # ==================== 扩展 API ====================

    def register_agent(self, agent_id: str, pool_type: str, metadata: Dict = None) -> APIResponse:
        """注册智能体"""
        metrics_collector.counter("resource_register_agent_total", labels={"pool_type": pool_type})
        self.audit("register_agent", f"agent_id={agent_id}, pool_type={pool_type}")
        try:
            pool_type_enum = AgentPoolType(pool_type)
            pool = self._pools.get(pool_type_enum)
            if not pool:
                return APIResponse(success=False, error=f"池 {pool_type} 不存在", code=404)

            agent = pool.register_agent(agent_id, metadata)
            return APIResponse(success=True, data=agent.to_dict())
        except ValueError:
            return APIResponse(success=False, error=f"无效的池类型: {pool_type}", code=400)
        except Exception as e:
            logger.error(f"注册智能体失败: {e}")
            return APIResponse(success=False, error=str(e))

    def dispatch_task(self, task: Dict) -> APIResponse:
        """分发任务"""
        metrics_collector.counter("resource_dispatch_total", labels={"task_type": task.get("type", "unknown")})
        self.audit("dispatch_task", f"task_type={task.get('type', '')}")
        try:
            agent_id = self.load_balancer.dispatch_task(task)
            if agent_id:
                return APIResponse(success=True, data={"agent_id": agent_id})
            else:
                return APIResponse(success=False, error="无可用智能体", code=503)
        except Exception as e:
            logger.error(f"任务分发失败: {e}")
            return APIResponse(success=False, error=str(e))

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态"""
        hardware = self.hardware_monitor.get_current_metrics()

        pool_stats = {}
        for pool_type, pool in self._pools.items():
            pool_stats[pool_type.value] = pool.get_pool_stats()

        load_stats = self.load_balancer.get_load_stats()

        return {
            "version": self.version,
            "namespace": self.namespace,
            "hardware": hardware.to_dict(),
            "pools": pool_stats,
            "load_balancer": load_stats,
            "perf_mode": self.low_perf_adapter.perf_mode.value,
            "uptime": time.time(),
        }

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._circuit_breakers.get(name)

    def create_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """创建熔断器"""
        cb = CircuitBreaker(name, config)
        self._circuit_breakers[name] = cb
        self._record_audit("circuit_breaker_created", {"name": name})
        return cb

    # ==================== 审计日志 ====================

    def _record_audit(self, action: str, details: Dict = None) -> None:
        """记录资源操作审计"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
        }
        with self._audit_lock:
            self._audit_log.append(entry)
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries :]

    def get_audit_log(self, action: str = None, limit: int = 100) -> List[Dict]:
        """查询审计日志"""
        with self._audit_lock:
            logs = self._audit_log
            if action:
                logs = [e for e in logs if e["action"] == action]
            return logs[-limit:]

    # ==================== API限流 ====================

    def _check_rate_limit(self, client_id: str, limit: int = 100, window: int = 60) -> bool:
        """检查API限流"""
        now = time.time()
        with self._rate_limit_lock:
            if client_id not in self._rate_limits:
                self._rate_limits[client_id] = {"count": 0, "window_start": now}
            entry = self._rate_limits[client_id]
            if now - entry["window_start"] > window:
                entry["count"] = 0
                entry["window_start"] = now
            if entry["count"] >= limit:
                return False
            entry["count"] += 1
            return True

    def get_rate_limit_status(self, client_id: str) -> Dict:
        """获取限流状态"""
        with self._rate_limit_lock:
            entry = self._rate_limits.get(client_id)
            if not entry:
                return {"client": client_id, "limited": False, "count": 0}
            elapsed = time.time() - entry["window_start"]
            return {
                "client": client_id,
                "limited": entry["count"] >= 100,
                "count": entry["count"],
                "elapsed": round(elapsed, 1),
            }

            # ==================== 导出定义 ====================

            __all__ = [
                # 版本信息
                "__version__",
                "VERSION",
                # 枚举
                "AgentPoolType",
                "AgentStatus",
                "ResourcePriority",
                "CircuitState",
                "PerfMode",
                # 数据类
                "HardwareMetrics",
                "AgentInfo",
                "ResourceQuota",
                "PoolConfig",
                "CircuitBreakerConfig",
                "APIResponse",
                # 异常
                "CircuitOpenException",
                # 核心类
                "HardwareMonitor",
                "ResourceQuotaManager",
                "AgentPool",
                "LoadBalancer",
                "CircuitBreaker",
                "LowPerfAdapter",
                "AgentResourceController",
            ]

        __version__ = "V0.1"

VERSION = "V0.1"

# ==================== 使用示例 ====================

if __name__ == "__main__":
    print(f"AUTO EVO AI v{VERSION} - 智能体集群资源精细化管控模块")
    print("=" * 60)

    # 创建控制器
    controller = AgentResourceController()

    try:
        pass
        # 示例1: 获取硬件状态
        print("\n[1] 硬件资源状态:")
        status = controller.get_hardware_status()
        if status.success:
            metrics = status.data["current"]
            print(f"  CPU: {metrics['cpu_percent']:.1f}%")
            print(f"  内存: {metrics['memory_percent']:.1f}%")
            print(f"  GPU: {metrics['gpu_percent']:.1f}%")

        # 示例2: 注册智能体
        print("\n[2] 注册智能体到轻量池:")
        result = controller.register_agent("agent_001", "light", {"purpose": "test"})
        if result.success:
            print(f"  成功注册: {result.data['agent_id']}")

        # 示例3: 任务分发
        print("\n[3] 任务分发:")
        task_result = controller.dispatch_task({"priority": "normal", "requires_gpu": False})
        if task_result.success:
            print(f"  分配到: {task_result.data['agent_id']}")

        # 示例4: 休眠/唤醒
        print("\n[4] 智能体休眠:")
        sleep_result = controller.sleep_agent("agent_001", "light")
        print(f"  结果: {sleep_result.success}")

        print("\n[5] 智能体唤醒:")
        wake_result = controller.wake_agent("agent_001", "light")
        print(f"  结果: {wake_result.success}")

        # 示例5: 系统状态
        print("\n[6] 系统整体状态:")
        sys_status = controller.get_system_status()
        print(f"  版本: {sys_status['version']}")
        print(f"  性能模式: {sys_status['perf_mode']}")
        print(f"  池数量: {len(sys_status['pools'])}")

    finally:
        controller.shutdown()
        print("\n控制器已关闭")

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

    def health_check(self) -> dict:
        """Health check for agent_resource_control."""
        return {
            "status": "healthy",
            "module": self.__class__.__name__,
            "uptime": getattr(self, "_start_time", 0) and (time.time() - self._start_time) or 0,
        }

    def initialize(self) -> dict:
        """Initialize agent_resource_control."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self.logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentResourceController
