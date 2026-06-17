"""
AUTO-EVO-AI 工具引擎 — 87 个智能体工具
转发到 api/tools/ 子模块

===========================
工具清单见: api/tools/ 目录
===========================
"""
from api.tools import tool, exec_tool, list_tools, _tools, BASE

# 注册终极集成引擎 (图片/音频/转换/WebHook/沙箱/截图)
try:
    from api.hub.unified_toolchain import TOOLS as _UT
    _tools.update(_UT)
except Exception:
    pass

try:
    from api.hub.ultimate_integration import execute as _UE
    for _n, _f in [
        ("generate_image", lambda a, **k: _UE("generate_image", {**a, **k})),
        ("transcribe_audio", lambda a, **k: _UE("transcribe_audio", {**a, **k})),
        ("convert_file", lambda a, **k: _UE("convert_file", {**a, **k})),
        ("send_webhook", lambda a, **k: _UE("send_webhook", {**a, **k})),
        ("run_code_sandbox", lambda a, **k: _UE("run_code_sandbox", {**a, **k})),
        ("capture_analyze", lambda a, **k: _UE("capture_and_analyze", {**a, **k})),
    ]:
        _f._meta = {"name": _n, "category": "终极集成", "description": "图片生成/音频转录/格式转换/WebHook/沙箱/截图"}
        _tools[_n] = _f
except Exception:
    pass

__all__ = ["tool", "exec_tool", "list_tools", "_tools", "BASE"]
