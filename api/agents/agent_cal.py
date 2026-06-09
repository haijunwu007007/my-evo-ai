"""
cal_schedule - Cal.com日程调度 - 开源Calendly, 自动安排会议/预订时间
"""
import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("CAL_API_KEY_URL", "") or "https://api.cal.com"
_API_KEY = os.environ.get("CAL_API_KEY_KEY", "") or os.environ.get("CAL_API_KEY", "")
_TIMEOUT = 15

def cal_schedule(**kwargs):
    """Cal.com日程调度 - 通过Cal.com API管理日程
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {"ok": bool, "data": ..., "message": ...}
    """
    try:
        if not _API_BASE:
            return {"ok": False, "data": "请设置环境变量 CAL_API_KEY_URL", "message": "未配置"}
        
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


def cal_schedule_helper(**kwargs):
    """Cal.com日程调度 - 通过Cal.com API管理日程 - 辅助操作"""
    return cal_schedule(**kwargs)
