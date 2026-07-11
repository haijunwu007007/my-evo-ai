from __future__ import annotations

# -*- coding: utf-8 -*-

"""桌面Agent v2 — OpenHuman 风格桌面视觉操作

屏幕截取 → 视觉理解 → UI元素检测 → 鼠标/键盘操作 → 记忆

"""

import os, json, time, subprocess, base64, io, re

from typing import Optional

from pathlib import Path



# ── 可选依赖 ──

_HAS_MSS = False

_HAS_PYAG = False

_HAS_PIL = False

_HAS_OCR = False

_OCR_MODE = None  # 'tesseract' or 'easyocr'



try: import mss; _HAS_MSS = True

except: pass

try: import pyautogui; _HAS_PYAG = True

except: pass

try:

    from PIL import Image, ImageGrab

    _HAS_PIL = True

except: pass

try:

    import pytesseract

    _OCR_MODE = 'tesseract'

    _HAS_OCR = True

except: pass

# easyocr: 惰性加载（不阻塞启动）

_OCR_READER = None





class DesktopAgent:

    """OpenHuman 风格桌面视觉操作 Agent"""



    def __init__(self):

        self._allowed_cmds = ["ls","dir","pwd","whoami","echo","cat","type","head","tail","wc","date"]

        self._last_screenshot = None

        self._last_ocr = None

        self._screen_size = None



    # ── 能力描述 ──

    def get_capabilities(self) -> dict:

        return {

            "screen_capture": _HAS_MSS or _HAS_PIL,

            "ocr_text": _HAS_OCR,

            "mouse_control": _HAS_PYAG,

            "keyboard_control": _HAS_PYAG,

            "ui_element_detect": _HAS_OCR,

            "window_manage": True,  # via subprocess

            "clipboard": True,

            "file_ops": True,

            "vision_understand": True,  # uses existing image_understand module

        }



    # ════════════════════════════════════════════

    # 1. 屏幕截取

    # ════════════════════════════════════════════



    def screenshot(self, region: str = "") -> dict:

        """

        截图当前屏幕

        region: ""=全屏, "window"=活动窗口, "区域x,y,w,h"(如"100,100,800,600")

        返回: {success, b64(png), w, h, path, format}

        """

        img = None

        try:

            if _HAS_MSS:

                with mss.mss() as sct:

                    if region and ',' in region:

                        parts = [int(x.strip()) for x in region.split(',')]

                        mon = {"top": parts[1],"left": parts[0],"width": parts[2],"height": parts[3]}

                        img = sct.grab(mon)

                    else:

                        img = sct.grab(sct.monitors[1])  # primary monitor

                    from PIL import Image as PImage

                    img_pil = PImage.frombytes("RGB", img.size, img.rgb)

                    self._screen_size = img.size

            elif _HAS_PIL:

                img_pil = ImageGrab.grab()

                self._screen_size = img_pil.size

                if region and ',' in region:

                    parts = [int(x.strip()) for x in region.split(',')]

                    img_pil = img_pil.crop((parts[0], parts[1], parts[0]+parts[2], parts[1]+parts[3]))

            else:

                # fallback: use a simple command line tool

                result = subprocess.run(

                    ["import","-window","root","/tmp/evo_ss.png"] if os.name != 'nt' else [],

                    capture_output=True, timeout=10

                )

                if os.path.exists("/tmp/evo_ss.png"):

                    from PIL import Image as PImage

                    img_pil = PImage.open("/tmp/evo_ss.png")

                else:

                    return {"success": False, "error": "没有可用的截图库，请安装: pip install mss pillow"}



            # 保存

            ts = int(time.time())

            out_dir = Path(os.getenv('EVO_OUTPUT_DIR', '/tmp/evo_screenshots'))

            out_dir.mkdir(parents=True, exist_ok=True)

            path = str(out_dir / f'screen_{ts}.png')



            img_pil.save(path)

            buf = io.BytesIO()

            img_pil.save(buf, format='PNG')

            b64 = base64.b64encode(buf.getvalue()).decode()



            self._last_screenshot = {'path': path, 'w': img_pil.width, 'h': img_pil.height, 'b64': b64}



            return {

                "success": True,

                "path": path,

                "width": img_pil.width,

                "height": img_pil.height,

                "b64": b64[:100] + "...",  # 前端不显示完整 base64

                "format": "png",

                "size_kb": round(len(b64)*3/4/1024, 1)

            }

        except Exception as e:

            return {"success": False, "error": f"截图失败: {str(e)}"}



    # ════════════════════════════════════════════

    # 2. OCR — 屏幕文字识别

    # ════════════════════════════════════════════



    def ocr_screen(self, region: str = "", lang: str = "ch_sim+en") -> dict:

        """识别屏幕上的文字"""

        ss = self.screenshot(region)

        if not ss.get("success"):

            return ss



        if not _HAS_OCR:

            return {"success": False, "error": "没有 OCR 引擎，请安装: pip install pytesseract easyocr"}



        try:

            from PIL import Image as PImage

            img = PImage.open(ss["path"])



            if _OCR_MODE == 'tesseract':

                try:

                    text = pytesseract.image_to_string(img, lang='chi_sim+eng')

                except:

                    text = pytesseract.image_to_string(img)

                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

                elements = []

                for i in range(len(data['text'])):

                    if data['text'][i].strip():

                        elements.append({

                            "text": data['text'][i],

                            "x": data['left'][i], "y": data['top'][i],

                            "w": data['width'][i], "h": data['height'][i],

                            "confidence": data['conf'][i]

                        })

            else:

                # easyocr (惰性加载)

                global _OCR_READER, _OCR_MODE, _HAS_OCR

                if _OCR_READER is None:

                    try:

                        import easyocr

                        _OCR_READER = easyocr.Reader(['ch_sim','en'], gpu=False)

                        _OCR_MODE = 'easyocr'

                        _HAS_OCR = True

                    except Exception as e:

                        return {"success": False, "error": f"easyocr 加载失败: {str(e)}"}

                try:

                    result = _OCR_READER.readtext(img)

                except Exception as e:

                    return {"success": False, "error": f"OCR 识别失败: {str(e)}"}

                text = '\n'.join([r[1] for r in result])

                elements = [{

                    "text": r[1],

                    "confidence": round(r[2], 2),

                    "bbox": [[int(x), int(y)] for x, y in r[0]]

                } for r in result]



            self._last_ocr = {

                "text": text,

                "elements": elements,

                "count": len(elements)

            }



            return {

                "success": True,

                "text": text[:2000],

                "elements": elements[:100],

                "count": len(elements),

                "ocr_engine": _OCR_MODE

            }

        except Exception as e:

            return {"success": False, "error": f"OCR 失败: {str(e)}"}



    # ════════════════════════════════════════════

    # 3. UI 元素检测

    # ════════════════════════════════════════════



    def find_ui_element(self, target: str, by: str = "text") -> dict:

        """

        在屏幕上找到 UI 元素

        by: "text"(文字匹配), "button"(按钮), "input"(输入框), "icon"(图标)

        """

        ocr = self.ocr_screen()

        if not ocr.get("success"):

            return ocr



        matches = []

        for el in ocr.get("elements", []):

            text = el.get("text", "")

            if by == "text" and target.lower() in text.lower():

                matches.append(el)

            elif by == "button" and any(kw in text.lower() for kw in ["确定","取消","提交","保存","确认","ok","save","submit","confirm"]):

                matches.append(el)

            elif by == "input" and len(text.strip()) < 3:

                # short text may be input labels

                matches.append(el)



        if matches:

            # return the best match (first or highest confidence)

            best = matches[0]

            center_x = best.get('x', 0) + best.get('w', 0)//2 if 'w' in best else (best['bbox'][0][0] + best['bbox'][2][0])//2

            center_y = best.get('y', 0) + best.get('h', 0)//2 if 'h' in best else (best['bbox'][0][1] + best['bbox'][2][1])//2

            return {

                "success": True,

                "matches": len(matches),

                "element": best,

                "click_point": {"x": center_x, "y": center_y},

                "target": target

            }

        return {"success": False, "error": f"未找到 '{target}'", "target": target, "by": by}



    # ════════════════════════════════════════════

    # 4. 鼠标操作

    # ════════════════════════════════════════════



    def mouse_click(self, x: int = None, y: int = None, target: str = None, button: str = "left") -> dict:

        """点击鼠标，支持坐标或查找目标"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui: pip install pyautogui"}



        try:

            if target:

                found = self.find_ui_element(target)

                if not found.get("success"):

                    return found

                pt = found.get("click_point", {})

                x, y = pt.get("x"), pt.get("y")



            if x is None or y is None:

                # click current position

                pyautogui.click(button=button)

            else:

                pyautogui.click(x, y, button=button)



            return {"success": True, "action": "click", "x": x, "y": y, "button": button}

        except Exception as e:

            return {"success": False, "error": f"鼠标点击失败: {str(e)}"}



    def mouse_move(self, x: int, y: int, duration: float = 0.3) -> dict:

        """移动鼠标"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.moveTo(x, y, duration=duration)

            return {"success": True, "x": x, "y": y}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def mouse_drag(self, x1: int, y1: int, x2: int, y2: int) -> dict:

        """拖拽"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)

            return {"success": True}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def scroll(self, clicks: int = -3) -> dict:

        """滚动，负数=向下"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.scroll(clicks)

            return {"success": True, "clicks": clicks}

        except Exception as e:

            return {"success": False, "error": str(e)}



    # ════════════════════════════════════════════

    # 5. 键盘操作

    # ════════════════════════════════════════════



    def keyboard_type(self, text: str, interval: float = 0.05) -> dict:

        """键盘输入文本"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.typewrite(text, interval=interval)

            return {"success": True, "chars": len(text)}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def keyboard_hotkey(self, keys: list) -> dict:

        """快捷键: keyboard_hotkey(['ctrl','c'])"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.hotkey(*keys)

            return {"success": True, "keys": keys}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def keyboard_press(self, key: str) -> dict:

        """按单个键: keyboard_press('enter')"""

        if not _HAS_PYAG:

            return {"success": False, "error": "需要 pyautogui"}

        try:

            pyautogui.press(key)

            return {"success": True, "key": key}

        except Exception as e:

            return {"success": False, "error": str(e)}



    # ════════════════════════════════════════════

    # 6. 窗口管理

    # ════════════════════════════════════════════



    def list_windows(self) -> dict:

        """列出所有窗口（仅 Linux/macOS）"""

        try:

            if os.name == 'nt':

                import ctypes

                result = []

                # Windows: use EnumWindows

                def enum_callback(hwnd, lparam):

                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)

                    if length > 0:

                        buf = ctypes.create_unicode_buffer(length + 1)

                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)

                        rect = ctypes.wintypes.RECT()

                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))

                        result.append({

                            "hwnd": hwnd,

                            "title": buf.value,

                            "x": rect.left, "y": rect.top,

                            "w": rect.right - rect.left, "h": rect.bottom - rect.top

                        })

                ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(enum_callback), 0)

                return {"success": True, "windows": result[:50], "count": len(result)}

            else:

                r = subprocess.run(["wmctrl","-l"], capture_output=True, text=True, timeout=5)

                lines = r.stdout.strip().split('\n') if r.stdout.strip() else []

                wins = []

                for line in lines:

                    parts = line.split(None, 3)

                    if len(parts) >= 4:

                        wins.append({"id": parts[0], "desktop": parts[1], "pid": parts[2], "title": parts[3]})

                return {"success": True, "windows": wins[:50], "count": len(wins)}

        except Exception as e:

            return {"success": False, "error": str(e), "windows": []}



    def focus_window(self, title: str) -> dict:

        """聚焦窗口"""

        try:

            if os.name == 'nt':

                import ctypes

                wins = self.list_windows()

                for w in wins.get("windows", []):

                    if title.lower() in w.get("title", "").lower():

                        ctypes.windll.user32.SetForegroundWindow(w["hwnd"])

                        return {"success": True, "window": w["title"]}

                return {"success": False, "error": f"未找到包含 '{title}' 的窗口"}

            else:

                r = subprocess.run(["wmctrl","-a", title], capture_output=True, text=True, timeout=5)

                return {"success": r.returncode == 0, "output": r.stdout}

        except Exception as e:

            return {"success": False, "error": str(e)}



    # ════════════════════════════════════════════

    # 7. 剪贴板

    # ════════════════════════════════════════════



    def clipboard_get(self) -> dict:

        """读取剪贴板"""

        try:

            import pyperclip

            text = pyperclip.paste()

            return {"success": True, "text": text[:2000], "length": len(text)}

        except:

            try:

                r = subprocess.run(["xclip","-o","-selection","clipboard"], capture_output=True, text=True, timeout=5)

                return {"success": True, "text": r.stdout[:2000], "length": len(r.stdout)}

            except Exception as e:

                return {"success": False, "error": f"需要 pyperclip: pip install pyperclip, {e}"}



    def clipboard_set(self, text: str) -> dict:

        """写入剪贴板"""

        try:

            import pyperclip

            pyperclip.copy(text)

            return {"success": True, "length": len(text)}

        except:

            try:

                p = subprocess.Popen(["xclip","-selection","clipboard"], stdin=subprocess.PIPE, text=True)

                p.communicate(text)

                return {"success": True}

            except Exception as e:

                return {"success": False, "error": str(e)}



    # ════════════════════════════════════════════

    # 8. 视觉理解（集成 image_understand）

    # ════════════════════════════════════════════



    def describe_screen(self, prompt: str = "描述这个屏幕上有什么") -> dict:

        """使用视觉 AI 模型理解屏幕内容"""

        ss = self.screenshot()

        if not ss.get("success"):

            return ss



        try:

            # 调用已有的 image_understand 模块

            from modules.image_understand import ImageUnderstand

            iu = ImageUnderstand()

            result = iu.understand(ss["path"], prompt)

            return result

        except ImportError:

            return {"success": False, "error": "image_understand 模块不可用", "note": "可以先用 ocr_screen 识别文字"}

        except Exception as e:

            return {"success": False, "error": str(e)}



    # ════════════════════════════════════════════

    # 9. 高级操作链

    # ════════════════════════════════════════════



    def automate(self, steps: list) -> dict:

        """

        执行一系列操作步骤，类似于 OpenHuman 的任务链

        steps: [{action: "click", target: "确定"}, {action: "type", text: "hello"}]

        支持的 action: click, type, hotkey, scroll, screenshot, ocr, wait

        """

        results = []

        for i, step in enumerate(steps):

            action = step.get("action", "")

            try:

                if action == "click":

                    r = self.mouse_click(target=step.get("target"), x=step.get("x"), y=step.get("y"))

                elif action == "type":

                    r = self.keyboard_type(step.get("text", ""))

                elif action == "hotkey":

                    r = self.keyboard_hotkey(step.get("keys", []))

                elif action == "scroll":

                    r = self.scroll(step.get("clicks", -3))

                elif action == "screenshot":

                    r = self.screenshot()

                elif action == "ocr":

                    r = self.ocr_screen()

                elif action == "wait":

                    time.sleep(step.get("seconds", 1))

                    r = {"success": True, "waited": step.get("seconds", 1)}

                elif action == "move":

                    r = self.mouse_move(step.get("x", 0), step.get("y", 0))

                else:

                    r = {"success": False, "error": f"未知动作: {action}"}

            except Exception as e:

                r = {"success": False, "error": str(e), "step": i}

            results.append({"step": i, "action": action, "result": r})

            if not r.get("success") and step.get("critical", False):

                break

        return {"success": True, "steps": len(steps), "completed": i+1, "results": results}



    # ════════════════════════════════════════════

    # 10. 原有功能保留

    # ════════════════════════════════════════════



    def execute(self, cmd: str, cwd: str = "") -> dict:

        """执行安全命令"""

        base = cmd.strip().split()[0].lower() if cmd.strip() else ""

        if base not in self._allowed_cmds:

            return {"success": False, "error": f"命令 '{base}' 不在白名单", "allowed": self._allowed_cmds}

        try:

            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=cwd or os.getcwd())

            return {"success": True, "stdout": r.stdout[:500], "stderr": r.stderr[:200], "code": r.returncode}

        except subprocess.TimeoutExpired:

            return {"success": False, "error": "超时"}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def read_file(self, path: str) -> dict:

        try:

            c = open(path, "r", encoding="utf-8", errors="replace").read(5000)

            return {"success": True, "content": c, "size": len(c)}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def write_file(self, path: str, content: str) -> dict:

        try:

            with open(path, "w", encoding="utf-8") as f: f.write(content)

            return {"success": True, "path": path, "bytes": len(content)}

        except Exception as e:

            return {"success": False, "error": str(e)}



    def list_dir(self, path: str = ".") -> dict:

        try:

            items = os.listdir(path)

            return {"success": True, "path": path, "items": items[:50], "count": len(items)}

        except Exception as e:

            return {"success": False, "error": str(e)}





# ── EnterpriseModule 兼容 ──

try:

    from modules._base.enterprise_module import EnterpriseModule

    class DesktopAgentEnterprise(DesktopAgent, EnterpriseModule):

        pass

except:

    pass

