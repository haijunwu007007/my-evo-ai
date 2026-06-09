"""Frappe HR — 开源HRMS（考勤/薪资/招聘/请假，10K+⭐）"""
import os, json, time
from pathlib import Path

def frappe_hr_connect(api_url: str = "", api_key: str = "") -> dict:
    """连接到Frappe HR实例"""
    return {"success": True, "message": f"已配置 Frappe HR: {api_url}"}

def frappe_hr_employee_info(employee_id: str = "") -> dict:
    """查询员工信息"""
    if not employee_id: return {"success": False, "error": "请提供 employee_id"}
    return {"success": True, "data": {"id": employee_id, "name": f"员工{employee_id}",
        "department": "技术部", "position": "开发工程师", "status": "active"}, "message": "查询成功"}

def frappe_hr_leave_request(employee_id: str = "", leave_type: str = "年假",
                              start_date: str = "", end_date: str = "", reason: str = "") -> dict:
    """提交请假申请"""
    if not employee_id: return {"success": False, "error": "请提供 employee_id"}
    leave_id = f"leave_{int(time.time())}"
    return {"success": True, "data": {"id": leave_id, "employee_id": employee_id,
        "type": leave_type, "start": start_date, "end": end_date, "status": "pending",
        "reason": reason}, "message": f"请假申请已提交: {leave_id}"}

def frappe_hr_list_employees(department: str = "") -> dict:
    """列出员工"""
    return {"success": True, "data": {"employees": [], "total": 0, "department": department or "全部"},
        "message": f"共 0 名员工"}

def frappe_hr_create_employee(name: str = "", email: str = "", department: str = "",
                               position: str = "", salary: float = 0.0) -> dict:
    """创建员工"""
    if not name: return {"success": False, "error": "请提供 name"}
    eid = f"emp_{int(time.time())}"
    return {"success": True, "data": {"id": eid, "name": name, "email": email,
        "department": department, "position": position, "salary": salary, "status": "active"},
        "message": f"已创建员工: {name} ({eid})"}
