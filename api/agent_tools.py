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

# ── Java/K8s 部署工具 ──
try:
    from api.hub.java_build_deploy import auto_build_java, detect_java_type
    _tools["java_build"] = lambda a, **k: auto_build_java(a.get("path","."))
    _tools["java_build"]._meta = {"name":"java_build","category":"部署","description":"Java自动检测构建部署"}
except Exception:
    pass

try:
    from api.hub.k8s_fallback import deploy_k8s_or_fallback, check_k8s
    _tools["k8s_deploy"] = lambda a, **k: deploy_k8s_or_fallback(a.get("config",""), a.get("name","evo-app"))
    _tools["k8s_deploy"]._meta = {"name":"k8s_deploy","category":"部署","description":"K8s部署+自动降级docker-compose"}
    _tools["k8s_check"] = lambda a, **k: check_k8s()
    _tools["k8s_check"]._meta = {"name":"k8s_check","category":"部署","description":"检查K8s集群状态"}
except Exception:
    pass

# ── BrowserAct 反爬浏览器自动化 ──
try:
    from api.agent_tools_browseract import get_browseract_tools
    for _bt in get_browseract_tools():
        _tools[_bt["name"]] = _bt["fn"]
        _tools[_bt["name"]]._meta = {"name": _bt["name"], "category": "浏览器", "description": _bt["desc"]}
except Exception:
    pass

print(f"  [agent_tools] +5 new tools (browseract_extract,browseract_browse,codemem_index,codemem_query,java_build)")

__all__ = ["tool", "exec_tool", "list_tools", "_tools", "BASE"]
