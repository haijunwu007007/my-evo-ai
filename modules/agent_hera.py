"""
# Grade: A
AUTO-EVO-AI V0.1 — Agent Hera (人力资源管理引擎)
===================================================
企业级智能体，负责组织架构管理、员工档案、考勤追踪、绩效评估、薪酬计算与人才发展。
支持多部门矩阵管理、工时统计、晋升路径规划与离职预警。

继承: EnterpriseModule
"""

__module_meta__ = {
        "id": "agent-hera",
        "name": "Agent Hera",
        "version": "V0.1",
        "group": "agent",
        "inputs": [
            {
                "name": "emp_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "check_time",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "record_date",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "emp_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "check_time_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "record_date_2",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "event",
                "config": {
                    "on": "agent_hera.task.request"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "engine",
            "multi-agent",
            "agent"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 — Agent Hera (人力资源管理引擎) ==================================================="
    }

import time
import json
import hashlib
import logging
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result, HealthReport, ModuleStats
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("agent.hera")

class EmployeeStatus(Enum):
    ACTIVE = "active"
    PROBATION = "probation"
    ON_LEAVE = "on_leave"
    RESIGNED = "resigned"
    TERMINATED = "terminated"

class PerformanceRating(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    NEEDS_IMPROVEMENT = "needs_improvement"
    UNSATISFACTORY = "unsatisfactory"

@dataclass
class Department:
    dept_id: str = ""
    name: str = ""
    parent_id: Optional[str] = None
    head_id: Optional[str] = None
    budget: float = 0.0
    headcount_limit: int = 0
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "dept_id": self.dept_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "head_id": self.head_id,
            "budget": self.budget,
            "headcount_limit": self.headcount_limit,
            "description": self.description,
        }

@dataclass
class Employee:
    emp_id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    dept_id: str = ""
    position: str = ""
    level: str = ""
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    hire_date: str = ""
    probation_end: str = ""
    salary_base: float = 0.0
    salary_bonus: float = 0.0
    skills: List[str] = field(default_factory=list)
    manager_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def total_salary(self) -> float:
        return self.salary_base + self.salary_bonus

    @property
    def tenure_days(self) -> int:
        if not self.hire_date:
            return 0
        try:
            hd = datetime.strptime(self.hire_date, "%Y-%m-%d").date()
            return (date.today() - hd).days
        except Exception:
            return 0

    def to_dict(self) -> Dict:
        return {
            "emp_id": self.emp_id,
            "name": self.name,
            "email": self.email,
            "dept_id": self.dept_id,
            "position": self.position,
            "level": self.level,
            "status": self.status.value,
            "hire_date": self.hire_date,
            "salary_base": self.salary_base,
            "salary_bonus": self.salary_bonus,
            "total_salary": self.total_salary,
            "skills": self.skills,
            "manager_id": self.manager_id,
            "tenure_days": self.tenure_days,
        }

@dataclass
class AttendanceRecord:
    record_id: str = ""
    emp_id: str = ""
    date: str = ""
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    work_hours: float = 0.0
    overtime_hours: float = 0.0
    status: str = "normal"
    remark: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "emp_id": self.emp_id,
            "date": self.date,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "work_hours": self.work_hours,
            "overtime_hours": self.overtime_hours,
            "status": self.status,
        }

@dataclass
class PerformanceReview:
    review_id: str = ""
    emp_id: str = ""
    period: str = ""
    rating: PerformanceRating = PerformanceRating.AVERAGE
    score: float = 0.0
    goals_completed: int = 0
    goals_total: int = 0
    reviewer_id: str = ""
    feedback: str = ""
    promotion_recommendation: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "review_id": self.review_id,
            "emp_id": self.emp_id,
            "period": self.period,
            "rating": self.rating.value,
            "score": self.score,
            "goals_completed": self.goals_completed,
            "goals_total": self.goals_total,
            "reviewer_id": self.reviewer_id,
            "feedback": self.feedback,
            "promotion_recommendation": self.promotion_recommendation,
        }

# ============================================================
# 考勤引擎
# ============================================================

class AttendanceEngine(object):
    """考勤计算引擎 — 标准工时/迟到早退/加班统计"""

    LATE_THRESHOLD = "09:00"
    EARLY_THRESHOLD = "18:00"
    STANDARD_HOURS = 8.0

    def __init__(self):
        self._records: Dict[str, AttendanceRecord] = {}

    def record_check_in(self, emp_id: str, check_time: str, record_date: Optional[str] = None) -> AttendanceRecord:
        today = record_date or date.today().isoformat()
        rid = hashlib.md5(f"{emp_id}:{today}".encode()).hexdigest()[:16]
        rec = self._records.get(rid, AttendanceRecord(record_id=rid, emp_id=emp_id, date=today))
        rec.check_in = check_time
        if check_time > self.LATE_THRESHOLD:
            rec.status = "late"
        self._records[rid] = rec
        return rec

    def record_check_out(
        self, emp_id: str, check_time: str, record_date: Optional[str] = None
    ) -> Optional[AttendanceRecord]:
        today = record_date or date.today().isoformat()
        rid = hashlib.md5(f"{emp_id}:{today}".encode()).hexdigest()[:16]
        rec = self._records.get(rid)
        if not rec:
            return None
        rec.check_out = check_time
        rec.work_hours = self._calc_work_hours(rec.check_in, check_time)
        if rec.work_hours > self.STANDARD_HOURS:
            rec.overtime_hours = rec.work_hours - self.STANDARD_HOURS
        if check_time < self.EARLY_THRESHOLD and rec.status == "normal":
            rec.status = "early_leave"
        self._records[rid] = rec
        return rec

    def record_absence(self, emp_id: str, record_date: str, reason: str = "") -> AttendanceRecord:
        rid = hashlib.md5(f"{emp_id}:{record_date}".encode()).hexdigest()[:16]
        rec = AttendanceRecord(record_id=rid, emp_id=emp_id, date=record_date, status="absent", remark=reason)
        self._records[rid] = rec
        return rec

    def _calc_work_hours(self, check_in: Optional[str], check_out: Optional[str]) -> float:
        if not check_in or not check_out:
            return 0.0
        try:
            t_in = datetime.strptime(check_in, "%H:%M")
            t_out = datetime.strptime(check_out, "%H:%M")
            diff = (t_out - t_in).total_seconds() / 3600
            return max(0.0, round(diff, 2))
        except Exception:
            return 0.0

    def get_monthly_summary(self, emp_id: str, year_month: str) -> Dict:
        records = [r for r in self._records.values() if r.emp_id == emp_id and r.date.startswith(year_month)]
        total_hours = sum(r.work_hours for r in records)
        overtime = sum(r.overtime_hours for r in records)
        late_count = sum(1 for r in records if r.status == "late")
        absent_count = sum(1 for r in records if r.status == "absent")
        work_days = sum(1 for r in records if r.status in ("normal", "late", "early_leave"))
        return {
            "total_hours": round(total_hours, 1),
            "overtime_hours": round(overtime, 1),
            "late_count": late_count,
            "absent_count": absent_count,
            "work_days": work_days,
            "total_records": len(records),
        }

# ============================================================
# 薪酬计算引擎
# ============================================================

class SalaryEngine(object):
    """薪酬计算引擎 — 基本工资/绩效奖金/社保公积金/个税"""

    def __init__(self):
        self._social_rates = {
            "pension": {"employee": 0.08, "employer": 0.16},
            "medical": {"employee": 0.02, "employer": 0.10},
            "unemployment": {"employee": 0.005, "employer": 0.005},
            "housing_fund": {"employee": 0.12, "employer": 0.12},
        }
        self._tax_brackets = [
            (36000, 0.03, 0),
            (144000, 0.10, 2520),
            (300000, 0.20, 16920),
            (420000, 0.25, 31920),
            (660000, 0.30, 52920),
            (960000, 0.35, 85920),
            (float("inf"), 0.45, 181920),
        ]
        self._threshold = 5000  # 起征点

    def calculate_payslip(self, emp: Employee, month: str) -> Dict:
        """计算月度工资单"""
        base = emp.salary_base
        bonus = emp.salary_bonus

        # 社保公积金（个人部分）
        social_total = 0.0
        social_details = {}
        for name, rates in self._social_rates.items():
            amount = round(base * rates["employee"], 2)
            social_details[name] = amount
            social_total += amount

        # 应纳税所得额
        taxable = base + bonus - social_total - self._threshold
        taxable = max(0.0, taxable)

        # 个税计算（累计预扣法简化为月度）
        tax = self._calc_tax(taxable)

        # 实发工资
        net_pay = base + bonus - social_total - tax

        return {
            "emp_id": emp.emp_id,
            "month": month,
            "base_salary": base,
            "bonus": bonus,
            "gross_pay": base + bonus,
            "social_insurance": round(social_total, 2),
            "social_details": social_details,
            "taxable_income": round(taxable, 2),
            "tax": round(tax, 2),
            "net_pay": round(net_pay, 2),
        }

    def _calc_tax(self, taxable: float) -> float:
        for upper, rate, deduction in self._tax_brackets:
            if taxable <= upper:
                return round(taxable * rate - deduction, 2)
        return round(taxable * 0.45 - 181920, 2)

    def calculate_dept_payroll(self, employees: List[Employee], month: str) -> Dict:
        """计算部门薪资汇总"""
        total_gross = 0.0
        total_net = 0.0
        total_tax = 0.0
        total_social = 0.0
        slips = []
        for emp in employees:
            slip = self.calculate_payslip(emp, month)
            slips.append(slip)
            total_gross += slip["gross_pay"]
            total_net += slip["net_pay"]
            total_tax += slip["tax"]
            total_social += slip["social_insurance"]
        return {
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_tax": round(total_tax, 2),
            "total_social": round(total_social, 2),
            "headcount": len(employees),
            "avg_salary": round(total_gross / len(employees), 2) if employees else 0,
            "payslips": slips,
        }

# ============================================================
class CompensationCalculator:
    """薪酬计算引擎 - 处理薪资结构、社保公积金、个税和绩效奖金。

    企业场景：月薪+绩效+津贴的复合薪资体系，需要正确处理
    五险一金扣除、累计预扣法个税、年终奖单独计税。
    """

    # 2024年度个税累进税率
    TAX_BRACKETS = [
        (36000, 0.03, 0),
        (144000, 0.10, 2520),
        (300000, 0.20, 16920),
        (420000, 0.25, 31920),
        (660000, 0.30, 52920),
        (960000, 0.35, 85920),
        (float("inf"), 0.45, 181920),
    ]

    def __init__(self):
        self._base_rates = {
            "pension_employee": 0.08,
            "pension_employer": 0.16,
            "medical_employee": 0.02,
            "medical_employer": 0.10,
            "unemployment_employee": 0.005,
            "unemployment_employer": 0.005,
            "housing_employee": 0.12,
            "housing_employer": 0.12,
        }

    def calculate_monthly(
        self, base_salary: float, performance: float = 0, allowances: float = 0, housing_fund_base: float = None
    ) -> Dict:
        """计算月度工资明细"""
        gross = base_salary + performance + allowances
        # 五险一金
        hf_base = min(housing_fund_base or base_salary, 31884)  # 公积金基数上限
        social_base = min(base_salary, 31884)
        deductions = {}
        total_deduction = 0
        for key, rate in self._base_rates.items():
            if "housing" in key:
                amount = round(hf_base * rate, 2)
            else:
                amount = round(social_base * rate, 2)
            deductions[key] = amount
            if "_employee" in key:
                total_deduction += amount
        # 应纳税所得额
        taxable = gross - total_deduction - 5000  # 起征点
        tax = self._calc_tax(taxable)
        net = gross - total_deduction - tax
        return {
            "gross_salary": round(gross, 2),
            "social_deductions": round(total_deduction, 2),
            "individual_tax": round(tax, 2),
            "net_salary": round(net, 2),
            "detail": deductions,
        }

    def _calc_tax(self, taxable_income: float) -> float:
        """累计预扣法计算个税"""
        if taxable_income <= 0:
            return 0
        for bracket, rate, quick_deduction in self.TAX_BRACKETS:
            if taxable_income <= bracket:
                return round(taxable_income * rate - quick_deduction, 2)
        return 0

    def calculate_annual_bonus(self, bonus: float, method: str = "separate") -> Dict:
        """年终奖计税（单独计税/合并计税）"""
        if method == "separate":
            monthly_avg = bonus / 12
            tax = self._calc_bonus_tax(monthly_avg) * 12
        else:
            tax = self._calc_tax(bonus)  # 并入综合所得
        return {"bonus": bonus, "method": method, "tax": round(tax, 2), "net": round(bonus - tax, 2)}

    def _calc_bonus_tax(self, monthly_avg: float) -> float:
        """年终奖单独计税的月均税率"""
        brackets = [
            (3000, 0.03, 0),
            (12000, 0.10, 210),
            (25000, 0.20, 1410),
            (35000, 0.25, 2660),
            (55000, 0.30, 4410),
            (80000, 0.35, 7160),
            (float("inf"), 0.45, 15160),
        ]
        for bracket, rate, qd in brackets:
            if monthly_avg <= bracket:
                return monthly_avg * rate - qd
        return 0

    def estimate_annual_cost(self, base_salary: float, headcount: int = 1) -> Dict:
        """估算企业年度用工成本（含雇主社保）"""
        monthly = self.calculate_monthly(base_salary)
        employer_cost = base_salary  # 基础薪资
        social_base = min(base_salary, 31884)
        for key, rate in self._base_rates.items():
            if "_employer" in key:
                employer_cost += social_base * rate
        annual = employer_cost * 12 * headcount
        return {
            "monthly_employer_cost": round(employer_cost, 2),
            "annual_total_cost": round(annual, 2),
            "per_head_monthly": round(employer_cost, 2),
            "social_ratio": round((employer_cost - base_salary) / base_salary * 100, 1),
        }

# 主模块: AgentHera
# ============================================================

class AgentHera(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Hera智能体 — 人力资源管理引擎"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(module_name="agent_hera", version="6.39.0", config=config)
        self._employees: Dict[str, Employee] = {}
        self._departments: Dict[str, Department] = {}
        self._attendance = AttendanceEngine()
        self._salary_engine = SalaryEngine()
        self._reviews: Dict[str, PerformanceReview] = {}
        self._stats = {
            "total_employees": 0,
            "total_departments": 0,
            "total_attendance_records": 0,
            "total_reviews": 0,
            "total_payroll_calculations": 0,
        }

    async def initialize(self) -> None:
        await super().initialize()
        self._update_status(ModuleStatus.READY)
        logger.info("AgentHera 人力资源管理引擎初始化完成")

    # === 部门管理 ===

    async def create_department(
        self,
        dept_id: str,
        name: str,
        parent_id: Optional[str] = None,
        head_id: Optional[str] = None,
        budget: float = 0.0,
        headcount_limit: int = 50,
    ) -> Result:
        if dept_id in self._departments:
            return Result(success=False, message=f"部门 {dept_id} 已存在")
        dept = Department(
            dept_id=dept_id,
            name=name,
            parent_id=parent_id,
            head_id=head_id,
            budget=budget,
            headcount_limit=headcount_limit,
        )
        self._departments[dept_id] = dept
        self._stats["total_departments"] += 1
        await self._audit_log("create_department", f"创建部门: {name} ({dept_id})")
        return Result(success=True, data=dept.to_dict())

    async def get_dept_tree(self) -> Result:
        """获取部门树形结构"""
        roots = []
        for dept in self._departments.values():
            if not dept.parent_id or dept.parent_id not in self._departments:
                roots.append(self._build_dept_node(dept))
        return Result(success=True, data={"tree": roots})

    def _build_dept_node(self, dept: Department) -> Dict:
        children = [self._build_dept_node(d) for d in self._departments.values() if d.parent_id == dept.dept_id]
        member_count = sum(
            1 for e in self._employees.values() if e.dept_id == dept.dept_id and e.status == EmployeeStatus.ACTIVE
        )
        return {
            "dept_id": dept.dept_id,
            "name": dept.name,
            "member_count": member_count,
            "budget": dept.budget,
            "children": children,
        }

    # === 员工管理 ===

    async def hire_employee(
        self,
        emp_id: str,
        name: str,
        dept_id: str,
        position: str,
        level: str,
        salary_base: float,
        email: str = "",
        phone: str = "",
        manager_id: Optional[str] = None,
        skills: Optional[List[str]] = None,
    ) -> Result:
        if emp_id in self._employees:
            return Result(success=False, message=f"员工 {emp_id} 已存在")
        if dept_id and dept_id not in self._departments:
            return Result(success=False, message=f"部门 {dept_id} 不存在")
        emp = Employee(
            emp_id=emp_id,
            name=name,
            dept_id=dept_id,
            position=position,
            level=level,
            salary_base=salary_base,
            email=email,
            phone=phone,
            manager_id=manager_id,
            skills=skills or [],
            hire_date=date.today().isoformat(),
            status=EmployeeStatus.ACTIVE,
        )
        self._employees[emp_id] = emp
        self._stats["total_employees"] += 1
        await self._audit_log("hire_employee", f"入职: {name} ({emp_id}) -> {dept_id}")
        return Result(success=True, data=emp.to_dict())

    async def update_employee(self, emp_id: str, **kwargs) -> Result:
        emp = self._employees.get(emp_id)
        if not emp:
            return Result(success=False, message=f"员工 {emp_id} 不存在")
        for k, v in kwargs.items():
            if hasattr(emp, k):
                setattr(emp, k, v)
        emp.updated_at = time.time()
        await self._audit_log("update_employee", f"更新员工: {emp_id}")
        return Result(success=True, data=emp.to_dict())

    async def terminate_employee(self, emp_id: str, reason: str = "") -> Result:
        emp = self._employees.get(emp_id)
        if not emp:
            return Result(success=False, message=f"员工 {emp_id} 不存在")
        old_status = emp.status
        emp.status = EmployeeStatus.RESIGNED
        emp.updated_at = time.time()
        emp.attributes["termination_reason"] = reason
        emp.attributes["terminated_at"] = time.time()
        await self._audit_log("terminate_employee", f"离职: {emp.name} ({emp_id}), 原因: {reason}")
        return Result(success=True, message=f"员工 {emp_id} 已离职")

    async def list_employees(
        self, dept_id: Optional[str] = None, status: Optional[EmployeeStatus] = None, limit: int = 100
    ) -> Result:
        emps = list(self._employees.values())
        if dept_id:
            emps = [e for e in emps if e.dept_id == dept_id]
        if status:
            emps = [e for e in emps if e.status == status]
        return Result(success=True, data={"employees": [e.to_dict() for e in emps[:limit]], "total": len(emps)})

    # === 考勤管理 ===

    async def check_in(self, emp_id: str, check_time: str, record_date: Optional[str] = None) -> Result:
        if emp_id not in self._employees:
            return Result(success=False, message=f"员工 {emp_id} 不存在")
        rec = self._attendance.record_check_in(emp_id, check_time, record_date)
        self._stats["total_attendance_records"] += 1
        return Result(success=True, data=rec.to_dict())

    async def check_out(self, emp_id: str, check_time: str, record_date: Optional[str] = None) -> Result:
        rec = self._attendance.record_check_out(emp_id, check_time, record_date)
        if not rec:
            return Result(success=False, message="未找到签到记录")
        return Result(success=True, data=rec.to_dict())

    async def get_attendance_summary(self, emp_id: str, year_month: str) -> Result:
        summary = self._attendance.get_monthly_summary(emp_id, year_month)
        return Result(success=True, data=summary)

    # === 绩效管理 ===

    async def submit_review(
        self,
        emp_id: str,
        period: str,
        rating: PerformanceRating,
        score: float,
        goals_completed: int,
        goals_total: int,
        reviewer_id: str,
        feedback: str = "",
        strengths: Optional[List[str]] = None,
        improvements: Optional[List[str]] = None,
    ) -> Result:
        if emp_id not in self._employees:
            return Result(success=False, message=f"员工 {emp_id} 不存在")
        review_id = hashlib.md5(f"{emp_id}:{period}".encode()).hexdigest()[:16]
        review = PerformanceReview(
            review_id=review_id,
            emp_id=emp_id,
            period=period,
            rating=rating,
            score=score,
            goals_completed=goals_completed,
            goals_total=goals_total,
            reviewer_id=reviewer_id,
            feedback=feedback,
            strengths=strengths or [],
            improvements=improvements or [],
            promotion_recommendation=rating in (PerformanceRating.EXCELLENT, PerformanceRating.GOOD),
        )
        self._reviews[review_id] = review
        self._stats["total_reviews"] += 1
        await self._audit_log("submit_review", f"提交绩效: {emp_id} {period} {rating.value}")
        return Result(success=True, data=review.to_dict())

    async def get_employee_reviews(self, emp_id: str) -> Result:
        reviews = [r for r in self._reviews.values() if r.emp_id == emp_id]
        reviews.sort(key=lambda r: r.period, reverse=True)
        return Result(success=True, data={"reviews": [r.to_dict() for r in reviews]})

    # === 薪酬管理 ===

    async def calculate_payslip(self, emp_id: str, month: str) -> Result:
        emp = self._employees.get(emp_id)
        if not emp:
            return Result(success=False, message=f"员工 {emp_id} 不存在")
        slip = self._salary_engine.calculate_payslip(emp, month)
        self._stats["total_payroll_calculations"] += 1
        return Result(success=True, data=slip)

    async def calculate_dept_payroll(self, dept_id: str, month: str) -> Result:
        emps = [e for e in self._employees.values() if e.dept_id == dept_id and e.status == EmployeeStatus.ACTIVE]
        result = self._salary_engine.calculate_dept_payroll(emps, month)
        return Result(success=True, data=result)

    # === 离职预警 ===

    async def turnover_risk_analysis(self) -> Result:
        """离职风险分析"""
        risk_list = []
        for emp in self._employees.values():
            if emp.status != EmployeeStatus.ACTIVE:
                continue
            risk_score = 0.0
            factors = []
            # 工龄短
            if emp.tenure_days < 90:
                risk_score += 0.2
                factors.append("工龄<3个月")
            # 薪资低于部门平均
            dept_emps = [
                e for e in self._employees.values() if e.dept_id == emp.dept_id and e.status == EmployeeStatus.ACTIVE
            ]
            if dept_emps:
                avg_sal = sum(e.salary_base for e in dept_emps) / len(dept_emps)
                if emp.salary_base < avg_sal * 0.8:
                    risk_score += 0.15
                    factors.append("薪资低于部门均值20%+")
            # 绩效低
            emp_reviews = [r for r in self._reviews.values() if r.emp_id == emp.emp_id]
            if emp_reviews:
                latest = max(emp_reviews, key=lambda r: r.period)
                if latest.rating in (PerformanceRating.NEEDS_IMPROVEMENT, PerformanceRating.UNSATISFACTORY):
                    risk_score += 0.25
                    factors.append(f"最近绩效: {latest.rating.value}")
            # 无manager
            if not emp.manager_id:
                risk_score += 0.1
                factors.append("无直属上级")
            risk_score = min(1.0, risk_score)
            if risk_score >= 0.3:
                risk_list.append(
                    {
                        "emp_id": emp.emp_id,
                        "name": emp.name,
                        "dept_id": emp.dept_id,
                        "risk_score": round(risk_score, 3),
                        "factors": factors,
                    }
                )
        risk_list.sort(key=lambda x: x["risk_score"], reverse=True)
        return Result(success=True, data={"high_risk_count": len(risk_list), "employees": risk_list})

    # === 统计报表 ===

    async def get_org_stats(self) -> Result:
        active = [e for e in self._employees.values() if e.status == EmployeeStatus.ACTIVE]
        dept_stats = {}
        for emp in active:
            d = emp.dept_id or "未分配"
            if d not in dept_stats:
                dept_stats[d] = {"count": 0, "total_salary": 0.0}
            dept_stats[d]["count"] += 1
            dept_stats[d]["total_salary"] += emp.total_salary
        return Result(
            success=True,
            data={
                "total_active": len(active),
                "dept_stats": dept_stats,
                "avg_tenure_days": round(sum(e.tenure_days for e in active) / len(active), 1) if active else 0,
            },
        )

    # === 健康检查 ===

    async def execute(self, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """统一执行入口 — 团队管理路由"""
        _ = self.trace("execute")
        metrics_collector.counter("agent_hera_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        if action == "health":
            hr = self.health_check()
            return hr.to_dict() if hasattr(hr, "to_dict") else {"status": "healthy"}
        elif action == "stats":
            teams = self._teams if hasattr(self, "_teams") else {}
            return {"success": True, "result": {"total_teams": len(teams)}}
        return {"success": False, "error": f"Unknown action: {action}"}

    def health_check(self) -> HealthReport:
        checks = {
            "employee_store": True,
            "department_store": True,
            "attendance_engine": True,
            "salary_engine": True,
            "review_store": True,
        }
        return HealthReport(
            module_name=self.module_name,
            status=ModuleStatus.RUNNING,
            checks=checks,
            stats=ModuleStats(total_operations=sum(self._stats.values())),
        )

    async def get_module_stats(self) -> Result:
        return Result(success=True, data=self._stats)

    def shutdown(self) -> dict:
        """Graceful shutdown for agent_hera."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = AgentHera
