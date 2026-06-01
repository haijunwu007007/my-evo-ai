"""AUTO-EVO-AI V0.1 — FileBrowser (55k⭐) 桥接路由"""
from fastapi import APIRouter
router = APIRouter()
import os, json, urllib.request
B = "/api/tools/filebrowser"

FB_URL = os.environ.get("FILEBROWSER_URL", "http://localhost:8083")
FB_USER = os.environ.get("FILEBROWSER_USER", "admin")
FB_PASS = os.environ.get("FILEBROWSER_PASS", "admin")

_SESSION = None

def _login():
    global _SESSION
    try:
        data = json.dumps({"username": FB_USER, "password": FB_PASS}).encode()
        req = urllib.request.Request(f"{FB_URL}/api/login", data=data, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        _SESSION = resp.headers.get("Set-Cookie", "")
        return True
    except Exception as e:
        _SESSION = None
        return False

def _req(method, path, data=None):
    global _SESSION
    if not _SESSION and not _login():
        return None, "FileBrowser not reachable"
    try:
        url = f"{FB_URL}/api{path}"
        headers = {"Cookie": _SESSION, "Content-Type": "application/json"} if _SESSION else {"Content-Type": "application/json"}
        r = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers, method=method)
        resp = urllib.request.urlopen(r, timeout=5)
        return json.loads(resp.read().decode()), None
    except Exception as e:
        return None, str(e)

@router.get(B)
async def status():
    ok = _login()
    return {"success": True, "available": ok, "url": FB_URL, "name": "FileBrowser (55k⭐) Web文件管理器"}

@router.get(B + "/resources")
async def resources(path: str = "/"):
    d, err = _req("GET", f"/resources{path}")
    if err:
        return {"success": False, "error": err}
    return {"success": True, "items": d}

@router.post(B + "/upload")
async def upload(path: str = "/"):
    return {"success": False, "error": "Use FileBrowser UI directly at: " + FB_URL}
