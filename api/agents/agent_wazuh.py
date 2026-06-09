"""
wazuh_siem - Wazuh安全监控 - 开源SIEM/XDR, 入侵检测+漏洞扫描
"""
import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("WAZUH_API_KEY_URL", "") or "https://localhost:55000"
_API_KEY = os.environ.get("WAZUH_API_KEY_KEY", "") or os.environ.get("WAZUH_API_KEY", "")
_TIMEOUT = 15

def wazuh_security(**kwargs):
    """Wazuh安全监控 - 通过Wazuh API管理安全事件
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 WAZUH_API_KEY_URL", "message": "未配置"}
        
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


def wazuh_security_helper(**kwargs):
    """Wazuh安全监控 - 通过Wazuh API管理安全事件 - 辅助操作"""
    return wazuh_security(**kwargs)
