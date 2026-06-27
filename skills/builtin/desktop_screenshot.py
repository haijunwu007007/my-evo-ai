"""桌面截图技能 — mss"""
from pathlib import Path

skill_def = {
    "name": "desktop-screenshot", "version": "1.0.0",
    "description": "桌面截图",
    "author": "AUTO-EVO-AI", "category": "桌面自动化", "icon": "🖥️",
    "tags": ["截图", "桌面", "屏幕"],
    "input_schema": {"type": "object", "properties": {"region": {"type": "string", "enum": ["full", "window"]}}},
    "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}}
}

OUT = Path(__file__).resolve().parent.parent.parent / "output" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

def execute(params, context=None):
    region = params.get("region", "full")
    import time
    name = f"screenshot_{int(time.time())}.png"
    fp = str(OUT / name)
    try:
        import mss
        with mss.mss() as sct:
            if region == "full":
                sct.shot(output=fp)
            else:
                mon = sct.monitors[1]
                sct.shot(mon, output=fp)
        return {"file_path": fp}
    except ImportError:
        try:
            import pyautogui
            im = pyautogui.screenshot()
            im.save(fp)
            return {"file_path": fp}
        except ImportError:
            return {"file_path": "", "error": "mss 和 pyautogui 均未安装"}
    except Exception as e:
        return {"file_path": "", "error": f"截图失败：{e}"}
