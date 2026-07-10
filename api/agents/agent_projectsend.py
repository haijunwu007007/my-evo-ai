"""
projectsend_files - ProjectSend安全文件共享 - 客户端上传/下载/权限
"""
import logging
logger = logging.getLogger("evo.agent_projectsend")

import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("PROJECTSEND_API_KEY_URL", "") or ""
_API_KEY = os.environ.get("PROJECTSEND_API_KEY_KEY", "") or os.environ.get("PROJECTSEND_API_KEY", "")
_TIMEOUT = 15

def projectsend_files(**kwargs):
    """ProjectSend文件共享 - 通过ProjectSend API管理文件共享
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 PROJECTSEND_API_KEY_URL", "message": "未配置"}
        
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


def projectsend_files_helper(**kwargs):
    """ProjectSend文件共享 - 通过ProjectSend API管理文件共享 - 辅助操作"""
    return projectsend_files(**kwargs)
