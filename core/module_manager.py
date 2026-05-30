#!/usr/bin/env python3
"""
AUTO-EVO-AI V0.1 模块管理器
统一管理所有功能模块的加载、调度和执行
"""

import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
from datetime import datetime

from .evolution_engine import engine as evo_engine
from .module_base import ModuleBase


class ModuleManager:
    """模块管理器"""

    def __init__(self):
        self.modules: Dict[str, ModuleBase] = {}
        self.module_registry: Dict[str, Type[ModuleBase]] = {}
        self.module_metadata: Dict[str, Dict] = {}
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "start_time": datetime.now().isoformat()
        }

    def register_module_class(self, module_id: str, module_class: Type[ModuleBase]):
        self.module_registry[module_id] = module_class

    def register_module(self, module: ModuleBase):
        self.modules[module.id] = module

    def get_module(self, module_id: str) -> Optional[ModuleBase]:
        if module_id in self.modules:
            return self.modules[module_id]
        if module_id in self.module_registry:
            module_class = self.module_registry[module_id]
            instance = module_class(module_id)
            self.modules[module_id] = instance
            return instance
        return None

    def get_all_modules(self) -> List[ModuleBase]:
        return list(self.modules.values())

    def get_enabled_modules(self) -> List[ModuleBase]:
        return [m for m in self.modules.values() if m.enabled]

    async def execute_module(self, module_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.stats["total_calls"] += 1
        module = self.get_module(module_id)
        action = params.get("action", "execute")
        start = time.monotonic()
        if not module:
            self.stats["failed_calls"] += 1
            evo_engine.record(module_id, action, False, 0, "模块不存在")
            return {"success": False, "error": f"模块 {module_id} 不存在"}
        if not module.enabled:
            self.stats["failed_calls"] += 1
            evo_engine.record(module_id, action, False, 0, "模块已禁用")
            return {"success": False, "error": f"模块 {module_id} 已禁用"}
        try:
            result = await module.execute(params)
            elapsed = (time.monotonic() - start) * 1000
            ok = result.get("success", True)
            err = result.get("error", "")
            evo_engine.record(module_id, action, ok, elapsed, err)
            if ok:
                self.stats["successful_calls"] += 1
            else:
                self.stats["failed_calls"] += 1
            return result
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self.stats["failed_calls"] += 1
            evo_engine.record(module_id, action, False, elapsed, str(e))
            return {"success": False, "error": str(e)}

    async def execute_chain(self, module_ids: List[str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        shared_context = params.copy()
        for module_id in module_ids:
            result = await self.execute_module(module_id, shared_context)
            results.append({"module": module_id, "result": result})
            shared_context[f"_{module_id}_result"] = result
        return results

    async def execute_parallel(self, module_ids: List[str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        tasks = [self.execute_module(mid, params) for mid in module_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"module": module_ids[i], "result": r if not isinstance(r, Exception) else {"success": False, "error": str(r)}}
            for i, r in enumerate(results)
        ]

    def load_metadata_from_html(self, html_path: str):
        """从 HTML 中解析 DEFAULT_MODULES 数组，支持跨行字段值"""
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        import re

        # 提取 DEFAULT_MODULES 数组体
        match = re.search(r'const DEFAULT_MODULES\s*=\s*\[(.*?)\];', content, re.DOTALL)
        if not match:
            return
        modules_text = match.group(1)

        # 逐对象解析：按 { ... } 拆分每个模块对象
        # 使用 id 作为分割锚点，确保每个模块独立解析
        # 先找所有对象起始位置（每个对象以 "{ id:" 开头）
        obj_starts = [m.start() for m in re.finditer(r'\{\s*id\s*:', modules_text)]

        def extract_field(obj_text: str, field: str) -> str:
            """从单个对象文本中提取字段值，支持跨行"""
            # 匹配 field: 'value' 或 field: "value"，value 可含换行
            pat = re.compile(
                rf"{field}\s*:\s*'((?:[^'\\]|\\.)*)'"  # 单引号
                rf"|{field}\s*:\s*\"((?:[^\"\\]|\\.)*)\"",  # 双引号
                re.DOTALL
            )
            m = pat.search(obj_text)
            if m:
                val = m.group(1) if m.group(1) is not None else m.group(2)
                # 清理跨行产生的多余空白
                val = re.sub(r'\s+', ' ', val).strip()
                return val
            return ""

        count_before = len(self.module_metadata)
        for i, start in enumerate(obj_starts):
            # 确定对象结束位置：下一个对象起始 或 文本末尾
            end = obj_starts[i + 1] if i + 1 < len(obj_starts) else len(modules_text)
            obj_text = modules_text[start:end]

            module_id = extract_field(obj_text, 'id')
            if not module_id:
                continue

            self.module_metadata[module_id] = {
                "id": module_id,
                "name": extract_field(obj_text, 'name') or module_id,
                "group": extract_field(obj_text, 'group') or "未分类",
                "desc": extract_field(obj_text, 'desc'),
                "icon": extract_field(obj_text, 'icon') or "📦",
                "source": extract_field(obj_text, 'source'),
                "color": extract_field(obj_text, 'color') or "#6366F1",
                "stars": extract_field(obj_text, 'stars'),
            }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "registered_modules": len(self.modules),
            "enabled_modules": len(self.get_enabled_modules()),
            "groups": len(set(m.get("group") for m in self.module_metadata.values()))
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        groups = {}
        for module_id, meta in self.module_metadata.items():
            group = meta.get("group", "未分类")
            if group not in groups:
                groups[group] = []
            groups[group].append({**meta})
        return {
            "groups": groups,
            "stats": self.get_stats(),
            "total_modules": len(self.module_metadata),
            "total_groups": len(groups)
        }


__all__ = ["ModuleManager"]
