"""应用启动技能 — 跨平台打开系统应用"""
import subprocess, sys, os

skill_def = {
    "name": "app-opener", "version": "1.0.0",
    "description": "打开系统应用（计算器/记事本/浏览器）",
    "author": "AUTO-EVO-AI", "category": "桌面自动化", "icon": "🖥️",
    "tags": ["打开", "计算器", "记事本", "浏览器"],
    "input_schema": {"type": "object", "properties": {"app": {"type": "string", "enum": ["calculator", "notepad", "browser", "explorer"]}}},
    "output_schema": {"type": "object", "properties": {"status": {"type": "string"}}}
}

_APPS = {
    "calculator": {"win32": "calc", "linux": "gnome-calculator", "darwin": "open -a Calculator"},
    "notepad":   {"win32": "notepad", "linux": "gedit", "darwin": "open -a TextEdit"},
    "browser":   {"win32": "start", "linux": "xdg-open", "darwin": "open"},
    "explorer":  {"win32": "explorer", "linux": "nautilus", "darwin": "open"},
}

def execute(params, context=None):
    app = params.get("app", "")
    if not app:
        return {"status": "error"}
    plat = sys.platform
    cmd_tmpl = _APPS.get(app, {}).get(plat, "echo unsupported")
    try:
        if plat == "win32":
            os.system(cmd_tmpl)
        else:
            subprocess.Popen(cmd_tmpl.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": f"{app} 已启动"}
    except Exception as e:
        return {"status": f"启动失败：{e}"}
