"""
AUTO-EVO-AI 工具引擎 — 87 个智能体工具
转发到 api/tools/ 子模块

===========================
工具清单见: api/tools/ 目录
===========================
"""
from api.tools import tool, exec_tool, list_tools, _tools, BASE

# 注册统一工具链 (8大产业, 13个核心能力)
try:
    from api.hub.unified_toolchain import TOOLS as _UT
    _tools.update(_UT)
except Exception:
    pass

__all__ = ["tool", "exec_tool", "list_tools", "_tools", "BASE"]
