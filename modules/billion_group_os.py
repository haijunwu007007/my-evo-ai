"""
AUTO-EVO-AI V0.1 — 亿群OS企业管理模块
Grade: A (生产级) | Category: 企业管理
职责：企业组织架构管理、部门层级、员工档案、考勤、绩效评估
"""

__module_meta__ = {
    "id": "billion-group-os",
    "name": "Billion Group Os",
    "version": "1.0.0",
    "group": "system",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "prefix", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "billion"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 亿群OS企业管理模块 Grade: A (生产级) | Category: 企业管理",
}

import os
import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
logger = logging.getLogger("billion_group_os")

class EmployeeStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    RESIGNED = "resigned"

class PerformanceLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"

@dataclass
class Department:
    dept_id: str
    name: str
    parent_id: str = ""
    manager_id: str = ""
    budget: float = 0.0
    headcount_limit: int = 0
    created_at: str = ""

@dataclass
class Employee:
    emp_id: str
    name: str
    dept_id: str
    position: str = ""
    email: str = ""
    phone: str = ""
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    join_date: str = ""
    salary_grade: int = 1
    skills: List[str] = field(default_factory=list)

@dataclass
class AttendanceRecord:
    record_id: str
    emp_id: str
    date: str
    check_in: str = ""
    check_out: str = ""
    hours: float = 0.0
    status: str = "normal"

@dataclass
class PerformanceReview:
    review_id: str
    emp_id: str
    period: str
    score: float = 0.0
    level: PerformanceLevel = PerformanceLevel.AVERAGE
    goals: List[str] = field(default_factory=list)
    comments: str = ""
    reviewer_id: str = ""

class BillionGroupOSManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """企业管理管理器 - 生产级实现"""

    MODULE_ID = "billion_group_os"
    MODULE_NAME = "亿群OS企业管理"
    VERSION = "V0.1"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._depts: Dict[str, Department] = {}
        self._employees: Dict[str, Employee] = {}
        self._attendance: Dict[str, List[AttendanceRecord]] = defaultdict(list)
        self._reviews: Dict[str, List[PerformanceReview]] = defaultdict(list)
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        raw = f"{prefix}_{self._counter}_{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    def initialize(self) -> bool:
        try:
            self._load_initial_data()
            logger.info(f"亿群OS初始化完成，部门: {len(self._depts)}，员工: {len(self._employees)}")
            return True
        except Exception as e:
            logger.error(f"亿群OS初始化失败: {e}")
            return False

    def _load_initial_data(self):
        """加载初始组织架构"""
        # 部门
        depts = [
            ("dept_ceo", "总裁办", "", "", 10000000, 5),
            ("dept_tech", "技术中心", "dept_ceo", "", 5000000, 100),
            ("dept_hr", "人力资源", "dept_ceo", "", 2000000, 30),
            ("dept_finance", "财务部", "dept_ceo", "", 1500000, 20),
            ("dept_frontend", "前端组", "dept_tech", "", 1000000, 30),
            ("dept_backend", "后端组", "dept_tech", "", 1500000, 40),
            ("dept_devops", "运维组", "dept_tech", "", 800000, 15),
        ]
        for d in depts:
            self._depts[d[0]] = Department(
                dept_id=d[0],
                name=d[1],
                parent_id=d[2],
                manager_id=d[3],
                budget=d[4],
                headcount_limit=d[5],
                created_at=datetime.now().isoformat(),
            )
        # 员工
        emps = [
            ("emp_001", "张总", "dept_ceo", "CEO", "zhang@bgos.com", "13800000001", 10, ["管理", "战略"]),
            ("emp_002", "李工", "dept_tech", "CTO", "li@bgos.com", "13800000002", 9, ["架构", "管理"]),
            ("emp_003", "王工", "dept_frontend", "前端主管", "wang@bgos.com", "13800000003", 7, ["React", "Vue"]),
            ("emp_004", "赵工", "dept_backend", "后端主管", "zhao@bgos.com", "13800000004", 7, ["Python", "Go"]),
            ("emp_005", "钱工", "dept_devops", "运维工程师", "qian@bgos.com", "13800000005", 6, ["K8s", "Docker"]),
            ("emp_006", "孙姐", "dept_hr", "HR总监", "sun@bgos.com", "13800000006", 8, ["招聘", "培训"]),
        ]
        for e in emps:
            self._employees[e[0]] = Employee(
                emp_id=e[0],
                name=e[1],
                dept_id=e[2],
                position=e[3],
                email=e[4],
                phone=e[5],
                salary_grade=e[6],
                skills=e[7],
                join_date="2024-01-15",
            )

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("billion_group_os_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        actions = {
            "add_dept": self._exec_add_dept,
            "add_employee": self._exec_add_employee,
            "update_employee": self._exec_update_employee,
            "get_org_tree": self._exec_get_org_tree,
            "get_dept_info": self._exec_get_dept_info,
            "get_employee": self._exec_get_employee,
            "list_employees": self._exec_list_employees,
            "record_attendance": self._exec_record_attendance,
            "get_attendance": self._exec_get_attendance,
            "submit_review": self._exec_submit_review,
            "get_reviews": self._exec_get_reviews,
            "get_stats": self._exec_get_stats,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "error": f"未知操作: {action}"}
        return handler(params)
        return {"status": "healthy", "module": "billion_group_os"}

    def _exec_add_dept(self, p: Dict) -> Dict:
        did = self._next_id("dept")
        self._depts[did] = Department(
            dept_id=did,
            name=p["name"],
            parent_id=p.get("parent_id", ""),
            manager_id=p.get("manager_id", ""),
            budget=p.get("budget", 0),
            headcount_limit=p.get("headcount_limit", 0),
            created_at=datetime.now().isoformat(),
        )
        return {"success": True, "result": {"dept_id": did, "name": p["name"]}}

    def _exec_add_employee(self, p: Dict) -> Dict:
        eid = self._next_id("emp")
        self._employees[eid] = Employee(
            emp_id=eid,
            name=p["name"],
            dept_id=p.get("dept_id", ""),
            position=p.get("position", ""),
            email=p.get("email", ""),
            phone=p.get("phone", ""),
            salary_grade=p.get("salary_grade", 1),
            skills=p.get("skills", []),
            join_date=datetime.now().strftime("%Y-%m-%d"),
        )
        return {"success": True, "result": {"emp_id": eid, "name": p["name"]}}

    def _exec_update_employee(self, p: Dict) -> Dict:
        eid = p["emp_id"]
        if eid not in self._employees:
            return {"success": False, "error": "员工不存在"}
        emp = self._employees[eid]
        if "position" in p:
            emp.position = p["position"]
        if "dept_id" in p:
            emp.dept_id = p["dept_id"]
        if "salary_grade" in p:
            emp.salary_grade = p["salary_grade"]
        if "status" in p:
            emp.status = EmployeeStatus(p["status"])
        if "skills" in p:
            emp.skills = p["skills"]
        return {"success": True, "result": {"emp_id": eid, "updated": True}}

    def _exec_get_org_tree(self, p: Dict) -> Dict:
        def build_tree(parent_id: str) -> List[Dict]:
            children = []
            for d in self._depts.values():
                if d.parent_id == parent_id:
                    dept_data = {
                        "dept_id": d.dept_id,
                        "name": d.name,
                        "manager": d.manager_id,
                        "budget": d.budget,
                        "headcount": sum(1 for e in self._employees.values() if e.dept_id == d.dept_id),
                        "headcount_limit": d.headcount_limit,
                        "children": build_tree(d.dept_id),
                    }
                    children.append(dept_data)
            return children

        tree = build_tree("")
        return {"success": True, "result": tree}

    def _exec_get_dept_info(self, p: Dict) -> Dict:
        did = p["dept_id"]
        if did not in self._depts:
            return {"success": False, "error": "部门不存在"}
        d = self._depts[did]
        members = [e for e in self._employees.values() if e.dept_id == did]
        return {
            "success": True,
            "result": {
                "dept_id": d.dept_id,
                "name": d.name,
                "parent": d.parent_id,
                "manager": d.manager_id,
                "budget": d.budget,
                "headcount_limit": d.headcount_limit,
                "current_headcount": len(members),
                "members": [{"emp_id": e.emp_id, "name": e.name, "position": e.position} for e in members],
            },
        }

    def _exec_get_employee(self, p: Dict) -> Dict:
        eid = p["emp_id"]
        if eid not in self._employees:
            return {"success": False, "error": "员工不存在"}
        e = self._employees[eid]
        dept_name = self._depts[e.dept_id].name if e.dept_id in self._depts else ""
        return {
            "success": True,
            "result": {
                "emp_id": e.emp_id,
                "name": e.name,
                "dept": dept_name,
                "position": e.position,
                "email": e.email,
                "phone": e.phone,
                "status": e.status.value,
                "salary_grade": e.salary_grade,
                "skills": e.skills,
                "join_date": e.join_date,
            },
        }

    def _exec_list_employees(self, p: Dict) -> Dict:
        dept = p.get("dept_id", "")
        status = p.get("status", "")
        results = []
        for e in self._employees.values():
            if dept and e.dept_id != dept:
                continue
            if status and e.status.value != status:
                continue
            results.append({"emp_id": e.emp_id, "name": e.name, "position": e.position, "status": e.status.value})
        return {"success": True, "result": {"total": len(results), "employees": results}}

    def _exec_record_attendance(self, p: Dict) -> Dict:
        eid = p["emp_id"]
        date = p.get("date", datetime.now().strftime("%Y-%m-%d"))
        check_in = p.get("check_in", "09:00")
        check_out = p.get("check_out", "18:00")
        # 计算工时
        h_in, m_in = map(int, check_in.split(":"))
        h_out, m_out = map(int, check_out.split(":"))
        hours = max(0, (h_out * 60 + m_out - h_in * 60 - m_in) / 60)
        record = AttendanceRecord(
            record_id=self._next_id("att"),
            emp_id=eid,
            date=date,
            check_in=check_in,
            check_out=check_out,
            hours=hours,
            status="normal" if 8 <= hours <= 10 else "abnormal",
        )
        self._attendance[eid].append(record)
        return {"success": True, "result": {"record_id": record.record_id, "hours": hours, "status": record.status}}

    def _exec_get_attendance(self, p: Dict) -> Dict:
        eid = p.get("emp_id", "")
        date_from = p.get("date_from", "")
        date_to = p.get("date_to", "")
        records = self._attendance.get(eid, [])
        if date_from:
            records = [r for r in records if r.date >= date_from]
        if date_to:
            records = [r for r in records if r.date <= date_to]
        total_hours = sum(r.hours for r in records)
        return {
            "success": True,
            "result": {
                "total_records": len(records),
                "total_hours": round(total_hours, 1),
                "records": [
                    {
                        "date": r.date,
                        "check_in": r.check_in,
                        "check_out": r.check_out,
                        "hours": r.hours,
                        "status": r.status,
                    }
                    for r in records[-30:]
                ],
            },
        }

    def _exec_submit_review(self, p: Dict) -> Dict:
        score = p.get("score", 0)
        if score >= 90:
            level = PerformanceLevel.EXCELLENT
        elif score >= 75:
            level = PerformanceLevel.GOOD
        elif score >= 60:
            level = PerformanceLevel.AVERAGE
        elif score >= 40:
            level = PerformanceLevel.NEEDS_IMPROVEMENT
        else:
            level = PerformanceLevel.POOR
        review = PerformanceReview(
            review_id=self._next_id("rev"),
            emp_id=p["emp_id"],
            period=p.get("period", "Q1-2026"),
            score=score,
            level=level,
            goals=p.get("goals", []),
            comments=p.get("comments", ""),
            reviewer_id=p.get("reviewer_id", ""),
        )
        self._reviews[p["emp_id"]].append(review)
        return {"success": True, "result": {"review_id": review.review_id, "level": level.value, "score": score}}

    def _exec_get_reviews(self, p: Dict) -> Dict:
        eid = p.get("emp_id", "")
        reviews = self._reviews.get(eid, [])
        return {
            "success": True,
            "result": {
                "total": len(reviews),
                "reviews": [
                    {
                        "review_id": r.review_id,
                        "period": r.period,
                        "score": r.score,
                        "level": r.level.value,
                        "comments": r.comments,
                    }
                    for r in reviews[-10:]
                ],
            },
        }

    def _exec_get_stats(self, p: Dict) -> Dict:
        active = sum(1 for e in self._employees.values() if e.status == EmployeeStatus.ACTIVE)
        total_salary = sum(e.salary_grade * 5000 for e in self._employees.values() if e.status == EmployeeStatus.ACTIVE)
        return {
            "success": True,
            "result": {
                "total_departments": len(self._depts),
                "total_employees": len(self._employees),
                "active_employees": active,
                "departments_with_headcount": {
                    d.name: sum(1 for e in self._employees.values() if e.dept_id == d.dept_id)
                    for d in self._depts.values()
                },
                "estimated_monthly_payroll": total_salary,
            },
        }

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy",
                "module_id": self.MODULE_ID,
                "departments": len(self._depts),
                "employees": len(self._employees),
                "attendance_records": sum(len(v) for v in self._attendance.values()),
                "reviews": sum(len(v) for v in self._reviews.values()),
                "last_check": datetime.now().isoformat(),
            }
        )
        return result

    def shutdown(self) -> bool:
        logger.info("亿群OS关闭")
        return True

    def _audit_log(self, event: str, actor: str, detail: Dict) -> None:
        """记录组织管理审计日志"""
        if hasattr(self, "_audit") and self._audit:
            self._audit.log(event, {"actor": actor, **detail, "ts": datetime.now().isoformat()})

    def audit_employee_change(self, emp_id: str, change_type: str, fields: Dict) -> None:
        """审计员工信息变更"""
        self._audit_log("employee_change", emp_id, {"change_type": change_type, "fields": fields})

    def audit_attendance_record(self, emp_id: str, status: str) -> None:
        """审计考勤记录"""
        self._audit_log("attendance_record", emp_id, {"status": status})

    def get_org_statistics(self) -> Dict[str, Any]:
        """获取组织统计概览"""
        dept_count = len(self._departments)
        emp_count = len(self._employees)
        attendance_count = len(self._attendance)
        review_count = len(self._performance_reviews)
        return {
            "departments": dept_count,
            "employees": emp_count,
            "attendance_records": attendance_count,
            "reviews": review_count,
            "avg_emp_per_dept": round(emp_count / max(dept_count, 1), 1),
        }

    def get_dept_headcount(self, dept_id: str) -> int:
        """获取部门人数"""
        return sum(1 for e in self._employees.values() if e.get("dept_id") == dept_id)

    def search_employees(self, keyword: str, field: str = "name") -> List[Dict]:
        """搜索员工"""
        results = []
        kw_lower = keyword.lower()
        for emp in self._employees.values():
            val = str(emp.get(field, ""))
            if kw_lower in val.lower():
                results.append(emp)
        return results

    def get_employee_timeline(self, emp_id: str) -> List[Dict]:
        """获取员工操作时间线"""
        timeline = []
        for att in self._attendance.values():
            if att.get("emp_id") == emp_id:
                timeline.append({"type": "attendance", "data": att})
        for rev in self._performance_reviews.values():
            if rev.get("emp_id") == emp_id:
                timeline.append({"type": "review", "data": rev})
        timeline.sort(key=lambda x: x["data"].get("date", ""), reverse=True)
        return timeline

    def get_org_depth(self, dept_id: str) -> int:
        """获取组织架构深度"""
        max_depth = 0

        def walk(did, depth):
            nonlocal max_depth
            children = [d for d in self._departments.values() if d.get("parent_id") == did]
            max_depth = max(max_depth, depth)
            for child in children:
                walk(child["dept_id"], depth + 1)

        walk(dept_id, 1)
        return max_depth

    def batch_update_dept(self, updates: List[Dict]) -> Dict:
        """批量更新部门信息"""
        success = 0
        failed = 0
        for upd in updates:
            did = upd.get("dept_id")
            if did in self._departments:
                self._departments[did].update(upd)
                success += 1
            else:
                failed += 1
        return {"success": success, "failed": failed, "total": len(updates)}

    def export_org_chart(self, format_type: str = "tree") -> Dict:
        """导出组织架构"""
        root_depts = [d for d in self._departments.values() if not d.get("parent_id")]

        def build_node(did):
            dept = self._departments.get(did, {})
            children_ids = [d["dept_id"] for d in self._departments.values() if d.get("parent_id") == did]
            return {
                "dept_id": did,
                "name": dept.get("name", ""),
                "headcount": self.get_dept_headcount(did),
                "children": [build_node(cid) for cid in children_ids],
            }

        tree = [build_node(d["dept_id"]) for d in root_depts]
        return {"format": format_type, "roots": tree, "total_depts": len(self._departments)}

    def get_performance_summary(self, dept_id: Optional[str] = None) -> Dict:
        """获取绩效汇总"""
        reviews = [
            r
            for r in self._performance_reviews.values()
            if not dept_id or self._employees.get(r.get("emp_id", ""), {}).get("dept_id") == dept_id
        ]
        if not reviews:
            return {"count": 0, "avg_score": 0}
        scores = [r.get("score", 0) for r in reviews]
        return {
            "count": len(reviews),
            "avg_score": round(sum(scores) / len(scores), 1),
            "max_score": max(scores),
            "min_score": min(scores),
        }

    def generate_organization_health_report(self) -> Dict[str, Any]:
        """生成组织健康报告：成员活跃度、部门效能、项目进度汇总"""
        members = self._members if hasattr(self, "_members") else {}
        departments = self._departments if hasattr(self, "_departments") else {}
        if not members:
            return {"total_members": 0}
        active_count = sum(1 for m in members.values() if isinstance(m, dict) and m.get("status") == "active")
        dept_stats = {}
        for did, dept in departments.items():
            if isinstance(dept, dict):
                dept_stats[did] = {
                    "name": dept.get("name", did),
                    "member_count": dept.get("member_count", 0),
                    "active_projects": dept.get("active_projects", 0),
                }
        return {
            "total_members": len(members),
            "active_members": active_count,
            "active_rate": round(active_count / max(len(members), 1), 3),
            "departments": len(department_stats) if hasattr(self, "_department_stats") else len(dept_stats),
            "department_summary": dept_stats,
        }

    def detect_member_bottlenecks(self) -> List[Dict[str, Any]]:
        """检测成员瓶颈：识别负载过高或参与度过低的成员"""
        members = self._members if hasattr(self, "_members") else {}
        tasks = self._tasks if hasattr(self, "_tasks") else {}
        if not members:
            return []
        member_task_count: Dict[str, int] = {}
        for tid, task in tasks.items():
            if isinstance(task, dict):
                assignee = task.get("assignee", "")
                if assignee:
                    member_task_count[assignee] = member_task_count.get(assignee, 0) + 1
        avg_load = sum(member_task_count.values()) / max(len(member_task_count), 1)
        bottlenecks = []
        for mid, count in member_task_count.items():
            if count > avg_load * 3:
                bottlenecks.append(
                    {
                        "member_id": mid,
                        "task_count": count,
                        "avg_load": round(avg_load, 1),
                        "overload_ratio": round(count / max(avg_load, 1), 1),
                        "type": "overloaded",
                    }
                )
        return sorted(bottlenecks, key=lambda x: -x["overload_ratio"])

module_class = BillionGroupOSManager
