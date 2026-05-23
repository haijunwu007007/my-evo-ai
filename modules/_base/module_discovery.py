"""
AUTO-EVO-AI v7.0 — 模块自动发现引擎
=======================================
上市公司生产级实现 — 扫描模块目录、提取元数据、构建能力地图

核心功能:
  - 扫描 modules/ 目录下所有 Python 文件
  - 提取 __module_meta__ 并注册到 ModuleRegistry
  - 构建能力地图（谁依赖谁、谁触发谁）
  - 定时扫描 Hot-Reload（开发模式）

用法:
    from modules._base.module_discovery import ModuleDiscoveryEngine

    engine = ModuleDiscoveryEngine(module_dir="modules")
    await engine.scan_all()           # 全量扫描
    await engine.scan_incremental()   # 增量扫描（仅新文件）
    engine.start_watcher()            # 启动文件监听（开发模式）
"""

from __future__ import annotations

import os
import sys
import time
import json
import logging
import importlib
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from modules._base.module_meta import (
    ModuleMeta,
    ModuleRegistry,
    extract_meta_from_file,
)

logger = logging.getLogger("evo.module_discovery")


# ============================================================
# 发现结果
# ============================================================


@dataclass
class DiscoveryResult:
    """单次扫描结果"""

    total_files: int = 0
    discovered: int = 0  # 新发现的模块数
    updated: int = 0  # 更新的模块数
    failed: int = 0  # 解析失败的模块数
    removed: int = 0  # 已删除的模块数
    errors: List[str] = None  # 错误列表
    duration_ms: float = 0.0  # 耗时

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def merge(self, other: DiscoveryResult):
        self.total_files += other.total_files
        self.discovered += other.discovered
        self.updated += other.updated
        self.failed += other.failed
        self.removed += other.removed
        self.errors.extend(other.errors)
        self.duration_ms = max(self.duration_ms, other.duration_ms)

    def success_count(self) -> int:
        return self.discovered + self.updated

    def is_clean(self) -> bool:
        return self.failed == 0 and not self.errors

    def summary(self) -> str:
        parts = []
        if self.discovered:
            parts.append(f"+{self.discovered}发现")
        if self.updated:
            parts.append(f"~{self.updated}更新")
        if self.failed:
            parts.append(f"✗{self.failed}失败")
        if self.removed:
            parts.append(f"-{self.removed}移除")
        if self.errors:
            for e in self.errors[:3]:
                parts.append(f"⚠{e[:40]}")
        return f"{self.total_files}文件 {' '.join(parts)} [{self.duration_ms:.0f}ms]"


# ============================================================
# 模块发现引擎
# ============================================================


class ModuleDiscoveryEngine:
    """模块自动发现引擎

    支持全量扫描、增量扫描、文件变更监听。
    发现结果自动注册到 ModuleRegistry 单例。

    排除规则:
      - 以 _ 开头的文件（内部模块）
      - _base/ 目录下的基础设施模块
      - 文件名匹配 _*.py 的调试脚本
    """

    # 排除模式
    EXCLUDE_PREFIXES: Set[str] = {"_", "."}
    EXCLUDE_DIRS: Set[str] = {
        "_base",
        "_utils",
        "__pycache__",
        ".git",
        ".workbuddy",
        "_archive",
        ".data",
        ".audit_logs",
        ".backups",
        ".cache",
        "node_modules",
    }
    EXCLUDE_MODULES: Set[str] = {
        "__init__",
        "module_base",
        "enterprise_module",
        "module_meta",
        "module_discovery",
    }

    def __init__(
        self,
        module_dir: str = "modules",
        registry: Optional[ModuleRegistry] = None,
        max_workers: int = 8,
    ):
        self._base_path = Path(module_dir).resolve()
        self._registry = registry or ModuleRegistry()
        self._max_workers = max_workers

        # 缓存
        self._file_hashes: Dict[str, str] = {}  # filepath → md5
        self._scanned_file_count: int = 0
        self._last_scan_time: Optional[datetime] = None

        # 回调
        self._on_discover: List[Callable[[ModuleMeta], None]] = []
        self._on_error: List[Callable[[str, str], None]] = []

        # 监控
        self._watcher_running = False
        self._watcher_task = None

    # ── 公开API ──

    async def scan_all(self) -> DiscoveryResult:
        """全量扫描 modules/ 目录，更新所有模块元数据"""
        start = time.time()
        result = DiscoveryResult()

        py_files = self._find_py_files()
        result.total_files = len(py_files)

        if not py_files:
            return result

        # 并行扫描
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for fp in py_files:
                future = executor.submit(self._scan_single_file, fp)
                futures[future] = fp

            for future in futures:
                fp = futures[future]
                try:
                    meta, error = future.result()
                except Exception as e:
                    meta, error = None, str(e)

                if error:
                    result.failed += 1
                    result.errors.append(f"{fp.name}: {error[:100]}")
                    self._trigger_error(fp.name, error)
                elif meta:
                    # 检查是新增还是更新
                    existing = self._registry.get(meta.id)
                    file_key = str(fp)
                    old_hash = self._file_hashes.get(file_key)
                    new_hash = self._hash_file(fp)

                    if existing is None:
                        result.discovered += 1
                    elif old_hash != new_hash:
                        result.updated += 1
                    else:
                        continue  # 无变化

                    self._registry.register(meta.id, meta, str(fp))
                    self._file_hashes[file_key] = new_hash
                    self._trigger_discover(meta)

        self._last_scan_time = datetime.now()
        result.duration_ms = (time.time() - start) * 1000

        logger.info(f"扫描完成: {result.summary()}")
        return result

    async def scan_incremental(self) -> DiscoveryResult:
        """增量扫描——只处理新增或修改的文件"""
        start = time.time()
        result = DiscoveryResult()

        py_files = self._find_py_files()
        result.total_files = len(py_files)

        changed_files = [fp for fp in py_files if self._is_changed(str(fp))]

        if not changed_files:
            result.duration_ms = (time.time() - start) * 1000
            return result

        for fp in changed_files:
            meta, error = self._scan_single_file(fp)
            if error:
                result.failed += 1
                result.errors.append(f"{fp.name}: {error[:100]}")
                self._trigger_error(fp.name, error)
            elif meta:
                existing = self._registry.get(meta.id)
                if existing is None:
                    result.discovered += 1
                else:
                    result.updated += 1
                self._registry.register(meta.id, meta, str(fp))
                self._file_hashes[str(fp)] = self._hash_file(fp)
                self._trigger_discover(meta)

        result.duration_ms = (time.time() - start) * 1000
        return result

    async def discover_removed_files(self) -> List[str]:
        """检测已删除的文件并注销对应模块，返回已移除的模块ID列表"""
        registered_files = {
            mid: self._registry.source_of(mid)
            for mid in [m.id for m in self._registry.get_all()]
            if self._registry.source_of(mid)
        }
        removed_ids = []
        for mid, fpath in registered_files.items():
            if fpath and not os.path.exists(fpath):
                self._registry.unregister(mid)
                self._file_hashes.pop(fpath, None)
                removed_ids.append(mid)

        if removed_ids:
            logger.info(f"检测到 {len(removed_ids)} 个模块文件已删除")
        return removed_ids

    async def rebuild_capability_map(self) -> dict:
        """重建能力地图（全量扫描+依赖分析）"""
        await self.scan_all()
        return self._registry.export_capability_map()

    # ── 文件监听（开发模式） ──

    async def start_watcher(self, interval_seconds: float = 5.0):
        """启动文件变更监听（开发模式用）"""
        if self._watcher_running:
            logger.warning("监听器已在运行")
            return
        self._watcher_running = True
        logger.info(f"文件监听已启动 (interval={interval_seconds}s)")

        import asyncio

        while self._watcher_running:
            try:
                result = await self.scan_incremental()
                removed = await self.discover_removed_files()
                if result.success_count() > 0 or removed:
                    logger.info(f"热更新: {result.summary()}, 移除: {len(removed)}")
            except Exception as e:
                logger.error(f"监听扫描异常: {e}")
            await asyncio.sleep(interval_seconds)

    def stop_watcher(self):
        self._watcher_running = False
        logger.info("文件监听已停止")

    # ── 回调 ──

    def on_discover(self, callback: Callable[[ModuleMeta], None]):
        self._on_discover.append(callback)

    def on_error(self, callback: Callable[[str, str], None]):
        self._on_error.append(callback)

    # ── 统计 ──

    def get_stats(self) -> dict:
        return {
            "base_path": str(self._base_path),
            "scanned_files": self._scanned_file_count,
            "cached_hashes": len(self._file_hashes),
            "last_scan": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "watcher_running": self._watcher_running,
            "registry": self._registry.get_stats(),
        }

    # ── 内部方法 ──

    def _find_py_files(self) -> List[Path]:
        """递归查找 modules/ 下所有 .py 文件"""
        files: List[Path] = []
        base = self._base_path
        if not base.exists():
            logger.warning(f"模块目录不存在: {base}")
            return files

        for entry in base.rglob("*.py"):
            # 跳过排除目录
            if any(excl in entry.parts for excl in self.EXCLUDE_DIRS):
                continue
            # 跳过排除前缀
            if entry.stem.startswith("_"):
                continue
            # 跳过排除模块名
            if entry.stem in self.EXCLUDE_MODULES:
                continue
            # 跳过 __init__.py
            if entry.name == "__init__.py":
                continue
            files.append(entry)

        self._scanned_file_count = len(files)
        return files

    def _scan_single_file(self, filepath: Path) -> Tuple[Optional[ModuleMeta], Optional[str]]:
        """扫描单个文件，返回 (元数据, 错误信息)"""
        try:
            meta = extract_meta_from_file(str(filepath))
            if meta is None:
                return None, None  # 没有 __module_meta__ 不算错误
            return meta, None
        except Exception as e:
            return None, str(e)

    def _is_changed(self, filepath: str) -> bool:
        """检查文件是否有变化"""
        old_hash = self._file_hashes.get(filepath)
        if old_hash is None:
            return True  # 新文件
        return self._hash_file(Path(filepath)) != old_hash

    @staticmethod
    def _hash_file(filepath: Path) -> str:
        """计算文件 MD5 哈希"""
        import hashlib

        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _trigger_discover(self, meta: ModuleMeta):
        for cb in self._on_discover:
            try:
                cb(meta)
            except Exception as e:
                logger.warning(f"on_discover 回调异常: {e}")

    def _trigger_error(self, name: str, error: str):
        for cb in self._on_error:
            try:
                cb(name, error)
            except Exception as e:
                logger.warning(f"on_error 回调异常: {e}")


# ============================================================
# 便捷函数
# ============================================================


async def auto_discover(module_dir: str = "modules") -> ModuleRegistry:
    """一键发现并返回 ModuleRegistry 实例"""
    engine = ModuleDiscoveryEngine(module_dir=module_dir)
    result = await engine.scan_all()
    logger.info(f"自动发现完成: {result.summary()}")
    return engine._registry


def get_registry() -> ModuleRegistry:
    """获取全局 ModuleRegistry 单例"""
    return ModuleRegistry()


__all__ = [
    "ModuleDiscoveryEngine",
    "DiscoveryResult",
    "auto_discover",
    "get_registry",
]
