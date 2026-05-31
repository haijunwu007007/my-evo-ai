"""
AUTO-EVO-AI V0.1 - 模块注册器
=============================
全局模块管理中心，负责：
  - 模块注册/注销
  - 模块发现和查询
  - 模块生命周期管理（初始化/健康检查/关闭）
  - 模块能力索引（按分类/标签查找）
  - 模块依赖管理
  - 基础设施自动注入（追踪/指标/审计）

使用方式:
  registry = ModuleRegistry()

  # 注册模块
  registry.register(HealthCheck)

  # 按ID查找
  cls = registry.get_class("health-check")

  # 获取所有模块
  all_modules = registry.list_modules()

  # 初始化所有模块
  await registry.initialize_all()
"""

import importlib
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .enterprise_module import EnterpriseModule, HealthReport, ModuleStatus
from .tracing import get_tracer
from .metrics import get_metrics
from .audit import get_audit_logger

logger = logging.getLogger("evo.registry")


class ModuleInfo:
    """模块注册信息"""

    def __init__(
        self,
        module_class: type[EnterpriseModule],
        category: str = "general",
        tags: list[str] | None = None,
        dependencies: list[str] | None = None,
        priority: int = 0,
    ):
        self.module_class = module_class
        self.module_id = module_class.MODULE_ID
        self.module_name = module_class.MODULE_NAME
        self.version = module_class.VERSION
        self.level = module_class.MODULE_LEVEL
        self.category = category
        self.tags = tags or []
        self.dependencies = dependencies or []
        self.priority = priority
        self.instance: EnterpriseModule | None = None
        self.status = ModuleStatus.UNINITIALIZED

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "version": self.version,
            "level": self.level,
            "category": self.category,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "status": self.status.value,
            "initialized": self.instance is not None,
        }


class ModuleRegistry:
    """
    全局模块注册中心

    管理所有生产级模块的注册、发现和生命周期。
    """

    def __init__(self):
        self._modules: dict[str, ModuleInfo] = {}  # module_id -> ModuleInfo
        self._category_index: dict[str, list[str]] = {}  # category -> [module_ids]
        self._tag_index: dict[str, list[str]] = {}  # tag -> [module_ids]
        self._lock = asyncio.Lock() if asyncio.get_event_loop() else None

    def register(
        self,
        module_class: type[EnterpriseModule],
        category: str = "general",
        tags: list[str] | None = None,
        dependencies: list[str] | None = None,
        priority: int = 0,
    ):
        """
        注册模块类

        Args:
            module_class: 模块类（必须继承EnterpriseModule）
            category: 分类（system/tool/industry/extension）
            tags: 标签列表
            dependencies: 依赖的其他模块ID列表
            priority: 优先级（越大越先初始化）
        """
        if not issubclass(module_class, EnterpriseModule):
            raise TypeError(f"{module_class.__name__} 必须继承 EnterpriseModule")

        module_id = module_class.MODULE_ID
        if not module_id:
            raise ValueError(f"{module_class.__name__} 必须设置 MODULE_ID")

        info = ModuleInfo(
            module_class=module_class,
            category=category,
            tags=tags,
            dependencies=dependencies,
            priority=priority,
        )
        self._modules[module_id] = info

        # 更新分类索引
        if category not in self._category_index:
            self._category_index[category] = []
        if module_id not in self._category_index[category]:
            self._category_index[category].append(module_id)

        # 更新标签索引
        for tag in tags or []:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if module_id not in self._tag_index[tag]:
                self._tag_index[tag].append(module_id)

        logger.debug(f"[注册] {module_id} ({module_class.__name__}) → {category}")

    def unregister(self, module_id: str):
        """注销模块"""
        if module_id in self._modules:
            info = self._modules.pop(module_id)
            # 清理索引
            for cat, ids in self._category_index.items():
                if module_id in ids:
                    ids.remove(module_id)
            for tag, ids in self._tag_index.items():
                if module_id in ids:
                    ids.remove(module_id)
            logger.info(f"[注销] {module_id}")

    def get_class(self, module_id: str) -> type[EnterpriseModule] | None:
        """获取模块类"""
        info = self._modules.get(module_id)
        return info.module_class if info else None

    def get_info(self, module_id: str) -> ModuleInfo | None:
        """获取模块注册信息"""
        return self._modules.get(module_id)

    def get_instance(self, module_id: str) -> EnterpriseModule | None:
        """获取已初始化的模块实例"""
        info = self._modules.get(module_id)
        return info.instance if info else None

    def list_modules(self, category: str = "") -> list[dict[str, Any]]:
        """列出所有模块信息"""
        if category:
            ids = self._category_index.get(category, [])
            return [self._modules[mid].to_dict() for mid in ids if mid in self._modules]
        return [info.to_dict() for info in self._modules.values()]

    def list_by_category(self) -> dict[str, list[dict[str, Any]]]:
        """按分类列出模块"""
        result = {}
        for cat, ids in self._category_index.items():
            result[cat] = [self._modules[mid].to_dict() for mid in ids if mid in self._modules]
        return result

    def find_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """按标签查找模块"""
        ids = self._tag_index.get(tag, [])
        return [self._modules[mid].to_dict() for mid in ids if mid in self._modules]

    def total_count(self) -> int:
        """已注册模块总数"""
        return len(self._modules)

    def count_by_level(self) -> dict[str, int]:
        """按级别统计"""
        counts: dict[str, int] = {}
        for info in self._modules.values():
            counts[info.level] = counts.get(info.level, 0) + 1
        return counts

    async def create_instance(self, module_id: str, config: dict | None = None) -> EnterpriseModule | None:
        """创建模块实例（不初始化）"""
        info = self._modules.get(module_id)
        if not info:
            logger.error(f"模块不存在: {module_id}")
            return None

        instance = info.module_class(config=config)

        # 注入基础设施
        instance.init_infra(
            tracer=get_tracer(),
            metrics=get_metrics(),
            audit=get_audit_logger(),
        )

        info.instance = instance
        return instance

    async def initialize_all(self, config: dict[str, Any] | None = None):
        """
        初始化所有已注册模块
        按优先级从高到低，自动处理依赖顺序
        """
        config = config or {}
        sorted_modules = sorted(self._modules.values(), key=lambda m: m.priority, reverse=True)

        initialized = []
        failed = []

        for info in sorted_modules:
            try:
                instance = await self.create_instance(info.module_id, config)
                if instance:
                    await instance.initialize()
                    info.status = ModuleStatus.RUNNING
                    initialized.append(info.module_id)
                    logger.info(f"[初始化✅] {info.module_id}")
            except Exception as e:
                info.status = ModuleStatus.ERROR
                failed.append((info.module_id, str(e)))
                logger.error(f"[初始化❌] {info.module_id}: {e}")

        logger.info(f"批量初始化完成: {len(initialized)}✅ {len(failed)}❌")
        return {"initialized": initialized, "failed": failed}

    async def health_check_all(self) -> dict[str, Any]:
        """检查所有模块健康状态"""
        results = {}
        healthy_count = 0
        unhealthy_count = 0

        for module_id, info in self._modules.items():
            if info.instance:
                try:
                    report = info.instance.health_check()
                    results[module_id] = report.to_dict()
                    if report.healthy:
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                except Exception as e:
                    results[module_id] = {"healthy": False, "error": str(e)}
                    unhealthy_count += 1
            else:
                results[module_id] = {"healthy": False, "status": "not_initialized"}

        return {
            "total": len(self._modules),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "modules": results,
        }

    async def shutdown_all(self):
        """关闭所有模块"""
        shutdown_ok = []
        failed = []

        for info in self._modules.values():
            if info.instance:
                try:
                    await info.instance.shutdown()
                    info.status = ModuleStatus.STOPPED
                    shutdown_ok.append(info.module_id)
                except Exception as e:
                    failed.append((info.module_id, str(e)))
                    logger.error(f"[关闭❌] {info.module_id}: {e}")

        logger.info(f"批量关闭完成: {len(shutdown_ok)}✅ {len(failed)}❌")
        return {"shutdown": shutdown_ok, "failed": failed}

    def get_stats(self) -> dict[str, Any]:
        """获取注册中心统计"""
        return {
            "total_modules": len(self._modules),
            "by_level": self.count_by_level(),
            "by_category": {cat: len(ids) for cat, ids in self._category_index.items()},
            "initialized": sum(1 for i in self._modules.values() if i.instance is not None),
        }


# 全局单例
_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    """获取全局模块注册器"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
        logger.info("模块注册中心初始化完成")
    return _registry
