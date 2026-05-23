#!/usr/bin/env python3
"""
AUTO-EVO-AI V0.1 模块基类
所有功能模块的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json


class ModuleBase(ABC):
    """模块基类"""

    def __init__(self, module_id: str, config: Optional[Dict] = None):
        self.id = module_id
        self.config = config or {}
        self.enabled = True
        self.usage_count = 0
        self.last_used = None
        self.status = "idle"  # idle, running, success, error

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行模块功能
        返回执行结果
        """
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        pass

    async def validate(self, params: Dict[str, Any]) -> bool:
        """验证参数是否有效"""
        return True

    async def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行前钩子"""
        self.status = "running"
        self.usage_count += 1
        return params

    async def post_execute(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """执行后钩子"""
        self.last_used = datetime.now()
        self.status = "success" if result.get("success") else "error"
        return result

    def enable(self):
        """启用模块"""
        self.enabled = True

    def disable(self):
        """禁用模块"""
        self.enabled = False

    def get_stats(self) -> Dict[str, Any]:
        """获取模块统计"""
        return {
            "id": self.id,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "status": self.status,
            "enabled": self.enabled
        }


class CompositeModule(ModuleBase):
    """组合模块 - 包含多个子模块"""

    def __init__(self, module_id: str, sub_modules: List[ModuleBase], config: Optional[Dict] = None):
        super().__init__(module_id, config)
        self.sub_modules = {m.id: m for m in sub_modules}

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        for name, module in self.sub_modules.items():
            if module.enabled:
                try:
                    results[name] = await module.execute(params)
                except Exception as e:
                    results[name] = {"error": str(e)}
        return {"sub_results": results}

    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "composite",
            "sub_modules": list(self.sub_modules.keys())
        }


class AsyncModule(ModuleBase):
    """异步模块 - 支持长时间运行任务"""

    def __init__(self, module_id: str, config: Optional[Dict] = None):
        super().__init__(module_id, config)
        self.task = None
        self.progress = 0

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = await self.pre_execute(params)

        try:
            result = await self._run_async(params)
            return await self.post_execute({"success": True, "data": result})
        except Exception as e:
            self.status = "error"
            return {"success": False, "error": str(e)}

    @abstractmethod
    async def _run_async(self, params: Dict[str, Any]) -> Any:
        """实际的异步执行逻辑"""
        pass

    async def get_progress(self) -> float:
        """获取执行进度"""
        return self.progress

    async def cancel(self):
        """取消执行"""
        if self.task:
            self.task.cancel()
            self.status = "idle"


class StreamingModule(ModuleBase):
    """流式模块 - 支持流式输出"""

    def __init__(self, module_id: str, config: Optional[Dict] = None):
        super().__init__(module_id, config)
        self.queue = asyncio.Queue()

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = await self.pre_execute(params)

        try:
            # 创建流式任务
            asyncio.create_task(self._stream_task(params))
            return await self.post_execute({"success": True, "streaming": True})
        except Exception as e:
            self.status = "error"
            return {"success": False, "error": str(e)}

    async def _stream_task(self, params: Dict[str, Any]):
        """流式任务"""
        try:
            async for chunk in self._generate_stream(params):
                await self.queue.put(chunk)
            await self.queue.put(None)  # 结束标记
        except Exception as e:
            await self.queue.put({"error": str(e)})
            await self.queue.put(None)

    @abstractmethod
    async def _generate_stream(self, params: Dict[str, Any]):
        """生成流式数据"""
        pass

    async def read_stream(self):
        """读取流式数据"""
        while True:
            chunk = await self.queue.get()
            if chunk is None:
                break
            yield chunk


class ToolModule(ModuleBase):
    """工具类模块 - 提供工具能力"""

    def __init__(self, module_id: str, tools: List[Dict], config: Optional[Dict] = None):
        super().__init__(module_id, config)
        self.tools = {t["name"]: t for t in tools}

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("tool")
        if tool_name not in self.tools:
            return {"success": False, "error": f"工具 {tool_name} 不存在"}

        tool = self.tools[tool_name]
        tool_params = params.get("params", {})

        try:
            result = await self._call_tool(tool, tool_params)
            return await self.post_execute({"success": True, "result": result})
        except Exception as e:
            return {"success": False, "error": str(e)}

    @abstractmethod
    async def _call_tool(self, tool: Dict, params: Dict) -> Any:
        """调用工具"""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "tool",
            "tools": list(self.tools.keys())
        }


# 导出
__all__ = ["ModuleBase", "CompositeModule", "AsyncModule", "StreamingModule", "ToolModule"]
