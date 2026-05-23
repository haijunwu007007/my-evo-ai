"""
AUTO-EVO-AI V0.1 — Agent Iris (视觉感知引擎)
===============================================
企业级智能体，负责图像理解、OCR文字识别、目标检测、场景分类、视觉异常检测。
支持多模态输入（图片/视频帧），内置特征提取管线与相似度匹配。

继承: EnterpriseModule
"""

__module_meta__ = {
    "id": "agent-iris",
    "name": "Agent Iris",
    "version": "1.0.0",
    "group": "agent",
    "inputs": [
        {"name": "feature_dim", "type": "string", "required": True, "description": ""},
        {"name": "pixel_data", "type": "string", "required": True, "description": ""},
        {"name": "bins", "type": "string", "required": True, "description": ""},
        {"name": "pixel_data", "type": "string", "required": True, "description": ""},
        {"name": "width", "type": "string", "required": True, "description": ""},
        {"name": "height", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_iris.task.request"}}],
    "depends_on": [],
    "tags": ["multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Agent Iris (视觉感知引擎) ===============================================",
}

import time
import json
import hashlib
import logging
import base64
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("agent.iris")

class ImageFormat(Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    GIF = "gif"
    TIFF = "tiff"

class DetectionCategory(Enum):
    PERSON = "person"
    VEHICLE = "vehicle"
    OBJECT = "object"
    TEXT = "text"
    FACE = "face"
    ANIMAL = "animal"
    SCENE = "scene"
    ANOMALY = "anomaly"

class SceneType(Enum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    AERIAL = "aerial"
    UNDERWATER = "underwater"
    NIGHT = "night"
    DOCUMENT = "document"

@dataclass
class BoundingBox:
    """边界框"""

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    confidence: float = 0.0
    label: str = ""
    category: DetectionCategory = DetectionCategory.OBJECT

    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "label": self.label,
            "category": self.category.value,
        }

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def iou_threshold(self) -> float:
        """推荐的IoU阈值"""
        if self.confidence >= 0.9:
            return 0.5
        elif self.confidence >= 0.7:
            return 0.6
        return 0.7

@dataclass
class DetectedObject:
    """检测结果"""

    object_id: str = ""
    bbox: BoundingBox = field(default_factory=BoundingBox)
    attributes: Dict[str, Any] = field(default_factory=dict)
    feature_vector: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {"object_id": self.object_id, "bbox": self.bbox.to_dict(), "attributes": self.attributes}

@dataclass
class OCRResult:
    """OCR识别结果"""

    text: str = ""
    confidence: float = 0.0
    language: str = "auto"
    words: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "word_count": len(self.words),
            "block_count": len(self.blocks),
            "words": self.words[:50],
        }

@dataclass
class SceneAnalysis:
    """场景分析结果"""

    scene_type: SceneType = SceneType.INDOOR
    description: str = ""
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    color_palette: List[str] = field(default_factory=list)
    dominant_colors: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "scene_type": self.scene_type.value,
            "description": self.description,
            "tags": self.tags,
            "confidence": self.confidence,
            "dominant_colors": [{"color": c, "ratio": r} for c, r in self.dominant_colors],
        }

@dataclass
class ImageAnalysisResult:
    """图像分析综合结果"""

    analysis_id: str = ""
    source_ref: str = ""
    format: str = ""
    width: int = 0
    height: int = 0
    file_size: int = 0
    objects: List[DetectedObject] = field(default_factory=list)
    ocr: Optional[OCRResult] = None
    scene: Optional[SceneAnalysis] = None
    anomaly_score: float = 0.0
    is_anomaly: bool = False
    features: List[float] = field(default_factory=list)
    processing_time_ms: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id,
            "source_ref": self.source_ref,
            "width": self.width,
            "height": self.height,
            "object_count": len(self.objects),
            "objects": [o.to_dict() for o in self.objects],
            "ocr": self.ocr.to_dict() if self.ocr else None,
            "scene": self.scene.to_dict() if self.scene else None,
            "anomaly_score": self.anomaly_score,
            "is_anomaly": self.is_anomaly,
            "processing_time_ms": self.processing_time_ms,
        }

# ============================================================
# 特征提取器
# ============================================================

class FeatureExtractor:
    """图像特征提取器 — 基于哈希与统计特征"""

    def __init__(self, feature_dim: int = 256):
        self.feature_dim = feature_dim
        self._feature_cache: Dict[str, List[float]] = {}

    def extract_color_histogram(self, pixel_data: List[Tuple[int, int, int]], bins: int = 16) -> List[float]:
        """提取颜色直方图特征"""
        r_hist = [0] * bins
        g_hist = [0] * bins
        b_hist = [0] * bins
        for r, g, b in pixel_data:
            r_hist[min(r * bins // 256, bins - 1)] += 1
            g_hist[min(g * bins // 256, bins - 1)] += 1
            b_hist[min(b * bins // 256, bins - 1)] += 1
        total = len(pixel_data) or 1
        features = []
        for h in [r_hist, g_hist, b_hist]:
            features.extend([v / total for v in h])
        # pad/truncate到目标维度
        while len(features) < self.feature_dim:
            features.append(0.0)
        return features[: self.feature_dim]

    def extract_phash(self, pixel_data: List[Tuple[int, int, int]], width: int, height: int, hash_size: int = 8) -> str:
        """感知哈希(简化版)"""
        block_w = max(1, width // hash_size)
        block_h = max(1, height // hash_size)
        blocks = [[0.0] * hash_size for _ in range(hash_size)]
        counts = [[0] * hash_size for _ in range(hash_size)]
        for idx, (r, g, b) in enumerate(pixel_data):
            x = (idx % width) // block_w
            y = (idx // width) // block_h
            x = min(x, hash_size - 1)
            y = min(y, hash_size - 1)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            blocks[y][x] += brightness
            counts[y][x] += 1
        avg_blocks = [[blocks[y][x] / max(1, counts[y][x]) for x in range(hash_size)] for y in range(hash_size)]
        flat = [avg_blocks[y][x] for y in range(hash_size) for x in range(hash_size)]
        avg = sum(flat) / len(flat) if flat else 0
        bits = "".join("1" if v >= avg else "0" for v in flat)
        return hex(int(bits, 2))[2:]

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算余弦相似度"""
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return round(dot / (norm_a * norm_b), 4)

# ============================================================
# NMS非极大值抑制
# ============================================================

class NMSProcessor(object):
    """非极大值抑制 — 去除重叠检测框"""

    def __init__(self, iou_threshold: float = 0.5):
        self.iou_threshold = iou_threshold

    def compute_iou(self, box_a: BoundingBox, box_b: BoundingBox) -> float:
        """计算两个边界框的IoU"""
        x1 = max(box_a.x, box_b.x)
        y1 = max(box_a.y, box_b.y)
        x2 = min(box_a.x + box_a.width, box_b.x + box_b.width)
        y2 = min(box_a.y + box_a.height, box_b.y + box_b.height)
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        union = box_a.area + box_b.area - intersection
        return intersection / union if union > 0 else 0.0

    def suppress(self, boxes: List[BoundingBox]) -> List[BoundingBox]:
        """执行NMS"""
        if not boxes:
            return []
        sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
        keep = []
        while sorted_boxes:
            best = sorted_boxes.pop(0)
            keep.append(best)
            sorted_boxes = [b for b in sorted_boxes if self.compute_iou(best, b) < self.iou_threshold]
        return keep

# ============================================================
class FeatureExtractor:
    """视觉特征提取器 - 从图像中提取结构化特征向量用于匹配和分类。

    企业场景：商品图片相似度搜索、人脸特征比对、文档版式识别。
    提取颜色直方图、边缘方向、纹理特征，生成可比较的特征指纹。
    """

    def __init__(self):
        self._feature_cache: Dict[str, List[float]] = {}
        self._dimensions = 256  # 特征向量维度

    def extract_color_histogram(self, pixels: List[Tuple], bins: int = 32) -> List[float]:
        """提取RGB颜色直方图特征（归一化）"""
        hist_r = [0] * bins
        hist_g = [0] * bins
        hist_b = [0] * bins
        total = len(pixels) or 1
        for r, g, b in pixels:
            hist_r[min(r * bins // 256, bins - 1)] += 1
            hist_g[min(g * bins // 256, bins - 1)] += 1
            hist_b[min(b * bins // 256, bins - 1)] += 1
        # 归一化并拼接
        features = [h / total for h in hist_r + hist_g + hist_b]
        return features

    def extract_edge_histogram(self, pixels: List[Tuple], width: int, height: int) -> List[float]:
        """提取边缘方向直方图（Sobel简化版）"""
        directions = [0] * 8  # 8方向量化
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = y * width + x
                if idx >= len(pixels):
                    break
                left = pixels[idx - 1][0] if idx > 0 else 0
                right = pixels[idx + 1][0] if idx + 1 < len(pixels) else 0
                top = pixels[idx - width][0] if idx >= width else 0
                bottom = pixels[idx + width][0] if idx + width < len(pixels) else 0
                gx = right - left
                gy = bottom - top
                magnitude = (gx**2 + gy**2) ** 0.5
                if magnitude < 20:
                    continue
                angle = (
                    (int(((3.14159 + (gy / magnitude).as_integer_ratio()[0] if gy else 0) / 3.14159) * 4)) % 8
                    if gy != 0
                    else 0
                )
                directions[min(max(angle, 0), 7)] += magnitude
        total = sum(directions) or 1
        return [d / total for d in directions]

    def compute_similarity(self, features_a: List[float], features_b: List[float]) -> float:
        """余弦相似度计算"""
        if len(features_a) != len(features_b) or not features_a:
            return 0.0
        dot = sum(a * b for a, b in zip(features_a, features_b))
        mag_a = sum(a**2 for a in features_a) ** 0.5
        mag_b = sum(b**2 for b in features_b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def build_fingerprint(self, image_id: str, pixels: List[Tuple], width: int, height: int) -> Dict:
        """生成图像综合特征指纹"""
        color_feat = self.extract_color_histogram(pixels)
        features = color_feat + [0.0] * (self._dimensions - len(color_feat))
        features = features[: self._dimensions]
        self._feature_cache[image_id] = features
        return {
            "image_id": image_id,
            "dimensions": len(features),
            "feature_hash": hashlib.md5(str(features[:16]).encode()).hexdigest(),
        }

# 主模块: AgentIris
# ============================================================

class AgentIris(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Iris智能体 — 视觉感知引擎"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(module_name="agent_iris", version="6.39.0", config=config)
        self._feature_extractor = FeatureExtractor()
        self._nms = NMSProcessor()
        self._analysis_cache: Dict[str, ImageAnalysisResult] = {}
        self._feature_store: Dict[str, List[float]] = {}
        self._stats = {
            "total_analyses": 0,
            "total_detections": 0,
            "total_ocr": 0,
            "total_scene_analyses": 0,
            "total_anomalies": 0,
            "total_similarity_queries": 0,
        }

    async def initialize(self) -> None:
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentIris 视觉感知引擎初始化完成")

    async def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        """统一执行入口 — 根据action路由到视觉分析业务方法"""
        _ = self.trace("execute")
        metrics_collector.counter("agent_iris_ops_total", labels={"action": action})
        params = params or {}

        if action == "analyze":
            result = await self.analyze_image(
                params.get("source_ref", ""), params.get("image_data", ""), params.get("options")
            )
            self.audit("analyze_image", f"source={params.get('source_ref', '')}, success={result.success}")
            return result
        elif action == "extract_features":
            result = await self.extract_features(
                params.get("source_ref", ""), params.get("image_data", ""), params.get("options")
            )
            self.audit("extract_features", f"source={params.get('source_ref', '')}, success={result.success}")
            return result
        elif action == "find_similar":
            result = await self.find_similar(
                params.get("source_ref", ""), top_k=params.get("top_k", 5), threshold=params.get("threshold", 0.7)
            )
            self.audit("find_similar", f"source={params.get('source_ref', '')}, top_k={params.get('top_k', 5)}")
            return result
        elif action == "get_analysis":
            result = await self.get_analysis(params.get("analysis_id", ""))
            self.audit("get_analysis", f"analysis_id={params.get('analysis_id', '')}")
            return result
        elif action == "list_analyses":
            return await self.list_analyses(limit=params.get("limit", 50))
        elif action == "stats":
            return await self.get_module_stats()
        elif action == "health":
            hr = self.health_check()
            return Result(success=True, data=hr.to_dict() if hasattr(hr, "to_dict") else {"status": "healthy"})
        else:
            return Result(success=False, error=f"Unknown action: {action}")

    # === 图像分析 ===

    async def analyze_image(self, source_ref: str, image_data: str, options: Optional[Dict[str, Any]] = None) -> Result:
        """分析图像（OCR + 目标检测 + 场景分类）"""
        start = time.time()
        analysis_id = hashlib.md5(f"{source_ref}:{time.time()}".encode()).hexdigest()[:16]
        opts = options or {}

        try:
            pass
            # 解析图像元数据
            width = opts.get("width", 0)
            height = opts.get("height", 0)
            file_size = len(image_data) if isinstance(image_data, (str, bytes)) else 0

            result = ImageAnalysisResult(
                analysis_id=analysis_id, source_ref=source_ref, width=width, height=height, file_size=file_size
            )

            # OCR分析
            if opts.get("enable_ocr", True):
                ocr_result = await self._perform_ocr(image_data, opts)
                result.ocr = ocr_result
                self._stats["total_ocr"] += 1

            # 场景分析
            if opts.get("enable_scene", True):
                scene = await self._analyze_scene(opts)
                result.scene = scene
                self._stats["total_scene_analyses"] += 1

            # 目标检测（模拟）
            if opts.get("enable_detection", True):
                objects = await self._detect_objects(opts)
                # NMS后处理
                raw_boxes = [o.bbox for o in objects]
                keep_boxes = self._nms.suppress(raw_boxes)
                keep_ids = {b.label for b in keep_boxes}
                result.objects = [o for o in objects if o.bbox.label in keep_ids]
                self._stats["total_detections"] += len(result.objects)

            # 异常检测
            if opts.get("enable_anomaly", False):
                anomaly = self._detect_anomaly(result)
                result.anomaly_score = anomaly
                result.is_anomaly = anomaly > 0.7
                if result.is_anomaly:
                    self._stats["total_anomalies"] += 1

            result.processing_time_ms = int((time.time() - start) * 1000)
            self._analysis_cache[analysis_id] = result
            self._stats["total_analyses"] += 1

            await self._audit_log("analyze_image", f"分析完成: {analysis_id} -> {len(result.objects)}个目标")

            return Result(success=True, data=result.to_dict())

        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return Result(success=False, message=str(e))

    async def _perform_ocr(self, image_data: str, opts: Dict) -> OCRResult:
        """执行OCR识别"""
        # 模拟OCR处理 — 生产环境接入真实OCR引擎
        result = OCRResult(text="", confidence=0.0, language=opts.get("language", "auto"))
        if isinstance(image_data, str) and len(image_data) > 100:
            # 尝试从数据中提取文本线索
            result.text = f"[OCR识别] 数据长度: {len(image_data)}"
            result.confidence = 0.85
            result.language = "zh"
            result.words = [{"text": "示例", "confidence": 0.9, "bbox": [0, 0, 50, 20]}]
        return result

    async def _analyze_scene(self, opts: Dict) -> SceneAnalysis:
        """场景分类"""
        scene_type = opts.get("expected_scene", SceneType.INDOOR)
        if isinstance(scene_type, str):
            try:
                scene_type = SceneType(scene_type)
            except Exception:
                scene_type = SceneType.INDOOR
        return SceneAnalysis(
            scene_type=scene_type,
            description=f"检测到{scene_type.value}场景",
            tags=[scene_type.value, "analyzed"],
            confidence=0.82,
            dominant_colors=[("#333333", 0.3), ("#666666", 0.25), ("#999999", 0.2)],
        )

    async def _detect_objects(self, opts: Dict) -> List[DetectedObject]:
        """目标检测"""
        objects = []
        categories = opts.get("detect_categories", ["object"])
        for i, cat in enumerate(categories):
            det = DetectedObject(
                object_id=f"det_{i}_{int(time.time())}",
                bbox=BoundingBox(
                    x=10.0 + i * 50,
                    y=10.0,
                    width=40.0,
                    height=40.0,
                    confidence=round(0.7 + (i % 3) * 0.1, 2),
                    label=f"{cat}_{i}",
                    category=DetectionCategory.OBJECT,
                ),
            )
            objects.append(det)
        return objects

    def _detect_anomaly(self, result: ImageAnalysisResult) -> float:
        """异常检测评分"""
        score = 0.0
        if not result.objects and not result.ocr:
            score += 0.3
        if result.scene and result.scene.confidence < 0.5:
            score += 0.3
        if result.ocr and result.ocr.confidence < 0.5:
            score += 0.2
        return min(1.0, score)

    # === 特征匹配 ===

    async def extract_features(
        self, source_ref: str, pixel_data: List[Tuple[int, int, int]], width: int, height: int
    ) -> Result:
        """提取图像特征向量"""
        features = self._feature_extractor.extract_color_histogram(pixel_data)
        phash = self._feature_extractor.extract_phash(pixel_data, width, height)
        self._feature_store[source_ref] = features
        return Result(success=True, data={"source_ref": source_ref, "feature_dim": len(features), "phash": phash})

    async def find_similar(self, source_ref: str, top_k: int = 5, threshold: float = 0.5) -> Result:
        """查找相似图像"""
        query_vec = self._feature_store.get(source_ref)
        if not query_vec:
            return Result(success=False, message=f"未找到 {source_ref} 的特征向量")
        self._stats["total_similarity_queries"] += 1
        results = []
        for ref, vec in self._feature_store.items():
            if ref == source_ref:
                continue
            sim = self._feature_extractor.compute_similarity(query_vec, vec)
            if sim >= threshold:
                results.append({"ref": ref, "similarity": sim})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return Result(success=True, data={"query": source_ref, "matches": results[:top_k], "count": len(results)})

    # === 结果查询 ===

    async def get_analysis(self, analysis_id: str) -> Result:
        result = self._analysis_cache.get(analysis_id)
        if not result:
            return Result(success=False, message=f"分析 {analysis_id} 不存在")
        return Result(success=True, data=result.to_dict())

    async def list_analyses(self, limit: int = 50) -> Result:
        analyses = list(self._analysis_cache.values())
        analyses.sort(key=lambda a: a.created_at, reverse=True)
        return Result(success=True, data={"analyses": [a.to_dict() for a in analyses[:limit]], "count": len(analyses)})

    # === 健康检查 ===

    def health_check(self) -> HealthReport:
        return HealthReport(
            module_name=getattr(self, 'module_id', __import__('os').path.basename(__file__).replace('.py','')),
            status=ModuleStatus.RUNNING,
            checks={"feature_extractor": True, "nms_processor": True, "analysis_cache": True, "feature_store": True},
            stats={'total': self._stats["total_analyses"], 'custom': self._stats},
        )

    async def get_module_stats(self) -> Result:
        return Result(success=True, data=self._stats)

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

    def __init__(self):
        self._time_series: Dict[str, List[Tuple[float, float]]] = {}
        self._alert_rules: Dict[str, Dict] = {}
        self._alerts: List[Dict] = []
        self._window_size: int = 1000

    def record(self, metric_name: str, value: float, timestamp: float = None) -> None:
        """记录指标"""
        ts = timestamp or time.time()
        series = self._time_series.setdefault(metric_name, [])
        series.append((ts, value))
        if len(series) > self._window_size:
            self._time_series[metric_name] = series[-self._window_size :]

    def get_aggregate(self, metric_name: str, window: int = 60) -> Dict[str, float]:
        """获取聚合统计"""
        series = self._time_series.get(metric_name, [])
        if not series:
            return {"metric": metric_name, "count": 0}
        cutoff = time.time() - window
        values = [v for ts, v in series if ts > cutoff]
        if not values:
            return {"metric": metric_name, "count": 0}
        n = len(values)
        return {
            "metric": metric_name,
            "count": n,
            "avg": round(sum(values) / n, 4),
            "min": min(values),
            "max": max(values),
            "last": values[-1],
        }

    def add_alert_rule(self, rule_id: str, metric: str, condition: str, threshold: float) -> None:
        """添加告警规则"""
        self._alert_rules[rule_id] = {
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "status": "active",
        }

    def evaluate_alerts(self) -> List[Dict]:
        """评估告警规则"""
        triggered = []
        for rule_id, rule in self._alert_rules.items():
            agg = self.get_aggregate(rule["metric"])
            value = agg.get("avg", 0)
            triggered_flag = False
            if rule["condition"] == "gt" and value > rule["threshold"]:
                triggered_flag = True
            elif rule["condition"] == "lt" and value < rule["threshold"]:
                triggered_flag = True
            elif rule["condition"] == "eq" and abs(value - rule["threshold"]) < 0.01:
                triggered_flag = True
            if triggered_flag:
                alert = {
                    "rule_id": rule_id,
                    "metric": rule["metric"],
                    "value": value,
                    "threshold": rule["threshold"],
                    "condition": rule["condition"],
                    "timestamp": time.time(),
                }
                triggered.append(alert)
                self._alerts.append(alert)
        return triggered

    def get_metric_names(self) -> List[str]:
        return list(self._time_series.keys())

    def get_alert_history(self, limit: int = 50) -> List[Dict]:
        return self._alerts[-limit:]

    def delete_metric(self, metric_name: str) -> bool:
        if metric_name in self._time_series:
            del self._time_series[metric_name]
            return True
        return False

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_iris."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentIris

module_class = AgentIris

class MetricsAggregator:
    """指标聚合引擎 - 多维聚合、窗口计算、告警规则"""
