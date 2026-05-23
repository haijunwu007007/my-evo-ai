"""
AUTO-EVO-AI v7.0 — 模块元数据标准
===================================
上市公司生产级实现 — 数据类定义、Schema验证、序列化

核心概念:
  - 每个功能模块通过 __module_meta__ 模块级变量声明自身能力
  - ModuleMeta 描述模块的 输入/输出/触发条件/依赖关系/健康状况
  - OrchestrationEngine 通过元数据自动发现、组合、调度模块

用法:
    # 在任意模块文件顶部声明
    __module_meta__ = ModuleMeta(
        id="github-scanner",
        name="GitHub 项目扫描器",
        version="2.0.0",
        group="github",
        inputs=[ModuleIO(name="keywords", type="list[string]", required=True)],
        outputs=[ModuleIO(name="repos", type="list[dict]", description="扫描结果")],
        triggers=[
            ModuleTrigger(type="schedule", config={"cron": "0 */4 * * *"}),
            ModuleTrigger(type="event", config={"on": "github.scan.request"}),
        ],
        depends_on=["database-client", "cache-engine"],
        tags=["github", "scanner", "core"],
    )
"""

from __future__ import annotations

import re
import json
import time
import hashlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict, is_dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# 数据类型枚举
# ============================================================


class ModuleStatus(Enum):
    """模块生命周期状态"""

    PENDING = "pending"  # 待初始化
    ACTIVE = "active"  # 运行中
    DEGRADED = "degraded"  # 降级运行
    STOPPED = "stopped"  # 已停止
    ERROR = "error"  # 异常
    UNKNOWN = "unknown"  # 未知


class IODirection(Enum):
    """IO方向"""

    INPUT = "input"
    OUTPUT = "output"


# ============================================================
# 数据类型（生产级 data class）
# ============================================================


@dataclass
class ModuleIO:
    """模块输入/输出参数描述

    Attributes:
        name:        参数名
        type:        数据类型 (string, int, float, bool, list[string], dict, file, any)
        required:    是否必填
        default:     默认值
        description: 参数说明
    """

    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

    def __post_init__(self):
        self._validate_type()

    def _validate_type(self):
        """校验 type 格式"""
        valid_base = {"string", "int", "float", "bool", "dict", "any", "file", "bytes"}
        if self.type in valid_base:
            return
        # 支持 list[T] 格式
        if re.match(r"^list\[(string|int|float|bool|dict|any)\]$", self.type):
            return
        # 支持 dict[K,V] 格式
        if re.match(r"^dict\[(string|int),\s*(string|int|float|bool|any)\]$", self.type):
            return
        logger.warning(f"ModuleIO '{self.name}' 使用了非标准类型 '{self.type}'")

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> ModuleIO:
        return ModuleIO(**data)

    def __hash__(self):
        return hash(self.name)


@dataclass
class ModuleTrigger:
    """模块触发条件

    类型说明:
        - event:       订阅EventBus事件触发 (config.on)
        - schedule:    定时触发 (config.cron)
        - webhook:     HTTP webhook触发 (config.path, config.method)
        - file_watch:  文件变更触发 (config.path)
        - dependent:   依赖模块完成触发 (config.on_module)
    """

    type: str = "manual"  # event, schedule, webhook, file_watch, dependent, manual
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        valid_types = {"event", "schedule", "webhook", "file_watch", "dependent", "manual"}
        if self.type not in valid_types:
            raise ValueError(f"触发类型必须为 {valid_types}，收到 '{self.type}'")
        self._validate_config()

    def _validate_config(self):
        if self.type == "event" and "on" not in self.config:
            logger.warning(f"event类型触发缺少 'on' 配置")
        if self.type == "schedule" and "cron" not in self.config:
            logger.warning(f"schedule类型触发缺少 'cron' 配置")
        if self.type == "webhook" and "path" not in self.config:
            logger.warning(f"webhook类型触发缺少 'path' 配置")
        if self.type == "file_watch" and "path" not in self.config:
            logger.warning(f"file_watch类型触发缺少 'path' 配置")
        if self.type == "dependent" and "on_module" not in self.config:
            logger.warning(f"dependent类型触发缺少 'on_module' 配置")

    def to_dict(self) -> dict:
        return {"type": self.type, "config": self.config}

    @staticmethod
    def from_dict(data: dict) -> ModuleTrigger:
        return ModuleTrigger(type=data.get("type", "manual"), config=data.get("config", {}))


@dataclass
class ModuleHealthCheck:
    """模块健康检查配置"""

    interval_seconds: int = 60  # 检查间隔
    timeout_seconds: int = 10  # 超时时间
    expected_status: str = "active"  # 期望状态
    retry_count: int = 3  # 重试次数
    fallback_module: Optional[str] = None  # 降级替代模块ID

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> ModuleHealthCheck:
        return ModuleHealthCheck(**data)


@dataclass
class ModuleMeta:
    """模块元数据——完整的自我描述

    用法:
        # 在模块文件头部声明
        __module_meta__ = ModuleMeta(
            id="my-module",
            name="我的模块",
            version="1.0.0",
            group="custom",
            inputs=[ModuleIO(name="param1", type="string", required=True)],
            outputs=[ModuleIO(name="result", type="dict")],
        )

    Attributes:
        id:           全局唯一模块ID（小写英数连字符）
        name:         模块显示名称
        version:      语义化版本号
        group:        模块分组（communication, database, ai, github, ...）
        inputs:       输入参数列表
        outputs:      输出参数列表
        triggers:     触发条件列表
        depends_on:   依赖的模块ID列表
        health_check: 健康检查配置（None表示不启用）
        tags:         标签列表
        grade:        生产等级 (S/A/B/C)
        author:       作者
        license:      许可证
        description:  长描述
    """

    id: str
    name: str = ""
    version: str = "1.0.0"
    group: str = "uncategorized"
    inputs: List[ModuleIO] = field(default_factory=list)
    outputs: List[ModuleIO] = field(default_factory=list)
    triggers: List[ModuleTrigger] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    health_check: Optional[ModuleHealthCheck] = None
    tags: List[str] = field(default_factory=list)
    grade: str = "B"
    author: str = "AUTO-EVO-AI"
    license: str = "GPL-3.0"
    description: str = ""

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """校验元数据合法性"""
        if not self.id or not re.match(r"^[a-z0-9][a-z0-9\-]*$", self.id):
            raise ValueError(f"模块ID '{self.id}' 格式无效：必须是小写字母、数字、连字符")
        if not re.match(r"^\d+\.\d+\.\d+$", self.version):
            logger.warning(f"模块 '{self.id}' 版本号 '{self.version}' 不符合 semver 规范")
        valid_grades = {"S", "A", "B", "C"}
        if self.grade not in valid_grades:
            logger.warning(f"模块 '{self.id}' 等级 '{self.grade}' 无效，使用 'B'")
            self.grade = "B"
        # 校验输入输出名称唯一
        input_names = [io.name for io in self.inputs]
        if len(input_names) != len(set(input_names)):
            dups = [n for n in input_names if input_names.count(n) > 1]
            logger.warning(f"模块 '{self.id}' inputs 中存在重复名称 {set(dups)}，自动去重")
            seen = set()
            self.inputs = [io for io in self.inputs if not (io.name in seen or seen.add(io.name))]
        output_names = [io.name for io in self.outputs]
        if len(output_names) != len(set(output_names)):
            dups = [n for n in output_names if output_names.count(n) > 1]
            logger.warning(f"模块 '{self.id}' outputs 中存在重复名称 {set(dups)}，自动去重")
            seen = set()
            self.outputs = [io for io in self.outputs if not (io.name in seen or seen.add(io.name))]

    def get_required_inputs(self) -> List[str]:
        return [io.name for io in self.inputs if io.required]

    def get_optional_inputs(self) -> List[str]:
        return [io.name for io in self.inputs if not io.required]

    def has_event_trigger(self, event_name: str = "") -> bool:
        """是否订阅了指定事件"""
        for t in self.triggers:
            if t.type == "event":
                if not event_name or t.config.get("on") == event_name:
                    return True
        return False

    def has_schedule(self) -> bool:
        return any(t.type == "schedule" for t in self.triggers)

    def input_types(self) -> Dict[str, str]:
        return {io.name: io.type for io in self.inputs}

    def output_types(self) -> Dict[str, str]:
        return {io.name: io.type for io in self.outputs}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name or self.id,
            "version": self.version,
            "group": self.group,
            "inputs": [io.to_dict() for io in self.inputs],
            "outputs": [io.to_dict() for io in self.outputs],
            "triggers": [t.to_dict() for t in self.triggers],
            "depends_on": self.depends_on,
            "health_check": self.health_check.to_dict() if self.health_check else None,
            "tags": self.tags,
            "grade": self.grade,
            "author": self.author,
            "license": self.license,
            "description": self.description,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(data: dict) -> ModuleMeta:
        inputs = [ModuleIO.from_dict(io) for io in data.get("inputs", [])]
        outputs = [ModuleIO.from_dict(io) for io in data.get("outputs", [])]
        triggers = [ModuleTrigger.from_dict(t) for t in data.get("triggers", [])]
        hc = data.get("health_check")
        health_check = ModuleHealthCheck.from_dict(hc) if hc and isinstance(hc, dict) else None
        return ModuleMeta(
            id=data["id"],
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            group=data.get("group", "uncategorized"),
            inputs=inputs,
            outputs=outputs,
            triggers=triggers,
            depends_on=data.get("depends_on", []),
            health_check=health_check,
            tags=data.get("tags", []),
            grade=data.get("grade", "B"),
            author=data.get("author", "AUTO-EVO-AI"),
            license=data.get("license", "GPL-3.0"),
            description=data.get("description", ""),
        )

    @staticmethod
    def from_module(module: Any) -> Optional[ModuleMeta]:
        """从模块对象中提取 __module_meta__"""
        raw = getattr(module, "__module_meta__", None)
        if raw is None:
            return None
        if isinstance(raw, ModuleMeta):
            return raw
        if isinstance(raw, dict):
            return ModuleMeta.from_dict(raw)
        return None

    @staticmethod
    def _ast_to_python(node) -> object:
        """将 AST 节点递归转换为 Python 对象

        兼容 Python 字面量和 JSON 风格值：
          - true/True → True
          - false/False → False
          - null/None → None
        """
        import ast as _ast

        if isinstance(node, _ast.Constant):
            return node.value
        if isinstance(node, _ast.List):
            return [ModuleMeta._ast_to_python(e) for e in node.elts]
        if isinstance(node, _ast.Tuple):
            return tuple(ModuleMeta._ast_to_python(e) for e in node.elts)
        if isinstance(node, _ast.Dict):
            return {
                ModuleMeta._ast_to_python(k): ModuleMeta._ast_to_python(v)
                for k, v in zip(node.keys, node.values) if k is not None
            }
        if isinstance(node, _ast.Name):
            name = node.id
            if name in ("True", "true"):
                return True
            if name in ("False", "false"):
                return False
            if name in ("None", "null"):
                return None
            return name  # fallback: return as string
        if isinstance(node, _ast.UnaryOp) and isinstance(node.op, _ast.USub):
            return -ModuleMeta._ast_to_python(node.operand)
        # unrecognized → fallback to literal_eval
        try:
            from ast import literal_eval
            return literal_eval(node)
        except Exception:
            return None

    @staticmethod
    def from_file(filepath: str) -> Optional[ModuleMeta]:
        """从 Python 文件提取元数据（AST解析，不执行模块）

        生产级实现：
          - 使用 AST 递归遍历，无需执行模块代码
          - 兼容 Python 字面量和 JSON 混合格式（true/false/null vs True/False/None）
          - 支持 dict 字面量和 ModuleMeta() 构造函数两种写法
        """
        import ast as _ast
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = _ast.parse(f.read())
        except Exception as e:
            logger.debug(f"从 {filepath} 解析AST失败: {e}")
            return None

        for node in tree.body:
            if not isinstance(node, _ast.Assign):
                continue
            for target in node.targets:
                if not (isinstance(target, _ast.Name) and target.id == "__module_meta__"):
                    continue
                val = node.value
                try:
                    # 格式1: dict 字面量
                    if isinstance(val, _ast.Dict):
                        meta_dict = ModuleMeta._ast_to_python(val)
                        if isinstance(meta_dict, dict):
                            return ModuleMeta.from_dict(meta_dict)
                    # 格式2: ModuleMeta(...) 构造函数
                    elif isinstance(val, _ast.Call) and isinstance(val.func, _ast.Name) and val.func.id == "ModuleMeta":
                        kwargs = {}
                        for kw in val.keywords:
                            if kw.arg is None:
                                continue
                            kwargs[kw.arg] = ModuleMeta._ast_to_python(kw.value)
                        if "id" in kwargs:
                            return ModuleMeta.from_dict(kwargs)
                except Exception as e:
                    logger.debug(f"从 {filepath} 解析 __module_meta__ 失败: {e}")
                    return None
        return None


# ============================================================
# Schema验证器
# ============================================================


class SchemaValidator:
    """模块IO Schema 验证器

    验证输入参数是否符合模块声明的类型规范。
    支持嵌套类型检查（list[dict], dict[string,int] 等）。
    """

    TYPE_PARSERS = {
        "string": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int),
        "float": lambda v: isinstance(v, (int, float)),
        "bool": lambda v: isinstance(v, bool),
        "dict": lambda v: isinstance(v, dict),
        "any": lambda v: True,
        "file": lambda v: isinstance(v, (str, bytes)),
        "bytes": lambda v: isinstance(v, (bytes, bytearray)),
    }

    @classmethod
    def validate(cls, params: Dict[str, Any], io_list: List[ModuleIO]) -> List[str]:
        """验证参数是否符合 IO 规范，返回错误列表（空=全部通过）"""
        errors: List[str] = []
        io_map = {io.name: io for io in io_list}

        # 检查必填字段
        for io in io_list:
            if io.required and io.name not in params:
                errors.append(f"缺少必填参数 '{io.name}' (type={io.type})")

        # 检查参数类型
        for name, value in params.items():
            if name not in io_map:
                errors.append(f"未知参数 '{name}'，不在模块IO声明中")
                continue
            io_def = io_map[name]
            if not cls._check_type(value, io_def.type):
                errors.append(f"参数 '{name}' 类型错误: 期望 {io_def.type}, 实际 {type(value).__name__}")

        return errors

    @classmethod
    def _check_type(cls, value: Any, type_str: str) -> bool:
        """递归检查类型"""
        # 基础类型
        if type_str in cls.TYPE_PARSERS:
            return cls.TYPE_PARSERS[type_str](value)

        # list[T]
        list_match = re.match(r"^list\[(\w+)\]$", type_str)
        if list_match and isinstance(value, list):
            inner = list_match.group(1)
            return all(cls._check_type(v, inner) for v in value)

        # dict[K,V]
        dict_match = re.match(r"^dict\[(\w+),\s*(\w+)\]$", type_str)
        if dict_match and isinstance(value, dict):
            ktype, vtype = dict_match.group(1), dict_match.group(2)
            return all(cls._check_type(k, ktype) and cls._check_type(v, vtype) for k, v in value.items())

        return False


# ============================================================
# 依赖解析器
# ============================================================


class DependencyResolver:
    """模块依赖解析器——拓扑排序

    分析模块间的依赖关系，生成可执行的顺序。
    支持环检测、缺失依赖检测。
    """

    def __init__(self):
        self._module_metas: Dict[str, ModuleMeta] = {}

    def register(self, meta: ModuleMeta):
        self._module_metas[meta.id] = meta

    def register_many(self, metas: List[ModuleMeta]):
        for m in metas:
            self.register(m)

    def resolve(self, target_ids: List[str]) -> Tuple[List[str], List[str]]:
        """拓扑排序，返回 (有序列表, 错误列表)"""
        graph: Dict[str, Set[str]] = {}
        for mid in target_ids:
            meta = self._module_metas.get(mid)
            if not meta:
                continue
            deps = set(meta.depends_on) & set(target_ids)
            graph[mid] = deps

        # 检测环
        cycle_errors = self._detect_cycles(graph)
        if cycle_errors:
            return [], cycle_errors

        # 缺失依赖检查
        missing = []
        for mid in target_ids:
            meta = self._module_metas.get(mid)
            if not meta:
                missing.append(f"模块 '{mid}' 未注册")
                continue
            for dep in meta.depends_on:
                if dep not in self._module_metas:
                    missing.append(f"模块 '{mid}' 的依赖 '{dep}' 不存在")
                elif dep not in graph and dep not in target_ids:
                    missing.append(f"模块 '{mid}' 的依赖 '{dep}' 不在目标列表中")

        if missing:
            return [], missing

        # Kahn 拓扑排序
        in_degree: Dict[str, int] = {n: 0 for n in graph}
        for n, deps in graph.items():
            for d in deps:
                in_degree[n] = in_degree.get(n, 0) + 1  # 反向：依赖多→入度大

        # 重新初始化：边方向为 A→B 表示 A依赖B
        in_degree = {n: 0 for n in graph}
        reverse_graph: Dict[str, Set[str]] = {n: set() for n in graph}
        for n, deps in graph.items():
            for d in deps:
                reverse_graph[d].add(n)
                in_degree[n] = in_degree.get(n, 0) + 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        ordered = []

        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for neighbor in reverse_graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(graph):
            return [], ["无法解析依赖顺序，可能存在残余环"]

        return ordered, []

    def _detect_cycles(self, graph: Dict[str, Set[str]]) -> List[str]:
        """DFS环检测"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}
        parent: Dict[str, Optional[str]] = {n: None for n in graph}
        cycles: List[str] = []

        def dfs(node: str):
            color[node] = GRAY
            for neighbor in graph.get(node, set()):
                if color.get(neighbor) == GRAY:
                    # 找到环
                    path = [neighbor]
                    cur = node
                    while cur != neighbor:
                        path.append(cur)
                        cur = parent.get(cur, "")
                        if cur is None:
                            break
                    path.append(neighbor)
                    path.reverse()
                    cycles.append(" → ".join(path))
                elif color.get(neighbor) == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor)
            color[node] = BLACK

        for n in list(graph.keys()):
            if color.get(n) == WHITE:
                dfs(n)

        return cycles

    def get_parallel_groups(self, target_ids: List[str]) -> List[List[str]]:
        """将依赖解析结果分组为并行执行层"""
        ordered, errors = self.resolve(target_ids)
        if errors:
            return [target_ids]  # 出错则全串行

        # 按依赖深度分层
        depth: Dict[str, int] = {}
        for mid in ordered:
            meta = self._module_metas.get(mid)
            if not meta:
                depth[mid] = 0
                continue
            dep_depths = [depth.get(d, 0) for d in meta.depends_on if d in depth]
            depth[mid] = max(dep_depths) + 1 if dep_depths else 0

        groups: Dict[int, List[str]] = defaultdict(list)
        for mid, d in depth.items():
            groups[d].append(mid)

        return [groups[k] for k in sorted(groups.keys())]


# ============================================================
# 模块注册表
# ============================================================


class ModuleRegistry:
    """全局模块注册表——单例

    存储所有已发现模块的元数据。
    提供按ID/分组/标签/触发类型查询的能力。
    """

    _instance: Optional[ModuleRegistry] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._metas: Dict[str, ModuleMeta] = {}
        self._source_files: Dict[str, str] = {}  # module_id → filepath
        self._resolver = DependencyResolver()

    # ── 注册 ──

    def register(self, module_id: str, meta: ModuleMeta, source_file: str = ""):
        self._metas[module_id] = meta
        if source_file:
            self._source_files[module_id] = source_file
        self._resolver.register(meta)
        logger.info(f"模块注册: {module_id} v{meta.version} [{meta.group}]")

    def register_from_file(self, filepath: str, module_id: Optional[str] = None):
        meta = ModuleMeta.from_file(filepath)
        if meta:
            mid = module_id or meta.id
            self.register(mid, meta, filepath)
            return meta
        return None

    def unregister(self, module_id: str):
        self._metas.pop(module_id, None)
        self._source_files.pop(module_id, None)
        logger.info(f"模块注销: {module_id}")

    # ── 查询 ──

    def get(self, module_id: str) -> Optional[ModuleMeta]:
        return self._metas.get(module_id)

    def get_all(self) -> List[ModuleMeta]:
        return list(self._metas.values())

    def get_by_group(self, group: str) -> List[ModuleMeta]:
        return [m for m in self._metas.values() if m.group == group]

    def get_by_tag(self, tag: str) -> List[ModuleMeta]:
        return [m for m in self._metas.values() if tag in m.tags]

    def get_by_grade(self, grade: str) -> List[ModuleMeta]:
        return [m for m in self._metas.values() if m.grade == grade]

    def get_triggered_by_event(self, event_name: str) -> List[ModuleMeta]:
        return [m for m in self._metas.values() if m.has_event_trigger(event_name)]

    def get_scheduled(self) -> List[ModuleMeta]:
        return [m for m in self._metas.values() if m.has_schedule()]

    def get_with_dep(self, dep_module_id: str) -> List[ModuleMeta]:
        """返回所有依赖了 dep_module_id 的模块"""
        return [m for m in self._metas.values() if dep_module_id in m.depends_on]

    def count(self) -> int:
        return len(self._metas)

    def source_of(self, module_id: str) -> str:
        return self._source_files.get(module_id, "")

    def groups(self) -> Dict[str, int]:
        """返回分组统计：group_name → count"""
        result: Dict[str, int] = defaultdict(int)
        for m in self._metas.values():
            result[m.group] += 1
        return dict(sorted(result.items()))

    def get_stats(self) -> dict:
        return {
            "total_modules": self.count(),
            "groups": self.groups(),
            "by_grade": {g: len(self.get_by_grade(g)) for g in ["S", "A", "B", "C"]},
            "scheduled": len(self.get_scheduled()),
            "event_driven": len(self.get_triggered_by_event("")),
            "with_health_check": sum(1 for m in self._metas.values() if m.health_check is not None),
            "source_files": len(self._source_files),
        }

    # ── 序列化 ──

    def to_dict(self) -> dict:
        return {
            "modules": {mid: meta.to_dict() for mid, meta in self._metas.items()},
            "stats": self.get_stats(),
        }

    def export_capability_map(self) -> dict:
        """导出能力地图——什么模块能做什么"""
        return {
            "triggers": {
                "event": [m.id for m in self._metas.values() if m.has_event_trigger()],
                "schedule": [m.id for m in self._metas.values() if m.has_schedule()],
            },
            "dependencies": self._resolve_dependency_graph(),
        }

    def _resolve_dependency_graph(self) -> Dict[str, List[str]]:
        graph: Dict[str, List[str]] = {}
        for mid, meta in self._metas.items():
            graph[mid] = meta.depends_on
        return graph

    def resolve_pipeline(self, module_ids: List[str]) -> Tuple[List[str], List[str]]:
        """解析执行顺序，返回 (有序模块ID列表, 错误列表)"""
        return self._resolver.resolve(module_ids)

    def get_parallel_layers(self, module_ids: List[str]) -> List[List[str]]:
        """返回分层并行执行计划"""
        return self._resolver.get_parallel_groups(module_ids)


# ============================================================
# 工具函数
# ============================================================


def extract_meta_from_file(filepath: str) -> Optional[ModuleMeta]:
    """从 Python 文件提取模块元数据"""
    return ModuleMeta.from_file(filepath)


def extract_meta_from_object(obj: Any) -> Optional[ModuleMeta]:
    """从模块对象提取 __module_meta__"""
    return ModuleMeta.from_module(obj)


def validate_input(params: Dict[str, Any], io_list: List[ModuleIO]) -> List[str]:
    """快速验证输入参数"""
    return SchemaValidator.validate(params, io_list)


def validate_output(results: Dict[str, Any], io_list: List[ModuleIO]) -> List[str]:
    """快速验证输出结果"""
    return SchemaValidator.validate(results, io_list)


__all__ = [
    "ModuleMeta",
    "ModuleIO",
    "ModuleTrigger",
    "ModuleHealthCheck",
    "ModuleStatus",
    "IODirection",
    "ModuleRegistry",
    "DependencyResolver",
    "SchemaValidator",
    "extract_meta_from_file",
    "extract_meta_from_object",
    "validate_input",
    "validate_output",
]
