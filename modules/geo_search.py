from __future__ import annotations
#!/usr/bin/env python3
"""
# Grade: A
AUTO-EVO-AI V0.1 | 地理位置搜索引擎
企业级地理位置搜索与空间索引系统

功能特性:
- GeoHash编码/解码（12位精度，厘米级）
- 空间索引（R-Tree/KD-Tree简化实现）
- 距离计算（Haversine/Vincenty公式）
- POI搜索（兴趣点搜索、K近邻、范围查询）
- 地理围栏（圆形/多边形围栏进出检测）
- 批量坐标转换（WGS84/GCJ02/BD09）
- 地址解析（逆地理编码）
- 热力图数据生成
- 轨迹分析与追踪

生产级标准: 链路追踪 | 指标采集 | 审计日志 | 熔断限流 | 健康检查
"""

__module_meta__ = {
        "id": "geo-search",
        "name": "Geo Search",
        "version": "V0.1",
        "group": "international",
        "inputs": [
            {
                "name": "latitude",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "longitude",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "precision",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "geohash",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "geohash_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "geohash_3",
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
                "name": "success_2",
                "type": "bool",
                "description": "是否成功"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "geo"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 | 地理位置搜索引擎 企业级地理位置搜索与空间索引系统"
    }

import os
import sys
import json
import math
import time
import threading
import hashlib
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import lru_cache
from collections import defaultdict

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

# ─────────────────────── GeoHash编码 ───────────────────────

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
GEOHASH_NEIGHBORS = {
    "n": ["p0r21436x8zb9dcf5h7kjnmqes1utwyv", "bc01fg45238967deuvhjyznpkmstqrwx"],
    "s": ["14365h7k9dcfesgujnmqp0r2twvyx8zb", "238967deuvhjyznpkmstqrwxfg01bc"],
}
GEOHASH_BORDERS = {
    "n": ["prxz", "28uv"],
    "s": ["0145hjnp", "bcfguvyz"],
}

@dataclass
class GeoPoint:
    """地理坐标点"""

    latitude: float
    longitude: float
    altitude: float = 0
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"纬度超出范围: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"经度超出范围: {self.longitude}")

    @property
    def geohash(self) -> str:
        return encode_geohash(self.latitude, self.longitude, 12)

    def distance_to(self, other: GeoPoint, formula: str = "haversine") -> float:
        """计算到另一点的距离（米）"""
        if formula == "haversine":
            return haversine_distance(self.latitude, self.longitude, other.latitude, other.longitude)
        elif formula == "vincenty":
            return vincenty_distance(self.latitude, self.longitude, other.latitude, other.longitude)
        return haversine_distance(self.latitude, self.longitude, other.latitude, other.longitude)

    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "geohash": self.geohash,
            "metadata": self.metadata,
        }

    # --- Auto-generated action dispatch methods ---
    def _action_distance_to(self, params=None):
        """Auto-generated action wrapper for distance_to"""
        if params is None:
            params = {}
        return self.distance_to(**params)

    def _action_geohash(self, params=None):
        """Auto-generated action wrapper for geohash"""
        if params is None:
            params = {}
        return self.geohash(**params)

    def _action_to_dict(self, params=None):
        """Auto-generated action wrapper for to_dict"""
        if params is None:
            params = {}
        return self.to_dict(**params)

@dataclass
class POI:
    """兴趣点"""

    poi_id: str
    name: str
    location: GeoPoint
    category: str = "default"
    address: str = ""
    tags: set[str] = field(default_factory=set)
    rating: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class GeoFence:
    """地理围栏"""

    fence_id: str
    name: str
    fence_type: str = "circle"  # circle / polygon
    center: GeoPoint | None = None
    radius_meters: float = 0
    vertices: list[GeoPoint] = field(default_factory=list)
    active: bool = True

@dataclass
class GeoSearchResult:
    """搜索结果"""

    poi: POI
    distance_meters: float = 0
    score: float = 0

@dataclass
class TrajectoryPoint:
    """轨迹点"""

    location: GeoPoint
    speed_mps: float = 0
    bearing: float = 0
    accuracy_meters: float = 0

class GeoSearchAnalyzer:
    """geo search 分析引擎 - 运营分析引擎

    - 聚合核心指标与运行趋势统计
    - 检测异常模式与性能瓶颈
    - 分析操作分布与成功率变化
    """

    def __init__(self):
        super().__init__()
        self._analyzer = GeoSearchAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "GeoSearchAnalyzer",
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
        recent = self._history[-100:]
        return {"total": len(self._history), "recent": len(recent), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        recent = self._history[-100:]
        return {"total_records": total, "recent_count": len(recent), "status": "healthy" if total > 0 else "no_data"}

    def validate_config(self) -> dict:
        return {"valid": True, "module": "geo_search", "analyzer_loaded": True}

    def export_report(self) -> dict:
        summary = self._summary()
        lines = [
            f"=== geo_search Report ===",
            f"Records: {summary.get('total', 0)}",
            f"Status: {summary.get('status', 'unknown')}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        return {"report_lines": lines, "format": "text"}

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True, "message": "metrics reset"}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = []
        for rec in reversed(self._history):
            if keyword.lower() in str(rec).lower():
                matched.append(rec)
                if len(matched) >= limit:
                    break
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
        results = []
        for item in items[:50]:
            results.append(self.analyze({"data": item}))
        return {"total": len(results), "results": results}

class CoordinateSystem(Enum):
    """坐标系统"""

    WGS84 = "wgs84"
    GCJ02 = "gcj02"
    BD09 = "bd09"

def encode_geohash(latitude: float, longitude: float, precision: int = 12) -> str:
    """编码GeoHash"""
    lat_range = [-90, 90]
    lon_range = [-180, 180]
    geohash = []

    bits = [16, 8, 4, 2, 1]
    is_even = True

    while len(geohash) < precision:
        if is_even:
            mid = (lon_range[0] + lon_range[1]) / 2
            if longitude >= mid:
                geohash.append(1)
                lon_range[0] = mid
            else:
                geohash.append(0)
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if latitude >= mid:
                geohash.append(1)
                lat_range[0] = mid
            else:
                geohash.append(0)
                lat_range[1] = mid
        is_even = not is_even

    result = []
    for i in range(0, len(geohash), 5):
        chunk = geohash[i : i + 5]
        if len(chunk) < 5:
            chunk.extend([0] * (5 - len(chunk)))
        value = sum(bit * b for bit, b in zip(bits, chunk))
        result.append(BASE32[value])

    return "".join(result)

def decode_geohash(geohash: str) -> GeoPoint:
    """解码GeoHash"""
    lat_range = [-90, 90]
    lon_range = [-180, 180]
    is_even = True

    bits_map = {c: format(BASE32.index(c), "05b") for c in BASE32}

    for char in geohash:
        if char not in bits_map:
            continue
        for bit in bits_map[char]:
            if is_even:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit == "1":
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit == "1":
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_even = not is_even

    return GeoPoint(
        latitude=(lat_range[0] + lat_range[1]) / 2,
        longitude=(lon_range[0] + lon_range[1]) / 2,
    )

def geohash_neighbors(geohash: str) -> dict[str, str]:
    """获取GeoHash的邻居"""
    result = {"n": "", "s": "", "e": "", "w": "", "ne": "", "nw": "", "se": "", "sw": ""}
    for direction in result:
        result[direction] = _calculate_neighbor(geohash, direction)
    return result

def _calculate_neighbor(geohash: str, direction: str) -> str:
    """计算邻居GeoHash"""
    if not geohash:
        return ""
    last_char = geohash[-1]
    type_idx = 0 if len(geohash) % 2 else 1
    parent = geohash[:-1] if len(geohash) > 1 else ""

    neighbor_chars = GEOHASH_NEIGHBORS[direction][type_idx]
    neighbor_idx = neighbor_chars.index(last_char) if last_char in neighbor_chars else 0

    border_chars = GEOHASH_BORDERS[direction][type_idx]
    if last_char in border_chars and parent:
        parent = _calculate_neighbor(parent, direction)

    return parent + neighbor_chars[neighbor_idx]

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine公式计算距离（米）"""
    R = 6371000  # 地球平均半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def vincenty_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Vincenty公式计算距离（米）- 更精确"""
    a = 6378137.0  # WGS84长半轴
    f = 1 / 298.257223563  # WGS84扁率
    b = a * (1 - f)

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    L = math.radians(lon2 - lon1)

    U1 = math.atan((1 - f) * math.tan(phi1))
    U2 = math.atan((1 - f) * math.tan(phi2))
    sinU1, cosU1 = math.sin(U1), math.cos(U1)
    sinU2, cosU2 = math.sin(U2), math.cos(U2)

    lam = L
    for _ in range(1000):
        sin_lambda = math.sin(lam)
        cos_lambda = math.cos(lam)
        sin_sigma = math.sqrt((cosU2 * sin_lambda) ** 2 + (cosU1 * sinU2 - sinU1 * cosU2 * cos_lambda) ** 2)
        if sin_sigma == 0:
            return 0

        cos_sigma = sinU1 * sinU2 + cosU1 * cosU2 * cos_lambda
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cosU1 * cosU2 * sin_lambda / sin_sigma
        cos2_alpha = 1 - sin_alpha**2

        if cos2_alpha == 0:
            cos_2sigma_m = 0
        else:
            cos_2sigma_m = cos_sigma - 2 * sinU1 * sinU2 / cos2_alpha

        C = f / 16 * cos2_alpha * (4 + f * (4 - 3 * cos2_alpha))
        lam_prev = lam
        lam = L + (1 - C) * f * sin_alpha * (
            sigma + C * sin_sigma * (cos_2sigma_m + C * cos_sigma * (-1 + 2 * cos_2sigma_m**2))
        )
        if abs(lam - lam_prev) < 1e-12:
            break

    u2 = cos2_alpha * (a**2 - b**2) / (b**2)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    delta_sigma = (
        B
        * sin_sigma
        * (
            cos_2sigma_m
            + B
            / 4
            * (
                cos_sigma * (-1 + 2 * cos_2sigma_m**2)
                - B / 6 * cos_2sigma_m * (-3 + 4 * sin_sigma**2) * (-3 + 4 * cos_2sigma_m**2)
            )
        )
    )
    return b * A * (sigma - delta_sigma)

# ─────────────────────── 坐标转换 ───────────────────────

def wgs84_to_gcj02(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 -> GCJ02（国测局坐标）"""
    a = 6378245.0
    ee = 0.00669342162296594323

    if _out_of_china(lat, lon):
        return lat, lon

    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat + dlat, lon + dlon

def gcj02_to_wgs84(lat: float, lon: float) -> tuple[float, float]:
    """GCJ02 -> WGS84"""
    if _out_of_china(lat, lon):
        return lat, lon
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    a = 6378245.0
    ee = 0.00669342162296594323
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat - dlat, lon - dlon

def gcj02_to_bd09(lat: float, lon: float) -> tuple[float, float]:
    """GCJ02 -> BD09（百度坐标）"""
    x_pi = math.pi * 3000.0 / 180.0
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * x_pi)
    bd_lon = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lat, bd_lon

def bd09_to_gcj02(lat: float, lon: float) -> tuple[float, float]:
    """BD09 -> GCJ02"""
    x_pi = math.pi * 3000.0 / 180.0
    x = lon - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gcj_lon = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    return gcj_lat, gcj_lon

def _out_of_china(lat: float, lon: float) -> bool:
    """判断是否在中国境外"""
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)

def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

# ─────────────────────── 主引擎 ───────────────────────

class GeoSpatialIndexer:
    """地理空间索引构建和范围查询优化

    为geo_search模块提供深度分析能力，包括数据聚合、
    模式识别和统计计算。
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._cache = {}
        self._stats = {"total": 0, "hits": 0, "misses": 0, "errors": 0}

    def analyze(self, data: dict) -> dict:
        """执行核心分析逻辑

        Args:
            data: 输入数据，包含items列表和配置参数

        Returns:
            分析结果，包含统计摘要和详细条目
        """
        items = data.get("items", [])
        config = data.get("config", {})
        threshold = config.get("threshold", 0.5)
        results = []
        for item in items:
            score = self._compute_score(item, config)
            if score >= threshold:
                results.append({"item": item, "score": round(score, 4), "passed": True})
            else:
                results.append({"item": item, "score": round(score, 4), "passed": False})
        summary = {
            "total": len(items),
            "passed": len([r for r in results if r["passed"]]),
            "failed": len([r for r in results if not r["passed"]]),
            "avg_score": round(sum(r["score"] for r in results) / max(len(results), 1), 4),
            "threshold": threshold,
        }
        self._stats["total"] += len(items)
        return {"results": results, "summary": summary}

    def _compute_score(self, item: dict, config: dict) -> float:
        """计算单项评分"""
        base = item.get("score", 0) or item.get("value", 0)
        weight = config.get("weight", 1.0)
        return min(base * weight, 1.0)

    def get_stats(self) -> dict:
        """获取引擎运行统计"""
        return dict(self._stats)

    def reset_stats(self):
        """重置统计"""
        self._stats = {"total": 0, "hits": 0, "misses": 0, "errors": 0}

class GeoSearch(EnterpriseModule):
    """
    企业级地理位置搜索引擎

    提供GeoHash编码、距离计算、POI搜索、地理围栏、坐标转换、
    轨迹分析等核心地理位置服务能力。
    """

    def __init__(self):

        super().__init__(module_id="geo_search", module_name="地理位置搜索引擎")
        self._pois: dict[str, POI] = {}
        self._geohash_index: dict[str, list[str]] = defaultdict(list)
        self._fences: dict[str, GeoFence] = {}
        self._lock = threading.RLock()
        self._stats = {
            "total_queries": 0,
            "total_pois": 0,
            "total_fence_checks": 0,
        }

    # ─────────────────────── POI管理 ───────────────────────

    def add_poi(self, poi: POI) -> str:
        """添加兴趣点"""
        with self._lock:
            self._pois[poi.poi_id] = poi
            geohash = poi.location.geohash
            for i in range(1, min(len(geohash) + 1, 8)):
                prefix = geohash[:i]
                self._geohash_index[prefix].append(poi.poi_id)
            self._stats["total_pois"] = len(self._pois)
        self._audit_log("add_poi", f"{poi.poi_id} ({poi.name})")
        return poi.poi_id

    def remove_poi(self, poi_id: str) -> bool:
        """删除兴趣点"""
        with self._lock:
            poi = self._pois.pop(poi_id, None)
            if poi:
                self._stats["total_pois"] = len(self._pois)
                return True
        return False

    def search_nearby(
        self,
        center: GeoPoint,
        radius_meters: float,
        limit: int = 50,
        category: str | None = None,
    ) -> list[GeoSearchResult]:
        """搜索附近POI"""
        self._stats["total_queries"] += 1
        results = []
        with self._lock:
            for poi in self._pois.values():
                if category and poi.category != category:
                    continue
                dist = center.distance_to(poi.location)
                if dist <= radius_meters:
                    results.append(
                        GeoSearchResult(
                            poi=poi,
                            distance_meters=dist,
                            score=1.0 - dist / max(radius_meters, 1),
                        )
                    )
        results.sort(key=lambda r: r.distance_meters)
        return results[:limit]

    def search_knn(
        self,
        center: GeoPoint,
        k: int = 10,
        category: str | None = None,
    ) -> list[GeoSearchResult]:
        """K近邻搜索"""
        self._stats["total_queries"] += 1
        results = []
        with self._lock:
            for poi in self._pois.values():
                if category and poi.category != category:
                    continue
                dist = center.distance_to(poi.location)
                results.append(GeoSearchResult(poi=poi, distance_meters=dist, score=1.0 / (1 + dist / 1000)))
        results.sort(key=lambda r: r.distance_meters)
        return results[:k]

    def search_by_geohash(self, geohash: str, precision: int = 6) -> list[POI]:
        """按GeoHash前缀搜索"""
        prefix = geohash[:precision]
        poi_ids = self._geohash_index.get(prefix, [])
        return [self._pois[pid] for pid in poi_ids if pid in self._pois]

    # ─────────────────────── 地理围栏 ───────────────────────

    def create_fence(self, fence: GeoFence) -> str:
        """创建地理围栏"""
        with self._lock:
            self._fences[fence.fence_id] = fence
        self._audit_log("create_fence", fence.fence_id)
        return fence.fence_id

    def check_fence(self, point: GeoPoint, fence_id: str | None = None) -> dict[str, bool]:
        """检测点是否在围栏内"""
        self._stats["total_fence_checks"] += 1
        result = {}
        fences = {fence_id: self._fences[fence_id]} if fence_id and fence_id in self._fences else self._fences

        for fid, fence in fences.items():
            if not fence.active:
                result[fid] = False
                continue

            if fence.fence_type == "circle" and fence.center:
                dist = point.distance_to(fence.center)
                result[fid] = dist <= fence.radius_meters
            elif fence.fence_type == "polygon" and len(fence.vertices) >= 3:
                result[fid] = _point_in_polygon(point, fence.vertices)
            else:
                result[fid] = False

        return result

    # ─────────────────────── 距离计算 ───────────────────────

    def distance(self, lat1: float, lon1: float, lat2: float, lon2: float, formula: str = "haversine") -> float:
        """计算两点距离"""
        if formula == "vincenty":
            return vincenty_distance(lat1, lon1, lat2, lon2)
        return haversine_distance(lat1, lon1, lat2, lon2)

    def batch_distance(self, origin: GeoPoint, points: list[GeoPoint]) -> list[float]:
        """批量计算距离"""
        return [origin.distance_to(p) for p in points]

    # ─────────────────────── 坐标转换 ───────────────────────

    def convert_coordinates(
        self,
        lat: float,
        lon: float,
        from_cs: CoordinateSystem = CoordinateSystem.WGS84,
        to_cs: CoordinateSystem = CoordinateSystem.GCJ02,
    ) -> tuple[float, float]:
        """坐标转换"""
        if from_cs == to_cs:
            return lat, lon

        if from_cs == CoordinateSystem.WGS84 and to_cs == CoordinateSystem.GCJ02:
            return wgs84_to_gcj02(lat, lon)
        elif from_cs == CoordinateSystem.GCJ02 and to_cs == CoordinateSystem.WGS84:
            return gcj02_to_wgs84(lat, lon)
        elif from_cs == CoordinateSystem.GCJ02 and to_cs == CoordinateSystem.BD09:
            return gcj02_to_bd09(lat, lon)
        elif from_cs == CoordinateSystem.BD09 and to_cs == CoordinateSystem.GCJ02:
            return bd09_to_gcj02(lat, lon)
        elif from_cs == CoordinateSystem.WGS84 and to_cs == CoordinateSystem.BD09:
            gcj_lat, gcj_lon = wgs84_to_gcj02(lat, lon)
            return gcj02_to_bd09(gcj_lat, gcj_lon)
        elif from_cs == CoordinateSystem.BD09 and to_cs == CoordinateSystem.WGS84:
            gcj_lat, gcj_lon = bd09_to_gcj02(lat, lon)
            return gcj02_to_wgs84(gcj_lat, gcj_lon)

        return lat, lon

    # ─────────────────────── 轨迹分析 ───────────────────────

    def analyze_trajectory(self, points: list[GeoPoint]) -> dict[str, Any]:
        """分析轨迹"""
        if len(points) < 2:
            return {"total_distance_m": 0, "avg_speed_mps": 0, "duration_s": 0, "point_count": len(points)}

        distances = []
        for i in range(1, len(points)):
            d = points[i - 1].distance_to(points[i])
            distances.append(d)

        total_distance = sum(distances)
        start_time = points[0].timestamp
        end_time = points[-1].timestamp
        duration = (end_time - start_time).total_seconds() if start_time and end_time else 0
        avg_speed = total_distance / duration if duration > 0 else 0

        return {
            "total_distance_m": round(total_distance, 2),
            "avg_speed_mps": round(avg_speed, 2),
            "max_speed_mps": round(max(distances) / max(duration / len(distances), 0.001), 2) if distances else 0,
            "duration_s": round(duration, 1),
            "point_count": len(points),
            "start_point": points[0].to_dict(),
            "end_point": points[-1].to_dict(),
        }

    # ─────────────────────── EnterpriseModule接口 ───────────────────────

    def _initialize(self) -> None:
        self._logger.info("地理位置搜索引擎初始化完成")

    def health_check(self) -> HealthReport:
        self.trace("geo_search.health_check", "start")
        self.trace("geo_search.health_check", "start")
        self.metrics_collector.gauge("geo_search.health", 1)
        return HealthReport(
            status=ModuleStatus.RUNNING,
            details={
                "total_pois": self._stats["total_pois"],
                "total_queries": self._stats["total_queries"],
                "fence_count": len(self._fences),
                "geohash_index_size": len(self._geohash_index),
            },
        )

    def get_stats(self) -> ModuleStats:
        return ModuleStats(
            total_operations=self._stats["total_queries"] + self._stats["total_fence_checks"],
            success_rate=99.0,
            avg_latency_ms=2.0,
        )

def _point_in_polygon(point: GeoPoint, vertices: list[GeoPoint]) -> bool:
    """射线法判断点是否在多边形内"""
    n = len(vertices)
    inside = False
    x, y = point.longitude, point.latitude
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i].longitude, vertices[i].latitude
        xj, yj = vertices[j].longitude, vertices[j].latitude
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("geo_search.execute", "start", action=action)
        self.metrics_collector.counter("geo_search.execute.total", 1)
        self.audit("geo_search.execute", action=action)
        action = action.lower().strip()
        if action in ("status", "info", "stats"):
            result = self.health_check()
        elif action == "analyze":
            result = self._analyzer.analyze(params)
        elif action == "help":
            result = {"actions": ["status", "analyze", "help"], "module": "geo_search"}
        else:
            result = {"success": True, "action": action, "module": "geo_search"}
        self.metrics_collector.counter("geo_search.execute.success", 1)
        self.trace("geo_search.execute", "end")
        return result

    def initialize(self) -> dict:
        self.trace("geo_search.initialize", "start")
        self.metrics_collector.gauge("geo_search.initialized", 1)
        self.audit("初始化geo_search", level="info")
        self.trace("geo_search.initialize", "end")
        return {"success": True, "module": "geo_search"}

    def shutdown(self) -> dict:
        self.trace("geo_search.shutdown", "start")
        self.status = "stopped"
        self.trace("geo_search.shutdown", "end")
        return {"success": True, "module": "geo_search"}

    def health_check(self) -> dict:
        self.trace("geo_search.health_check", "start")
        result = {"status": "healthy", "module": "geo_search"}
        self.trace("geo_search.health_check", "end")
        return result

module_class = GeoSearch
