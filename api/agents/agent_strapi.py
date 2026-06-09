"""
Strapi Headless CMS - 通过Strapi API管理内容和媒体
"""
import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("STRAPI_API_URL", "") or "http://localhost:1337"
_API_KEY = os.environ.get("STRAPI_API_KEY", "") or os.environ.get("STRAPI_TOKEN", "")
_TIMEOUT = 15


def strapi_cms(**kwargs):
    """Strapi Headless CMS - 通过Strapi API管理内容和媒体
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 STRAPI_API_URL", "message": "未配置"}
        
        headers = {"Content-Type": "application/json"}
        if _API_KEY:
            headers["Authorization"] = f"Bearer {_API_KEY}"
        
        action = kwargs.pop("action", "status")
        params = kwargs.get("params", kwargs)
        
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_API_BASE}/api/{action}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "data": data, "message": f"{action}成功"}
    except Exception as e:
        return {"ok": False, "data": f"{action}失败: {e}", "message": str(e)}

def strapi_content(**kwargs):
    """Strapi Headless CMS - 通过Strapi API管理内容和媒体
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 STRAPI_API_URL", "message": "未配置"}
        
        headers = {"Content-Type": "application/json"}
        if _API_KEY:
            headers["Authorization"] = f"Bearer {_API_KEY}"
        
        action = kwargs.pop("action", "status")
        params = kwargs.get("params", kwargs)
        
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_API_BASE}/api/{action}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "data": data, "message": f"{action}成功"}
    except Exception as e:
        return {"ok": False, "data": f"{action}失败: {e}", "message": str(e)}

def strapi_media(**kwargs):
    """Strapi Headless CMS - 通过Strapi API管理内容和媒体
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 STRAPI_API_URL", "message": "未配置"}
        
        headers = {"Content-Type": "application/json"}
        if _API_KEY:
            headers["Authorization"] = f"Bearer {_API_KEY}"
        
        action = kwargs.pop("action", "status")
        params = kwargs.get("params", kwargs)
        
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_API_BASE}/api/{action}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "data": data, "message": f"{action}成功"}
    except Exception as e:
        return {"ok": False, "data": f"{action}失败: {e}", "message": str(e)}
