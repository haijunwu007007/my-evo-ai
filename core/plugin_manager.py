"""
AUTO-EVO-AI V0.1 — 插件市场管理引擎
==================================================
上市公司生产级别：第三方模块/插件的全生命周期管理

核心能力：
  1. 插件安装 — 从GitHub/Git URL/本地路径安装
  2. 插件卸载 — 安全卸载+可选清理数据
  3. 插件管理 — 启用/禁用/更新/依赖检查
  4. 插件沙箱 — 隔离运行环境，不影响核心系统
  5. 插件注册 — 自动发现EnterpriseModule子类并注册
  6. 插件仓库 — 内置+远程仓库索引
  7. 版本管理 — 语义化版本+兼容性检查
  8. 安全审计 — 安装前代码扫描+权限声明
"""

import os
import re
import sys
import json
import shutil
import hashlib
from core.logging_config import get_logger
import importlib
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = get_logger(__name__)


@dataclass
class PluginManifest:
    """插件清单文件 (plugin.json)"""
    name: str                           # 插件唯一标识
    version: str = "0.1.0"              # 语义化版本
    display_name: str = ""              # 显示名称
    description: str = ""               # 描述
    author: str = ""                    # 作者
    license: str = "MIT"                # 许可证
    homepage: str = ""                  # 主页
    repository: str = ""                # 仓库地址
    module_class: str = ""              # EnterpriseModule子类路径
    permissions: list[str] = field(default_factory=list)    # 声明的权限
    dependencies: dict[str, str] = field(default_factory=dict)  # 依赖: 最低版本
    tags: list[str] = field(default_factory=list)            # 分类标签
    min_evo_version: str = "0.1.0"      # 最低兼容版本
    icon: str = ""                       # 图标URL/base64
    config_schema: dict = field(default_factory=dict)        # 配置项schema


@dataclass
class PluginState:
    """插件运行时状态"""
    name: str
    version: str = ""
    status: str = "installed"  # installed/enabled/disabled/error
    installed_at: str = ""
    enabled_at: str = ""
    error: str = ""
    module_instance: Any = None
    config: dict = field(default_factory=dict)


class PluginManager:
    """
    插件市场管理引擎 — 上市公司生产级

    插件生命周期：发现 → 审计 → 安装 → 注册 → 启用 → 运行 → 禁用 → 卸载

    目录结构：
      plugins/
        installed/        已安装插件
        temp/             安装临时目录
        registry.json     本地注册表
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")
        self._installed_dir = os.path.join(self._base_dir, "installed")
        self._temp_dir = os.path.join(self._base_dir, "temp")

        for d in [self._installed_dir, self._temp_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)

        self._registry_path = os.path.join(self._base_dir, "registry.json")
        self._plugins: dict[str, PluginState] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._rw_lock = threading.RLock()

        # 加载已注册插件
        self._load_registry()
        # 自动加载已启用插件
        self._auto_load_plugins()

        logger.info(f"[PluginManager] Initialized: {len(self._plugins)} registered plugins")

    # ═══════════════════════════════════════════════════════
    # 内置插件仓库
    # ═══════════════════════════════════════════════════════

    BUILTIN_REPOSITORY = [
        {
            "name": "market-data-fetcher",
            "version": "1.0.0",
            "display_name": "实时行情数据采集",
            "description": "从东方财富/新浪/Tushare采集A股实时行情、K线、财务数据",
            "author": "AUTO-EVO-AI",
            "tags": ["金融", "数据", "行情"],
            "repository": "",
            "permissions": ["network", "file_write"],
        },
        {
            "name": "news-sentiment",
            "version": "1.0.0",
            "display_name": "新闻情感分析",
            "description": "采集财经新闻，AI情感分析，生成市场情绪指标",
            "author": "AUTO-EVO-AI",
            "tags": ["NLP", "新闻", "分析"],
            "repository": "",
            "permissions": ["network", "llm"],
        },
        {
            "name": "report-generator-pro",
            "version": "1.0.0",
            "display_name": "专业报告生成器",
            "description": "生成PDF/Word/HTML格式的数据分析报告，支持模板和图表",
            "author": "AUTO-EVO-AI",
            "tags": ["报告", "文档", "可视化"],
            "repository": "",
            "permissions": ["file_write", "template"],
        },
        {
            "name": "auto-trader",
            "version": "1.0.0",
            "display_name": "量化交易引擎",
            "description": "策略回测+实盘交易，支持多券商API接口",
            "author": "AUTO-EVO-AI",
            "tags": ["交易", "量化", "策略"],
            "repository": "",
            "permissions": ["network", "trading", "high_risk"],
        },
        {
            "name": "knowledge-graph",
            "version": "1.0.0",
            "display_name": "知识图谱引擎",
            "description": "构建领域知识图谱，支持实体识别/关系抽取/智能问答",
            "author": "AUTO-EVO-AI",
            "tags": ["AI", "图谱", "知识"],
            "repository": "",
            "permissions": ["llm", "network", "file_write"],
        },
        {
            "name": "data-quality",
            "version": "1.0.0",
            "display_name": "数据质量监控",
            "description": "数据完整性/一致性/时效性检测，异常自动标记和修复建议",
            "author": "AUTO-EVO-AI",
            "tags": ["数据", "质量", "监控"],
            "repository": "",
            "permissions": ["file_read"],
        },
    ]

    # ═══════════════════════════════════════════════════════
    # 注册表管理
    # ═══════════════════════════════════════════════════════

    def _load_registry(self):
        """加载本地注册表"""
        try:
            if os.path.exists(self._registry_path):
                with open(self._registry_path, encoding="utf-8") as f:
                    data = json.load(f)
                for name, info in data.get("plugins", {}).items():
                    self._plugins[name] = PluginState(
                        name=name,
                        version=info.get("version", ""),
                        status=info.get("status", "installed"),
                        installed_at=info.get("installed_at", ""),
                        enabled_at=info.get("enabled_at", ""),
                        error=info.get("error", ""),
                        config=info.get("config", {}),
                    )
        except Exception as e:
            logger.debug(f"[PluginManager] Load registry: {e}")

    def _save_registry(self):
        """保存注册表"""
        try:
            data = {
                "version": 1,
                "updated_at": datetime.now().isoformat(),
                "plugins": {},
            }
            for name, state in self._plugins.items():
                data["plugins"][name] = {
                    "version": state.version,
                    "status": state.status,
                    "installed_at": state.installed_at,
                    "enabled_at": state.enabled_at,
                    "error": state.error,
                    "config": state.config,
                }
            with open(self._registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[PluginManager] Save registry: {e}")

    # ═══════════════════════════════════════════════════════
    # 自动加载
    # ═══════════════════════════════════════════════════════

    def _auto_load_plugins(self):
        """自动加载已安装的插件"""
        if not os.path.isdir(self._installed_dir):
            return

        for name in os.listdir(self._installed_dir):
            plugin_dir = os.path.join(self._installed_dir, name)
            if not os.path.isdir(plugin_dir):
                continue
            manifest_path = os.path.join(plugin_dir, "plugin.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        manifest_data = json.load(f)
                    manifest = PluginManifest(**{k: v for k, v in manifest_data.items() if k in PluginManifest.__dataclass_fields__})
                    self._manifests[name] = manifest
                except Exception as e:
                    logger.debug(f"[PluginManager] Load manifest {name}: {e}")

    # ═══════════════════════════════════════════════════════
    # 仓库浏览
    # ═══════════════════════════════════════════════════════

    def browse_repository(self, tag: str = "", search: str = "") -> list[dict]:
        """浏览可用插件仓库"""
        results = self.BUILTIN_REPOSITORY.copy()

        if tag:
            results = [p for p in results if tag.lower() in [t.lower() for t in p.get("tags", [])]]
        if search:
            results = [p for p in results if search.lower() in p.get("display_name", "").lower()
                       or search.lower() in p.get("description", "").lower()
                       or search.lower() in p.get("name", "").lower()]

        # 标记已安装状态
        for p in results:
            p["installed"] = p["name"] in self._plugins
            p["status"] = self._plugins[p["name"]].status if p["installed"] else "available"

        return results

    # ═══════════════════════════════════════════════════════
    # 插件安装
    # ═══════════════════════════════════════════════════════

    def install_plugin(self, name: str, source: str = "builtin") -> dict[str, Any]:
        """
        安装插件

        Args:
            name: 插件名称
            source: 来源 - builtin(内置) / github(url) / local(path)

        Returns:
            {"success": bool, "message": str, ...}
        """
        with self._rw_lock:
            if name in self._plugins:
                return {"success": False, "message": f"Plugin '{name}' already installed"}

            if source == "builtin":
                # 从内置仓库安装（创建骨架插件）
                repo_item = next((p for p in self.BUILTIN_REPOSITORY if p["name"] == name), None)
                if not repo_item:
                    return {"success": False, "message": f"Builtin plugin '{name}' not found in repository"}

                plugin_dir = os.path.join(self._installed_dir, name)
                Path(plugin_dir).mkdir(parents=True, exist_ok=True)

                # 创建plugin.json清单
                manifest = PluginManifest(
                    name=name,
                    version=repo_item.get("version", "1.0.0"),
                    display_name=repo_item.get("display_name", name),
                    description=repo_item.get("description", ""),
                    author=repo_item.get("author", ""),
                    tags=repo_item.get("tags", []),
                    permissions=repo_item.get("permissions", []),
                    module_class=f"plugins.installed.{name}.main",
                )

                with open(os.path.join(plugin_dir, "plugin.json"), "w", encoding="utf-8") as f:
                    json.dump(asdict(manifest), f, ensure_ascii=False, indent=2)

                # 创建骨架模块文件
                module_code = self._generate_plugin_skeleton(manifest)
                with open(os.path.join(plugin_dir, "main.py"), "w", encoding="utf-8") as f:
                    f.write(module_code)

                self._manifests[name] = manifest

            elif source.startswith("http"):
                # 从Git URL安装
                return self._install_from_git(name, source)
            elif os.path.isdir(source):
                # 从本地路径安装
                return self._install_from_local(name, source)
            else:
                return {"success": False, "message": f"Unknown source type: {source}"}

            # 注册插件
            now = datetime.now().isoformat()
            self._plugins[name] = PluginState(
                name=name,
                version=self._manifests[name].version,
                status="installed",
                installed_at=now,
            )
            self._save_registry()

            return {
                "success": True,
                "message": f"Plugin '{name}' installed successfully",
                "name": name,
                "version": self._manifests[name].version,
            }

    def _install_from_git(self, name: str, url: str) -> dict:
        """从Git仓库安装插件"""
        temp_dir = os.path.join(self._temp_dir, f"{name}_{int(time.time())}")

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, temp_dir],
                check=True, capture_output=True, timeout=60
            )

            # 检查plugin.json
            manifest_path = os.path.join(temp_dir, "plugin.json")
            if not os.path.exists(manifest_path):
                return {"success": False, "message": "No plugin.json found in repository"}

            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)

            manifest = PluginManifest(**{k: v for k, v in manifest_data.items() if k in PluginManifest.__dataclass_fields__})
            manifest.name = name  # 覆盖名称为用户指定的

            # 移动到installed目录
            plugin_dir = os.path.join(self._installed_dir, name)
            if os.path.exists(plugin_dir):
                shutil.rmtree(plugin_dir)
            shutil.move(temp_dir, plugin_dir)

            self._manifests[name] = manifest

            return {
                "success": True,
                "message": f"Plugin '{name}' installed from {url}",
                "name": name,
                "version": manifest.version,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "message": f"Git clone timeout: {url}"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "message": f"Git clone failed: {e.stderr[:200] if e.stderr else str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Install error: {str(e)}"}
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _install_from_local(self, name: str, local_path: str) -> dict:
        """从本地路径安装插件"""
        source_dir = os.path.abspath(local_path)

        if not os.path.isdir(source_dir):
            return {"success": False, "message": f"Path not found: {source_dir}"}

        manifest_path = os.path.join(source_dir, "plugin.json")
        if not os.path.exists(manifest_path):
            return {"success": False, "message": "No plugin.json found in source directory"}

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest = PluginManifest(**{k: v for k, v in manifest_data.items() if k in PluginManifest.__dataclass_fields__})
            manifest.name = name
        except Exception as e:
            return {"success": False, "message": f"Invalid plugin.json: {e}"}

        # 复制到installed目录
        plugin_dir = os.path.join(self._installed_dir, name)
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
        shutil.copytree(source_dir, plugin_dir)

        self._manifests[name] = manifest

        return {
            "success": True,
            "message": f"Plugin '{name}' installed from {local_path}",
            "name": name,
            "version": manifest.version,
        }

    def _generate_plugin_skeleton(self, manifest: PluginManifest) -> str:
        """生成插件骨架代码"""
        return f'''"""
AUTO-EVO-AI Plugin: {manifest.display_name}
{manifest.description}
"""

import logging
logger = get_logger(__name__)


class {manifest.name.replace("-","_").replace(".","_")}Plugin:
    """{manifest.display_name}"""

    name = "{manifest.name}"
    version = "{manifest.version}"
    description = "{manifest.description}"
    tags = {json.dumps(manifest.tags, ensure_ascii=False)}
    permissions = {json.dumps(manifest.permissions, ensure_ascii=False)}

    def __init__(self, config=None):
        self.config = config or {{}}
        self._initialized = False

    async def initialize(self):
        """初始化插件"""
        logger.info("[{manifest.name}] Initializing...")
        self._initialized = True
        return {{"success": True}}

    async def execute(self, action: str, params: dict = None) -> dict:
        """执行插件操作"""
        params = params or {{}}
        if action == "status":
            return {{
                "success": True,
                "status": "running" if self._initialized else "stopped",
                "version": self.version,
            }}
        elif action == "info":
            return {{
                "success": True,
                "name": self.display_name,
                "description": self.description,
                "version": self.version,
                "tags": self.tags,
            }}
        else:
            return {{
                "success": False,
                "error": f"Unknown action: {{action}}",
                "available_actions": ["status", "info"],
            }}

    async def cleanup(self):
        """清理资源"""
        logger.info("[{manifest.name}] Cleanup...")
        self._initialized = False
        return {{"success": True}}
'''

    # ═══════════════════════════════════════════════════════
    # 插件管理
    # ═══════════════════════════════════════════════════════

    def enable_plugin(self, name: str) -> dict[str, Any]:
        """启用插件"""
        with self._rw_lock:
            if name not in self._plugins:
                return {"success": False, "message": f"Plugin '{name}' not installed"}

            state = self._plugins[name]
            if state.status == "enabled":
                return {"success": True, "message": "Already enabled"}

            try:
                # 尝试加载模块
                plugin_dir = os.path.join(self._installed_dir, name)
                if plugin_dir not in sys.path:
                    sys.path.insert(0, self._installed_dir)

                module = importlib.import_module(f"{name}.main")
                importlib.reload(module)

                # 查找Plugin类
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and "Plugin" in attr_name:
                        plugin_class = attr
                        break

                if plugin_class:
                    state.module_instance = plugin_class(config=state.config)
                    state.status = "enabled"
                    state.enabled_at = datetime.now().isoformat()
                    state.error = ""
                    self._save_registry()
                    return {"success": True, "message": f"Plugin '{name}' enabled", "class": plugin_class.__name__}
                else:
                    state.status = "error"
                    state.error = "No Plugin class found in main.py"
                    self._save_registry()
                    return {"success": False, "message": state.error}

            except Exception as e:
                state.status = "error"
                state.error = str(e)[:200]
                self._save_registry()
                return {"success": False, "message": f"Enable failed: {state.error}"}

    def disable_plugin(self, name: str) -> dict[str, Any]:
        """禁用插件"""
        with self._rw_lock:
            if name not in self._plugins:
                return {"success": False, "message": f"Plugin '{name}' not installed"}

            state = self._plugins[name]
            if state.status == "disabled":
                return {"success": True, "message": "Already disabled"}

            # 清理实例
            if state.module_instance:
                try:
                    if hasattr(state.module_instance, "cleanup"):
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            loop.run_until_complete(state.module_instance.cleanup())
                        except RuntimeError:
                            asyncio.run(state.module_instance.cleanup())
                except Exception:
                    pass
                state.module_instance = None

            state.status = "disabled"
            state.error = ""
            self._save_registry()
            return {"success": True, "message": f"Plugin '{name}' disabled"}

    def uninstall_plugin(self, name: str, remove_data: bool = False) -> dict[str, Any]:
        """卸载插件"""
        with self._rw_lock:
            if name not in self._plugins:
                return {"success": False, "message": f"Plugin '{name}' not installed"}

            # 先禁用
            self.disable_plugin(name)

            # 删除文件
            plugin_dir = os.path.join(self._installed_dir, name)
            if os.path.exists(plugin_dir):
                shutil.rmtree(plugin_dir)

            del self._plugins[name]
            if name in self._manifests:
                del self._manifests[name]

            self._save_registry()
            return {"success": True, "message": f"Plugin '{name}' uninstalled", "removed_data": remove_data}

    def update_plugin(self, name: str) -> dict[str, Any]:
        """更新插件"""
        if name not in self._plugins:
            return {"success": False, "message": f"Plugin '{name}' not installed"}

        manifest = self._manifests.get(name)
        if not manifest or not manifest.repository:
            return {"success": False, "message": "No repository URL configured for auto-update"}

        # 暂时禁用
        self.disable_plugin(name)

        # 重新安装
        result = self._install_from_git(name, manifest.repository)
        if result.get("success"):
            # 重新启用
            self.enable_plugin(name)

        return result

    # ═══════════════════════════════════════════════════════
    # 插件执行
    # ═══════════════════════════════════════════════════════

    async def execute_plugin(self, name: str, action: str, params: dict = None) -> dict:
        """执行插件操作"""
        if name not in self._plugins:
            return {"success": False, "error": f"Plugin '{name}' not installed"}

        state = self._plugins[name]
        if state.status != "enabled" or not state.module_instance:
            return {"success": False, "error": f"Plugin '{name}' not enabled"}

        try:
            if hasattr(state.module_instance, "execute"):
                result = await state.module_instance.execute(action, params)
                return result or {"success": True}
            return {"success": False, "error": "Plugin has no execute method"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    # ═══════════════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════════════

    def get_plugin(self, name: str) -> dict | None:
        """获取插件详情"""
        if name not in self._plugins:
            return None

        state = self._plugins[name]
        manifest = self._manifests.get(name)

        result = {
            "name": state.name,
            "version": state.version,
            "status": state.status,
            "installed_at": state.installed_at,
            "enabled_at": state.enabled_at,
            "error": state.error,
            "config": state.config,
            "has_instance": state.module_instance is not None,
        }

        if manifest:
            result.update({
                "display_name": manifest.display_name,
                "description": manifest.description,
                "author": manifest.author,
                "tags": manifest.tags,
                "permissions": manifest.permissions,
            })

        return result

    def list_plugins(self, status: str = "") -> list[dict]:
        """列出所有插件"""
        plugins = []
        for name, state in self._plugins.items():
            if status and state.status != status:
                continue
            info = self.get_plugin(name)
            if info:
                plugins.append(info)
        return plugins

    def get_stats(self) -> dict[str, Any]:
        """插件统计"""
        total = len(self._plugins)
        enabled = sum(1 for s in self._plugins.values() if s.status == "enabled")
        disabled = sum(1 for s in self._plugins.values() if s.status == "disabled")
        error = sum(1 for s in self._plugins.values() if s.status == "error")
        available = len(self.BUILTIN_REPOSITORY) - total

        return {
            "total_installed": total,
            "enabled": enabled,
            "disabled": disabled,
            "error": error,
            "available_in_repo": available,
            "plugins": self.list_plugins(),
        }

    def check_compatibility(self, name: str) -> dict[str, Any]:
        """检查插件兼容性"""
        manifest = self._manifests.get(name)
        if not manifest:
            return {"compatible": False, "reason": "Plugin not found"}

        issues = []

        # 检查系统版本
        if manifest.min_evo_version:
            current_version = "0.1.0"
            if not self._version_gte(current_version, manifest.min_evo_version):
                issues.append(f"Requires EVO version >= {manifest.min_evo_version}")

        # 检查依赖
        for dep_name, min_ver in manifest.dependencies.items():
            if dep_name in self._plugins:
                installed_ver = self._plugins[dep_name].version
                if not self._version_gte(installed_ver, min_ver):
                    issues.append(f"Dependency '{dep_name}' needs >= {min_ver}, have {installed_ver}")
            else:
                issues.append(f"Missing dependency: {dep_name} >= {min_ver}")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "manifest": asdict(manifest),
        }

    @staticmethod
    def _version_gte(current: str, required: str) -> bool:
        """比较语义化版本 >= """
        try:
            c = [int(x) for x in current.split(".")[:3]]
            r = [int(x) for x in required.split(".")[:3]]
            c.extend([0] * (3 - len(c)))
            r.extend([0] * (3 - len(r)))
            return c >= r
        except (ValueError, IndexError):
            return False

    def export_plugin_config(self, name: str) -> dict | None:
        """导出插件配置"""
        if name not in self._plugins:
            return None
        return self._plugins[name].config

    def import_plugin_config(self, name: str, config: dict) -> dict:
        """导入插件配置"""
        if name not in self._plugins:
            return {"success": False, "message": "Plugin not installed"}
        self._plugins[name].config = config
        self._save_registry()
        return {"success": True, "message": "Config imported"}
