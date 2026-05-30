"""
AUTO-EVO-AI V0.1 — 安全扫描器
Grade: A (生产级) | Category: 安全合规
职责：漏洞扫描、代码安全审计、依赖安全、配置安全、合规检测
"""

__module_meta__ = {
    "id": "security-scanner",
    "name": "Security Scanner",
    "version": "V0.1",
    "group": "security",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [
        {"type": "schedule", "config": {"cron": "0 */4 * * *"}},
        {"type": "event", "config": {"on": "security_scanner.scan.request"}},
    ],
    "depends_on": [],
    "tags": ["adapter", "scanner", "security"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 安全扫描器 Grade: A (生产级) | Category: 安全合规",
}

import asyncio
import sys
import subprocess
import time
import uuid
import re
import os
import json
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("security_scanner")

class _MetricsAdapter:
    """轻量指标适配器"""
    def __init__(self):self._data={}
    def increment(self,name:str,value:float=1.0,**kw):self._data[name]=self._data.get(name,0)+value
    def histogram(self,name:str,value:float,**kw):self._data[name]=value
    def gauge(self,name:str,value:float,**kw):self._data[name]=value
    def snapshot(self):return dict(self._data)

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class VulnLevel(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ScanType(Enum):
    CODE = "code"
    DEPENDENCY = "dependency"
    CONFIG = "config"
    NETWORK = "network"
    FULL = "full"

@dataclass
class SecurityFinding:
    """安全发现"""

    finding_id: str
    scan_id: str
    title: str
    description: str
    level: VulnLevel
    category: str
    file_path: str = ""
    line_number: int = 0
    code_snippet: str = ""
    cve: Optional[str] = None
    cvss_score: float = 0.0
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    false_positive: bool = False

@dataclass
class ScanReport:
    """扫描报告"""

    scan_id: str
    scan_type: ScanType
    target: str
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "running"
    findings: List[SecurityFinding] = field(default_factory=list)
    files_scanned: int = 0
    lines_scanned: int = 0
    duration_ms: float = 0.0
    score: float = 100.0

class VulnerabilityEvaluator(object):
    """漏洞评估引擎 — CVSS风格评估、风险优先级排序、修复建议生成、误报检测"""

    """漏洞评分引擎 — CVSS风格评估、风险优先级排序、修复建议生成"""

    # CVSS基础指标权重
    _IMPACT_WEIGHTS = {"critical": 10.0, "high": 7.5, "medium": 5.0, "low": 2.5, "info": 0.5}
    _ATTACK_VECTOR_WEIGHTS = {"network": 1.0, "adjacent": 0.8, "local": 0.6, "physical": 0.3}
    _COMPLEXITY_WEIGHTS = {"low": 1.0, "medium": 0.8, "high": 0.5}

    def score_finding(
        self,
        severity: str,
        attack_vector: str = "network",
        complexity: str = "low",
        description: str = "",
        has_exploit: bool = False,
        affected_assets: int = 1,
    ) -> Dict[str, Any]:
        """为单个发现计算综合风险分数"""
        base_score = self._IMPACT_WEIGHTS.get(severity.lower(), 5.0)
        av_mult = self._ATTACK_VECTOR_WEIGHTS.get(attack_vector.lower(), 0.8)
        cx_mult = self._COMPLEXITY_WEIGHTS.get(complexity.lower(), 0.8)
        exploit_mult = 1.5 if has_exploit else 1.0
        asset_mult = min(1.0 + (affected_assets - 1) * 0.1, 2.0)

        risk_score = round(min(base_score * av_mult * cx_mult * exploit_mult * asset_mult, 10.0), 1)
        risk_level = (
            "critical"
            if risk_score >= 9.0
            else "high"
            if risk_score >= 7.0
            else "medium"
            if risk_score >= 4.0
            else "low"
            if risk_score >= 1.0
            else "info"
        )
        priority = (
            "P0"
            if risk_score >= 9.0
            else "P1"
            if risk_score >= 7.0
            else "P2"
            if risk_score >= 4.0
            else "P3"
            if risk_score >= 1.0
            else "P4"
        )

        return {
            "base_severity": severity,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "priority": priority,
            "exploit_available": has_exploit,
            "affected_assets": affected_assets,
            "suggested_sla_hours": self._recommend_sla(risk_level),
            "remediation_hint": self._get_remediation_hint(severity.lower(), description),
        }

    def score_report(self, findings: List[Dict]) -> Dict[str, Any]:
        """评估整份扫描报告，生成综合风险摘要"""
        if not findings:
            return {"overall_score": 100.0, "grade": "A", "summary": "未发现安全问题"}

        scores = [f.get("risk_score", 5.0) if isinstance(f, dict) else 5.0 for f in findings]
        avg_risk = round(sum(scores) / len(scores), 1)
        max_risk = round(max(scores), 1)
        critical_count = sum(1 for s in scores if s >= 9.0)
        high_count = sum(1 for s in scores if 7.0 <= s < 9.0)
        medium_count = sum(1 for s in scores if 4.0 <= s < 7.0)
        low_count = sum(1 for s in scores if s < 4.0)

        overall_score = round(max(0, 100 - max_risk * 8 - avg_risk * 2), 1)
        grade = (
            "F"
            if overall_score < 30
            else "D"
            if overall_score < 50
            else "C"
            if overall_score < 70
            else "B"
            if overall_score < 85
            else "A"
        )

        return {
            "overall_score": overall_score,
            "grade": grade,
            "total_findings": len(findings),
            "by_severity": {"critical": critical_count, "high": high_count, "medium": medium_count, "low": low_count},
            "avg_risk_score": avg_risk,
            "max_risk_score": max_risk,
            "top_risks": sorted(findings, key=lambda x: x.get("risk_score", 0), reverse=True)[:5],
            "recommendation": self._report_recommendation(critical_count, high_count, overall_score),
        }

    def prioritize_remediation(self, findings: List[Dict], team_capacity: int = 3) -> List[Dict]:
        """根据团队容量生成修复优先级排序列表"""
        scored = []
        for f in findings:
            if isinstance(f, dict) and "risk_score" not in f:
                f = self.score_finding(
                    severity=f.get("severity", "medium"),
                    attack_vector=f.get("attack_vector", "network"),
                    complexity=f.get("complexity", "low"),
                    description=f.get("description", ""),
                    has_exploit=f.get("has_exploit", False),
                )
            scored.append(f)
        scored.sort(key=lambda x: x.get("risk_score", 0), reverse=True)

        sprints = []
        current_sprint = []
        remaining_capacity = team_capacity
        for f in scored:
            effort = 1 if f.get("risk_score", 5) >= 7 else 0.5
            if effort <= remaining_capacity:
                current_sprint.append({**f, "sprint_ready": True})
                remaining_capacity -= effort
            else:
                if current_sprint:
                    sprints.append(current_sprint)
                current_sprint = [{**f, "sprint_ready": remaining_capacity > 0}]
                remaining_capacity = team_capacity - (
                    effort if remaining_capacity == 0 else effort - remaining_capacity
                )
        if current_sprint:
            sprints.append(current_sprint)

        return {
            "total_items": len(scored),
            "sprints": [{"sprint": i + 1, "items": len(s), "items_list": s} for i, s in enumerate(sprints)],
            "estimated_sprints": len(sprints),
        }

    def _recommend_sla(self, risk_level: str) -> int:
        sla_map = {"critical": 4, "high": 24, "medium": 72, "low": 168, "info": 336}
        return sla_map.get(risk_level, 72)

    def _get_remediation_hint(self, severity: str, description: str) -> str:
        hints = {
            "critical": "立即修复：分配高级工程师，启用紧急变更流程",
            "high": "高优先级：在当前冲刺内修复，增加回归测试覆盖",
            "medium": "计划修复：纳入下个冲刺，评估影响范围后实施",
            "low": "低优先级：记录为技术债务，定期审查",
            "info": "信息性：评估是否需要行动，可能无需修复",
        }
        base = hints.get(severity, hints["medium"])
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["sql", "injection", "注入"]):
            base += "。建议使用参数化查询替代字符串拼接。"
        elif any(kw in desc_lower for kw in ["xss", "cross-site", "跨站"]):
            base += "。建议对所有输出进行HTML转义。"
        elif any(kw in desc_lower for kw in ["hardcoded", "硬编码", "密码", "password", "secret"]):
            base += "。建议使用密钥管理服务存储敏感信息。"
        return base

    def _report_recommendation(self, critical: int, high: int, score: float) -> str:
        if critical > 0:
            return f"发现{critical}个严重漏洞，系统安全状态危险。建议立即暂停上线，优先修复所有严重和高危漏洞。"
        if high > 3:
            return f"发现{high}个高危漏洞，建议在48小时内完成修复并重新扫描验证。"
        if score < 70:
            return "安全评分偏低，建议制定修复计划并在2周内完成所有高危和中危漏洞的修复。"
        return "安全状态良好，建议定期扫描并持续关注新发现的安全问题。"

    def detect_false_positives(self, findings: List[Dict]) -> Dict[str, Any]:
        """检测可能的误报：基于模式置信度、上下文分析、历史标记"""
        if not findings:
            return {"total": 0, "likely_false_positives": 0, "details": []}
        false_positives = []
        for f in findings:
            fp_score = 0
            description = str(f.get("description", "")).lower()
            filepath = str(f.get("file_path", "")).lower()
            if len(description) < 20:
                fp_score += 3
            if "test" in filepath:
                fp_score += 2
            if "mock" in filepath or "fixture" in filepath:
                fp_score += 3
            if "example" in filepath or "demo" in filepath:
                fp_score += 2
            severity = str(f.get("severity", "")).lower()
            if severity in ("info", "low"):
                fp_score += 1
            is_likely_fp = fp_score >= 4
            if is_likely_fp:
                reasons = []
                if fp_score >= 5:
                    reasons.append("测试/示例文件中的发现")
                if len(description) < 20:
                    reasons.append("描述过于简短，缺少上下文")
                false_positives.append(
                    {**f, "fp_score": fp_score, "reason": "; ".join(reasons) or "综合评估为可能误报"}
                )
        return {
            "total": len(findings),
            "likely_false_positives": len(false_positives),
            "false_positive_rate": round(len(false_positives) / max(len(findings), 1), 3),
            "details": false_positives,
        }

class SecurityScanner(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """安全扫描器"""

    def __init__(self):

        super().__init__()
        self._metrics = _MetricsAdapter()
        self._scan_history: List[ScanReport] = []
        self._code_rules = self._init_code_rules()
        self._config_rules = self._init_config_rules()
        self._known_cve = self._init_cve_db()
        self._max_scan_size = 50 * 1024 * 1024
        self._vuln_scorer = VulnerabilityEvaluator()

    def _init_code_rules(self) -> List[Dict]:
        """代码安全规则"""
        return [
            {
                "id": "SEC001",
                "title": "SQL注入风险",
                "level": VulnLevel.CRITICAL,
                "pattern": r"(execute|cursor\.\w+)\s*\(\s*['\"].*\%s|\.format\(|f['\"].*SELECT|f['\"].*INSERT",
                "category": "injection",
                "remediation": "使用参数化查询替代字符串拼接",
            },
            {
                "id": "SEC002",
                "title": "命令注入风险",
                "level": VulnLevel.CRITICAL,
                "pattern": r"os\.(system|popen|exec|spawn)\s*\(\s*['\"].*\+|subprocess\.\w+\s*\(\s*['\"].*\+|eval\s*\(",
                "category": "injection",
                "remediation": "使用subprocess安全API或shlex.quote",
            },
            {
                "id": "SEC003",
                "title": "XSS风险",
                "level": VulnLevel.HIGH,
                "pattern": r"(innerHTML|dangerouslySetInnerHTML|render_template_string|Markup)\s*\(",
                "category": "xss",
                "remediation": "使用安全的模板渲染和HTML转义",
            },
            {
                "id": "SEC004",
                "title": "硬编码敏感信息",
                "level": VulnLevel.CRITICAL,
                "pattern": r"(password|passwd|secret|api_key|apikey|token|private_key)\s*=\s*['\"][^'\"]{8,}['\"]",
                "category": "credentials",
                "remediation": "使用环境变量或密钥管理器",
            },
            {
                "id": "SEC005",
                "title": "不安全的反序列化",
                "level": VulnLevel.HIGH,
                "pattern": r"(pickle\.loads?|yaml\.load\(|marshal\.loads?|shelve\.open)\s*\(",
                "category": "deserialization",
                "remediation": "使用json替代pickle，yaml用safe_load",
            },
            {
                "id": "SEC006",
                "title": "弱哈希算法",
                "level": VulnLevel.MEDIUM,
                "pattern": r"\bhashlib\.md5\(|\.md5\(|hashlib\.sha1\(",
                "category": "cryptography",
                "remediation": "使用sha256或更强的哈希算法",
            },
            {
                "id": "SEC007",
                "title": "不安全的随机数",
                "level": VulnLevel.MEDIUM,
                "pattern": r"random\.(random|randint|choice|sample)\s*\(",
                "category": "cryptography",
                "remediation": "安全场景使用secrets模块",
            },
            {
                "id": "SEC008",
                "title": "不安全的SSL/TLS",
                "level": VulnLevel.HIGH,
                "pattern": r"(verify\s*=\s*False|ssl\._create_unverified_context|CERT_NONE)",
                "category": "ssl",
                "remediation": "启用SSL证书验证",
            },
            {
                "id": "SEC009",
                "title": "路径遍历风险",
                "level": VulnLevel.HIGH,
                "pattern": r"open\s*\(\s*(os\.path\.join|request\.|user_).*(?:\+\s*['\"]|\.format)",
                "category": "path_traversal",
                "remediation": "验证和清理用户输入的路径",
            },
            {
                "id": "SEC010",
                "title": "调试代码残留",
                "level": VulnLevel.LOW,
                "pattern": r"(pdb\.set_trace|breakpoint\(\)|import pdb|print\(.*password|console\.log\(.*token)",
                "category": "debugging",
                "remediation": "移除调试代码",
            },
            {
                "id": "SEC011",
                "title": "CORS配置过于宽松",
                "level": VulnLevel.MEDIUM,
                "pattern": r"(Access-Control-Allow-Origin.*\*|cors\(.*origins\s*=\s*\[.?\*\])",
                "category": "misconfiguration",
                "remediation": "限制允许的来源域名",
            },
            {
                "id": "SEC012",
                "title": "不安全的文件上传",
                "level": VulnLevel.HIGH,
                "pattern": r"(save\s*\(.*request\.|upload.*\.(save|write)|shutil\.copyfileobj.*request)",
                "category": "file_upload",
                "remediation": "验证文件类型、大小和内容",
            },
        ]

    def _init_config_rules(self) -> List[Dict]:
        """配置安全规则"""
        return [
            {
                "id": "CFG001",
                "title": "DEBUG模式启用",
                "level": VulnLevel.HIGH,
                "pattern": r"DEBUG\s*=\s*True",
                "file_patterns": [".py", ".env", ".yaml", ".yml"],
                "remediation": "生产环境禁用DEBUG模式",
            },
            {
                "id": "CFG002",
                "title": "密钥为空或默认值",
                "level": VulnLevel.CRITICAL,
                "pattern": r"(SECRET_KEY|API_KEY|JWT_SECRET|DB_PASSWORD)\s*=\s*['\"]?(\s*|changeme|default|secret|password|12345)",
                "file_patterns": [".py", ".env", ".yaml", ".yml", ".json"],
                "remediation": "设置强随机密钥",
            },
            {
                "id": "CFG003",
                "title": "允许所有主机",
                "level": VulnLevel.MEDIUM,
                "pattern": r"ALLOWED_HOSTS\s*=\s*\[.?\*|\*|\[.?\].?\*",
                "file_patterns": [".py", ".env"],
                "remediation": "限制允许的主机列表",
            },
            {
                "id": "CFG004",
                "title": "日志暴露敏感信息",
                "level": VulnLevel.LOW,
                "pattern": r"(logging\.|logger\.|log\.).*(password|token|secret|key|cookie)",
                "file_patterns": [".py"],
                "remediation": "确保日志不记录敏感信息",
            },
            {
                "id": "CFG005",
                "title": ".env文件在版本控制中",
                "level": VulnLevel.HIGH,
                "pattern": r".env",
                "file_patterns": [".gitignore"],
                "remediation": "将.env添加到.gitignore",
            },
        ]

    def _init_cve_db(self) -> List[Dict]:
        """已知CVE数据库（模拟）"""
        return [
            {
                "cve": "CVE-2023-32681",
                "package": "requests",
                "versions": "<2.31.0",
                "cvss": 7.5,
                "title": "请求走私漏洞",
                "fix": "升级到>=2.31.0",
            },
            {
                "cve": "CVE-2023-43804",
                "package": "urllib3",
                "versions": "<1.26.18",
                "cvss": 5.3,
                "title": "ReDoS漏洞",
                "fix": "升级到>=1.26.18",
            },
            {
                "cve": "CVE-2023-44271",
                "package": "pillow",
                "versions": "<10.0.1",
                "cvss": 9.8,
                "title": "缓冲区溢出",
                "fix": "升级到>=10.0.1",
            },
            {
                "cve": "CVE-2023-46695",
                "package": "django",
                "versions": "<4.2.7",
                "cvss": 8.8,
                "title": "SQL注入",
                "fix": "升级到>=4.2.7",
            },
            {
                "cve": "CVE-2023-31147",
                "package": "flask",
                "versions": "<2.3.3",
                "cvss": 6.1,
                "title": "Cookie安全",
                "fix": "升级到>=2.3.3",
            },
            {
                "cve": "CVE-2023-40203",
                "package": "cryptography",
                "versions": "<41.0.3",
                "cvss": 9.1,
                "title": "内存损坏",
                "fix": "升级到>=41.0.3",
            },
        ]

    @trace_operation("security_scan")
    def scan(self, target: str, scan_type: ScanType = ScanType.FULL, depth: int = 3) -> Dict[str, Any]:
        """执行安全扫描"""
        scan_id = f"scan_{uuid.uuid4().hex[:10]}"
        report = ScanReport(scan_id=scan_id, scan_type=scan_type, target=target)

        start = time.time()
        try:
            if scan_type in (ScanType.CODE, ScanType.FULL):
                self._scan_code(target, report, depth)
            if scan_type in (ScanType.CONFIG, ScanType.FULL):
                self._scan_config(target, report)
            if scan_type in (ScanType.DEPENDENCY, ScanType.FULL):
                self._scan_dependencies(target, report)

            # 真实 bandit 扫描（Python 安全审计）
            if scan_type in (ScanType.CODE, ScanType.FULL) and os.path.isdir(target):
                self._run_bandit(target, report)
            # 真实 safety 扫描（Python 依赖漏洞）
            if scan_type in (ScanType.DEPENDENCY, ScanType.FULL):
                self._run_safety(report)

            report.status = "completed"
            report.score = self._calculate_security_score(report.findings)
        except Exception as e:
            report.status = "error"
            report.findings.append(
                SecurityFinding(
                    finding_id=f"f_{uuid.uuid4().hex[:8]}",
                    scan_id=scan_id,
                    title="扫描错误",
                    description=str(e),
                    level=VulnLevel.MEDIUM,
                    category="scanner",
                )
            )

        report.completed_at = time.time()
        report.duration_ms = (time.time() - start) * 1000
        self._scan_history.append(report)

        audit_logger.log(
            action="security_scan",
            resource=scan_id,
            details=f"目标: {target}, 发现: {len(report.findings)}, 评分: {report.score}",
        )
        self.stats["scans_completed"] += 1

        return self._format_report(report)

    def _scan_code(self, target: str, report: ScanReport, depth: int) -> None:
        """代码安全扫描"""
        if not os.path.isdir(target):
            if os.path.isfile(target):
                self._scan_file(target, report)
            return

        code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb"}
        for root, dirs, files in os.walk(target):
            depth_check = root[len(target) :].count(os.sep)
            if depth_check >= depth:
                dirs.clear()
                continue
            # 跳过.git, node_modules等
            dirs[:] = [
                d
                for d in dirs
                if d not in {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "dist", "build"}
            ]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in code_extensions:
                    fpath = os.path.join(root, fname)
                    self._scan_file(fpath, report)

    def _scan_file(self, filepath: str, report: ScanReport) -> None:
        """扫描单个文件"""
        try:
            size = os.path.getsize(filepath)
            if size > self._max_scan_size:
                return

            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            report.files_scanned += 1
            report.lines_scanned += len(lines)

            for rule in self._code_rules:
                pattern = re.compile(rule["pattern"], re.IGNORECASE)
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        finding = SecurityFinding(
                            finding_id=f"f_{uuid.uuid4().hex[:8]}",
                            scan_id=report.scan_id,
                            title=rule["title"],
                            description=rule["remediation"],
                            level=rule["level"],
                            category=rule["category"],
                            file_path=filepath,
                            line_number=i,
                            code_snippet=line.strip()[:200],
                            remediation=rule["remediation"],
                        )
                        report.findings.append(finding)
        except Exception as e:
            logger.warning(f"扫描文件失败 {filepath}: {e}")

    def _run_bandit(self, target: str, report: ScanReport) -> None:
        """调用真实 bandit 进行 Python 安全扫描"""
        try:
            r = subprocess.run(
                [sys.executable, "-m", "bandit", "-r", target, "-f", "json"],
                capture_output=True, text=True, timeout=120
            )
            if not r.stdout:
                return
            import json as _json
            data = _json.loads(r.stdout)
            for issue in data.get("results", []):
                try:
                    report.findings.append(SecurityFinding(
                        finding_id=f"bandit_{uuid.uuid4().hex[:8]}",
                        scan_id=report.scan_id,
                        title=f"Bandit: {issue.get('test_name','?')}",
                        description=issue.get("issue_text",""),
                        level=VulnLevel.HIGH if issue.get("issue_severity") == "HIGH" else
                              VulnLevel.MEDIUM if issue.get("issue_severity") == "MEDIUM" else VulnLevel.LOW,
                        category="code_security",
                        file_path=issue.get("filename",""),
                        line_number=issue.get("line_number",0),
                        code_snippet=issue.get("code","")[:500],
                        remediation=f"See: {issue.get('more_info','')}",
                    ))
                except Exception:
                    pass
            report.findings_count = len(report.findings)
        except FileNotFoundError:
            logger.info("bandit not installed, skipping real security scan")
        except subprocess.TimeoutExpired:
            logger.warning("bandit scan timed out")
        except Exception as e:
            logger.warning(f"bandit scan error: {e}")

    def _run_safety(self, report: ScanReport) -> None:
        """调用真实 safety 进行 Python 依赖漏洞扫描"""
        try:
            r = subprocess.run(
                [sys.executable, "-m", "safety", "check", "--json"],
                capture_output=True, text=True, timeout=60
            )
            if not r.stdout:
                return
            import json as _json
            data = _json.loads(r.stdout)
            if not isinstance(data, list):
                return
            for vuln in data:
                try:
                    pkg = vuln.get("package_name", vuln.get("name", "?"))
                    report.findings.append(SecurityFinding(
                        finding_id=f"safety_{uuid.uuid4().hex[:8]}",
                        scan_id=report.scan_id,
                        title=f"Safety: {pkg} {vuln.get('installed_version','?')}",
                        description=vuln.get("vulnerability", vuln.get("advisory","")),
                        level=VulnLevel.HIGH if vuln.get("severity","").upper() == "HIGH" else
                              VulnLevel.MEDIUM if vuln.get("severity","").upper() == "MEDIUM" else VulnLevel.LOW,
                        category="dependency",
                        remediation=f"Upgrade {pkg} to {vuln.get('fixed_version','latest')}",
                    ))
                except Exception:
                    pass
            report.findings_count = len(report.findings)
        except FileNotFoundError:
            logger.info("safety not installed, skipping dependency scan")
        except subprocess.TimeoutExpired:
            logger.warning("safety scan timed out")
        except Exception as e:
            logger.warning(f"safety scan error: {e}")

    def _scan_config(self, target: str, report: ScanReport) -> None:
        """配置安全扫描"""
        config_files = {
            ".env",
            "settings.py",
            "config.py",
            "config.yaml",
            "config.yml",
            "config.json",
            "application.yml",
            ".gitignore",
            "docker-compose.yml",
        }
        config_patterns = ["*.py", "*.env", "*.yaml", "*.yml", "*.json", ".gitignore"]

        for fname in config_files:
            fpath = os.path.join(target, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    lines = content.split("\n")
                    report.files_scanned += 1

                    for rule in self._config_rules:
                        pattern = re.compile(rule["pattern"], re.IGNORECASE)
                        for i, line in enumerate(lines, 1):
                            if pattern.search(line):
                                report.findings.append(
                                    SecurityFinding(
                                        finding_id=f"f_{uuid.uuid4().hex[:8]}",
                                        scan_id=report.scan_id,
                                        title=rule["title"],
                                        description=rule.get("remediation", ""),
                                        level=rule["level"],
                                        category="configuration",
                                        file_path=fpath,
                                        line_number=i,
                                        code_snippet=line.strip()[:200],
                                        remediation=rule.get("remediation", ""),
                                    )
                                )
                except Exception:
                    pass

    def _scan_dependencies(self, target: str, report: ScanReport) -> None:
        """依赖安全扫描"""
        dep_files = {
            "requirements.txt",
            "Pipfile.lock",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "yarn.lock",
        }

        deps_found: Dict[str, str] = {}
        for fname in dep_files:
            fpath = os.path.join(target, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    # 简单解析
                    if fname == "requirements.txt":
                        for line in content.split("\n"):
                            m = re.match(r"^([a-zA-Z0-9_-]+)[><=!~]*([\d.]+)?", line.strip())
                            if m:
                                deps_found[m.group(1).lower()] = m.group(2) or "0"
                    elif fname == "package.json":
                        try:
                            data = json.loads(content)
                            for section in ["dependencies", "devDependencies"]:
                                if section in data:
                                    for name, ver in data[section].items():
                                        clean = re.sub(r"[\^~>=<]", "", ver)
                                        deps_found[name.lower()] = clean
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass

        # 匹配CVE
        for pkg, version in deps_found.items():
            for cve in self._known_cve:
                if cve["package"] == pkg:
                    try:
                        ver_parts = [int(p) for p in version.split(".") if p.isdigit()]
                        fix_parts = [int(p) for p in cve["fix"].replace(">=", "").split(".") if p.isdigit()]
                        if ver_parts and fix_parts and ver_parts < fix_parts:
                            report.findings.append(
                                SecurityFinding(
                                    finding_id=f"f_{uuid.uuid4().hex[:8]}",
                                    scan_id=report.scan_id,
                                    title=cve["title"],
                                    description=f"{pkg} {version} 受 {cve['cve']} 影响",
                                    level=VulnLevel.CRITICAL
                                    if cve["cvss"] >= 9.0
                                    else VulnLevel.HIGH
                                    if cve["cvss"] >= 7.0
                                    else VulnLevel.MEDIUM,
                                    category="dependency",
                                    cve=cve["cve"],
                                    cvss_score=cve["cvss"],
                                    remediation=cve["fix"],
                                )
                            )
                    except (ValueError, IndexError):
                        pass

    def _calculate_security_score(self, findings: List[SecurityFinding]) -> float:
        """计算安全评分"""
        score = 100.0
        deductions = {
            VulnLevel.CRITICAL: 15,
            VulnLevel.HIGH: 8,
            VulnLevel.MEDIUM: 3,
            VulnLevel.LOW: 1,
            VulnLevel.INFO: 0.2,
        }
        for f in findings:
            score -= deductions.get(f.level, 0)
        return max(0, round(score, 1))

    def _format_report(self, report: ScanReport) -> Dict[str, Any]:
        """格式化扫描报告"""
        by_level = defaultdict(int)
        by_category = defaultdict(int)
        for f in report.findings:
            by_level[f.level.value] += 1
            by_category[f.category] += 1

        return {
            "scan_id": report.scan_id,
            "scan_type": report.scan_type.value,
            "target": report.target,
            "status": report.status,
            "security_score": report.score,
            "summary": {
                "total_findings": len(report.findings),
                "critical": by_level.get("critical", 0),
                "high": by_level.get("high", 0),
                "medium": by_level.get("medium", 0),
                "low": by_level.get("low", 0),
                "info": by_level.get("info", 0),
            },
            "by_category": dict(by_category),
            "files_scanned": report.files_scanned,
            "lines_scanned": report.lines_scanned,
            "duration_ms": round(report.duration_ms, 2),
            "top_findings": [
                {
                    "title": f.title,
                    "level": f.level.value,
                    "category": f.category,
                    "file": f.file_path,
                    "line": f.line_number,
                    "cve": f.cve,
                    "cvss": f.cvss_score,
                    "remediation": f.remediation,
                }
                for f in sorted(report.findings, key=lambda x: (x.level.value, x.cvss_score), reverse=True)[:20]
            ],
        }

    def get_scan_history(self, limit: int = 20) -> List[Dict]:
        return [
            {
                "scan_id": r.scan_id,
                "type": r.scan_type.value,
                "target": r.target,
                "score": r.score,
                "findings": len(r.findings),
                "duration_ms": round(r.duration_ms, 2),
                "timestamp": datetime.fromtimestamp(r.completed_at or r.started_at).isoformat(),
            }
            for r in reversed(self._scan_history[-limit:])
        ]

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        """统一执行入口 — 根据action路由到对应业务方法"""
        _ = self.trace("execute")
        metrics_collector.counter("security_scanner_ops_total", labels={"action": action})
        params = params or {}
        actions = {
            "scan": self.scan,
            "get_scan_history": self.get_scan_history,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        base.update(
            {
                "scans_completed": len(self._scan_history),
                "code_rules": len(self._code_rules),
                "config_rules": len(self._config_rules),
                "cve_database": len(self._known_cve),
                "latest_score": self._scan_history[-1].score if self._scan_history else None,
            }
        )
        return base

    def initialize(self) -> None:
        """初始化Unknown"""
        try:
            self.status = ModuleStatus.RUNNING
            self.stats.start_time = datetime.now()
            self.record_metrics("unknown.init", 1)
            self.audit("initialized", "Unknown初始化完成")
            self.audit("initialized", "Unknown初始化完成")
            self.info("Unknown初始化完成")
            self.record_metrics("unknown.init", 1)
        except Exception as e:
            self._logger.error(f"unknown初始化失败: {e}")
            self.record_metrics("unknown.init.error", 1)
            raise

    def shutdown(self) -> None:
        audit_logger.log(
            action="module_shutdown", resource="security_scanner", details=f"关闭，{len(self._scan_history)} 次扫描记录"
        )

    def shutdown(self) -> None:
        """优雅关闭"""
        self.status = ModuleStatus.STOPPED
        self.audit("shutdown", "unknown已关闭")
        self.info("unknown已优雅关闭")

module_class = SecurityScanner
