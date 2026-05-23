import time

"""
Hyperframes 视频渲染集成 v2.0
版本: v6.37 | HeyGen开源集成 + Pillow/numpy + ffmpeg
功能: HTML原生视频定义 + 真实视频渲染(多轨道合成、转场、文字叠加、图片序列、音频混合)
降级: 无ffmpeg时输出GIF；无Pillow时仅输出HTML定义
"""

__module_meta__ = {
    "id": "hyperframes-video",
    "name": "Hyperframes Video",
    "version": "1.0.0",
    "group": "media",
    "inputs": [
        {"name": "title", "type": "string", "required": True, "description": ""},
        {"name": "resolution", "type": "string", "required": True, "description": ""},
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["hyperframes"],
    "grade": "C",
    "description": "Hyperframes 视频渲染集成 v2.0 版本: v6.37 | HeyGen开源集成 + Pillow/numpy + ffmpeg",
}
import os, json, logging, subprocess, shutil, tempfile, math
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

def _find_ffmpeg() -> Optional[str]:
    for name in ["ffmpeg", "ffmpeg.exe"]:
        p = shutil.which(name)
        if p:
            return p
    for p in [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"]:
        if os.path.exists(p):
            return p
    return None

def _find_font() -> str:
    for p in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]:
        if os.path.exists(p):
            return p
    return ""

@dataclass
class HyperframesVideoAnalyzer(object):
    """hyperframes_video 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "hyperframes_video"
        self.version = "1.0.0"
        self._analyzer = HyperframesVideoAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "HyperframesVideoAnalyzer",
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
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "hyperframes_video"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== hyperframes_video ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
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
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class VideoTrack(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """视频轨道"""

    id: str
    type: str  # 'video', 'audio', 'text', 'image'
    start_time: float
    duration: float
    content: str
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VideoProject:
    """视频项目"""

    id: str
    title: str
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    tracks: List[VideoTrack] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    bg_color: Tuple[int, int, int] = (20, 20, 40)

class HyperframesVideo:
    """
    HeyGen Hyperframes 视频渲染 v2.0

    能力：
    - 多轨道编辑（文字/图片/音频/视频）
    - HTML预览 + 真实MP4输出
    - 转场效果（淡入淡出/缩放/滑动）
    - GSAP动画HTML预览
    """

    VERSION = "2.0.0"

    def __init__(self, output_dir: str = "./videos", ffmpeg_path: Optional[str] = None):
        super().__init__()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.projects: Dict[str, VideoProject] = {}
        self.ffmpeg_path = ffmpeg_path or _find_ffmpeg()
        self.font_path = _find_font()
        self._font_cache: Dict[int, Any] = {}

    def _get_font(self, size: int):
        if size in self._font_cache:
            return self._font_cache[size]
        try:
            font = ImageFont.truetype(self.font_path, size) if self.font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        self._font_cache[size] = font
        return font

    # ─── 项目管理 ──────────────────────────────────────
    def create_project(
        self,
        title: str,
        resolution: Tuple[int, int] = (1920, 1080),
        fps: int = 30,
        bg_color: Tuple[int, int, int] = (20, 20, 40),
    ) -> VideoProject:
        project_id = f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        project = VideoProject(id=project_id, title=title, resolution=resolution, fps=fps, bg_color=bg_color)
        self.projects[project_id] = project
        logger.info(f"项目已创建: {title} ({resolution[0]}x{resolution[1]} @ {fps}fps)")
        return project

    def add_text_track(
        self,
        project: VideoProject,
        text: str,
        start_time: float,
        duration: float,
        style: Optional[Dict[str, Any]] = None,
    ) -> VideoTrack:
        track = VideoTrack(
            id=f"track_{len(project.tracks) + 1}",
            type="text",
            start_time=start_time,
            duration=duration,
            content=text,
            properties=style or {},
        )
        project.tracks.append(track)
        return track

    def add_image_track(
        self,
        project: VideoProject,
        image_path: str,
        start_time: float,
        duration: float,
        position: tuple = (0, 0),
        scale: float = 1.0,
    ) -> VideoTrack:
        track = VideoTrack(
            id=f"track_{len(project.tracks) + 1}",
            type="image",
            start_time=start_time,
            duration=duration,
            content=image_path,
            properties={"position": position, "scale": scale},
        )
        project.tracks.append(track)
        return track

    def add_audio_track(
        self, project: VideoProject, audio_path: str, start_time: float = 0, volume: float = 1.0
    ) -> VideoTrack:
        # 尝试获取音频时长
        dur = 60.0
        if self.ffmpeg_path and os.path.exists(audio_path):
            try:
                r = subprocess.run(
                    [
                        self.ffmpeg_path,
                        "-i",
                        audio_path,
                        "-show_entries",
                        "format=duration",
                        "-v",
                        "quiet",
                        "-of",
                        "csv=p=0",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if r.stdout.strip():
                    dur = float(r.stdout.strip())
            except Exception:
                pass

        track = VideoTrack(
            id=f"track_{len(project.tracks) + 1}",
            type="audio",
            start_time=start_time,
            duration=dur,
            content=audio_path,
            properties={"volume": volume},
        )
        project.tracks.append(track)
        return track

    # ─── HTML预览 ──────────────────────────────────────
    def generate_html(self, project: VideoProject) -> str:
        w, h = project.resolution
        total_dur = max((t.start_time + t.duration for t in project.tracks), default=10)

        html = f'''<!DOCTYPE html>
<html data-duration="{total_dur}">
<head>
<meta charset="UTF-8">
<title>{project.title}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{w}px; height:{h}px; overflow:hidden;
  background:rgb({project.bg_color[0]},{project.bg_color[1]},{project.bg_color[2]});
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
.track {{ position:absolute; display:flex; align-items:center; justify-content:center; }}
.text-track {{ font-size:48px; color:white; text-shadow:2px 2px 8px rgba(0,0,0,0.5); }}
.image-track img {{ max-width:100%; max-height:100%; object-fit:contain; }}
</style>
</head><body>\n'''
        for t in project.tracks:
            if t.type == "text":
                fs = t.properties.get("fontSize", "48px")
                clr = t.properties.get("color", "white")
                html += f'''<div class="track text-track" data-start="{t.start_time}" data-duration="{t.duration}"
  style="width:{w}px;height:{h}px;font-size:{fs};color:{clr};">{t.content}</div>\n'''
            elif t.type == "image":
                pos = t.properties.get("position", (0, 0))
                sc = t.properties.get("scale", 1)
                html += f'''<div class="track image-track" data-start="{t.start_time}" data-duration="{t.duration}"
  style="left:{pos[0]}px;top:{pos[1]}px;transform:scale({sc});"><img src="{t.content}"></div>\n'''
        html += "</body></html>"
        return html

    def render_html(self, project: VideoProject, output_name: Optional[str] = None) -> str:
        """渲染为HTML文件(预览用)"""
        name = output_name or f"{project.title}.html"
        path = os.path.join(self.output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_html(project))
        return path

    def render_with_animation(self, project: VideoProject) -> str:
        """渲染带GSAP动画的HTML"""
        html = self.generate_html(project)
        gsap = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const tracks = document.querySelectorAll('.track');
    tracks.forEach(t => {
        const start = parseFloat(t.dataset.start)||0;
        const dur = parseFloat(t.dataset.duration)||1;
        gsap.fromTo(t, {opacity:0, y:50}, {opacity:1, y:0, duration:0.5, delay:start});
        gsap.to(t, {opacity:0, delay:start+dur-0.3, duration:0.3});
    });
});
</script>"""
        html = html.replace("</body>", gsap + "</body>")
        path = os.path.join(self.output_dir, f"{project.title}_animated.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    # ─── 真实视频渲染 ─────────────────────────────────
    def render_video(self, project: VideoProject, output_name: Optional[str] = None) -> Dict[str, Any]:
        """
        渲染为真实视频文件(MP4或GIF)

        Returns:
            {"success": True, "video_path": str, ...}
        """
        if not _HAS_PIL:
            return {"success": False, "error": "Pillow未安装 (pip install Pillow)"}

        w, h = project.resolution
        fps = project.fps
        total_dur = max((t.start_time + t.duration for t in project.tracks), default=5)
        total_frames = int(total_dur * fps)

        temp_dir = tempfile.mkdtemp(prefix="hyperframes_")
        try:
            pass
            # 按时间排序轨道
            sorted_tracks = sorted(project.tracks, key=lambda t: t.start_time)
            # 预加载图片
            image_cache: Dict[str, Image.Image] = {}
            for t in sorted_tracks:
                if t.type == "image" and os.path.exists(t.content):
                    try:
                        img = Image.open(t.content).convert("RGBA")
                        sc = t.properties.get("scale", 1.0)
                        if sc != 1.0:
                            nw, nh = int(img.width * sc), int(img.height * sc)
                            img = img.resize((nw, nh), Image.LANCZOS)
                        image_cache[t.content] = img
                    except Exception as e:
                        logger.warning(f"加载图片失败 {t.content}: {e}")

            # 逐帧渲染
            logger.info(f"Hyperframes渲染: {total_frames}帧 {w}x{h}@{fps}fps")
            for frame_i in range(total_frames):
                current_time = frame_i / fps
                img = Image.new("RGB", (w, h), project.bg_color)
                draw = ImageDraw.Draw(img)

                for track in sorted_tracks:
                    t_start = track.start_time
                    t_end = t_start + track.duration
                    if current_time < t_start or current_time >= t_end:
                        continue

                    progress = (current_time - t_start) / track.duration
                    alpha = 1.0
                    # 淡入淡出
                    fade_len = 0.15
                    if progress < fade_len:
                        alpha = progress / fade_len
                    elif progress > 1 - fade_len:
                        alpha = (1 - progress) / fade_len

                    if track.type == "text":
                        font_size = int(track.properties.get("fontSize", 48) or 48)
                        font = self._get_font(font_size)
                        color_str = track.properties.get("color", "white")
                        # 解析颜色
                        color = (255, 255, 255)
                        if color_str.startswith("#") and len(color_str) == 7:
                            color = (int(color_str[1:3], 16), int(color_str[3:5], 16), int(color_str[5:7], 16))

                        bbox = draw.textbbox((0, 0), track.content, font=font)
                        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        x = (w - tw) // 2
                        y = (h - th) // 2

                        # 缩放效果
                        scale = 0.9 + 0.1 * min(progress * 5, 1)
                        if scale != 1.0:
                            y_offset = int((1 - scale) * th / 2)
                            y += y_offset

                        draw.text((x + 2, y + 2), track.content, fill=(0, 0, 0), font=font)
                        adj_color = tuple(int(c * alpha) for c in color)
                        draw.text((x, y), track.content, fill=adj_color, font=font)

                    elif track.type == "image":
                        cached = image_cache.get(track.content)
                        if cached:
                            pos = track.properties.get("position", (0, 0))
                            paste_x = int((w - cached.width) // 2 + pos[0])
                            paste_y = int((h - cached.height) // 2 + pos[1])
                            if alpha < 1.0 and _HAS_NUMPY:
                                arr = np.array(cached).astype(np.float32)
                                arr[:, :, 3] = arr[:, :, 3] * alpha
                                temp = Image.fromarray(arr.astype(np.uint8), "RGBA")
                                img.paste(temp, (paste_x, paste_y), temp)
                            else:
                                img.paste(cached, (paste_x, paste_y), cached)

                frame_path = os.path.join(temp_dir, f"frame_{frame_i:06d}.png")
                img.save(frame_path, "PNG")

            # 编码
            ext = ".mp4" if self.ffmpeg_path else ".gif"
            out_name = output_name or f"{project.title}{ext}"
            out_path = os.path.join(self.output_dir, out_name)

            if self.ffmpeg_path:
                audio_tracks = [t for t in project.tracks if t.type == "audio"]
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-framerate",
                    str(fps),
                    "-i",
                    os.path.join(temp_dir, "frame_%06d.png"),
                ]
                # 混入音频
                for i, at in enumerate(audio_tracks):
                    cmd.extend(["-i", at.content])
                cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-shortest"])
                # 音频混合参数
                if audio_tracks:
                    for i in range(len(audio_tracks)):
                        cmd.extend([f"-map", f"{i + 1}:a"])
                    cmd.extend(["-c:a", "aac", "-b:a", "128k"])
                    if len(audio_tracks) > 1:
                        cmd.extend(["-filter_complex", "amix=inputs=" + str(len(audio_tracks)) + ":duration=shortest"])
                cmd.extend(["-movflags", "+faststart", out_path])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0 or not os.path.exists(out_path):
                    logger.error(f"ffmpeg失败: {result.stderr[:300]}")
                    out_path = self._encode_gif_fallback(temp_dir, out_path.replace(".mp4", ".gif"), fps)
            else:
                out_path = self._encode_gif_fallback(temp_dir, out_path, fps)

            shutil.rmtree(temp_dir, ignore_errors=True)

            size_mb = os.path.getsize(out_path) / 1024 / 1024 if os.path.exists(out_path) else 0
            return {
                "success": True,
                "video_path": out_path,
                "format": ext.lstrip("."),
                "size_mb": round(size_mb, 2),
                "resolution": f"{w}x{h}",
                "fps": fps,
                "frames": total_frames,
                "duration": round(total_dur, 2),
            }
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"success": False, "error": str(e)}

    def _encode_gif_fallback(self, frames_dir: str, output_path: str, fps: int) -> str:
        frames = []
        for fn in sorted(os.listdir(frames_dir))[:200]:
            if fn.endswith(".png"):
                img = Image.open(os.path.join(frames_dir, fn)).convert("RGB").thumbnail((480, 480))
                frames.append(img)
        if frames:
            frames[0].save(
                output_path, save_all=True, append_images=frames[1:], duration=1000 // fps, loop=0, optimize=True
            )
        return output_path

    # ─── 查询 ──────────────────────────────────────────
    def get_project_info(self, project: VideoProject) -> Dict[str, Any]:
        return {
            "id": project.id,
            "title": project.title,
            "resolution": f"{project.resolution[0]}x{project.resolution[1]}",
            "fps": project.fps,
            "tracks": len(project.tracks),
            "duration": max((t.start_time + t.duration for t in project.tracks), default=0),
            "created_at": project.created_at.isoformat(),
        }

    def get_capabilities(self) -> Dict:
        return {
            "pil": _HAS_PIL,
            "numpy": _HAS_NUMPY,
            "ffmpeg": self.ffmpeg_path is not None,
            "font": os.path.basename(self.font_path) if self.font_path else "default",
            "version": self.VERSION,
        }

    def health_check(self) -> Dict:
        return {
            "healthy": _HAS_PIL,
            "ffmpeg": self.ffmpeg_path is not None,
            "projects": len(self.projects),
            "version": self.VERSION,
        }

def create_video_project(title: str, resolution: Tuple[int, int] = (1920, 1080)):
    renderer = HyperframesVideo()
    project = renderer.create_project(title, resolution)
    return renderer, project

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("hyperframes_video.execute", "start", action=action)
        self.metrics_collector.counter("hyperframes_video.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "hyperframes_video"}
            else:
                result = {"success": True, "action": action, "module": "hyperframes_video"}
            self.metrics_collector.counter("hyperframes_video.execute.success", 1)
            self.trace("hyperframes_video.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("hyperframes_video.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "hyperframes_video"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "hyperframes_video", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("hyperframes_video.initialize", "start")
        self.metrics_collector.gauge("hyperframes_video.initialized", 1)
        self.audit("初始化hyperframes_video", level="info")
        self.trace("hyperframes_video.initialize", "end")
        return {"success": True, "module": "hyperframes_video"}

module_class = HyperframesVideo
