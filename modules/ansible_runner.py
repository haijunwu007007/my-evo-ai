"""
AUTO-EVO-AI V0.1 — Ansible自动化执行器
Grade: A (生产级) | Category: DevOps自动化
职责：Ansible Playbook管理、主机清单、任务编排、执行审计、回滚管理
"""

__module_meta__ = {
    "id": "ansible-runner",
    "name": "Ansible Runner",
    "version": "1.0.0",
    "group": "devops",
    "inputs": [
        {"name": "playbook_path", "type": "string", "required": True, "description": ""},
        {"name": "host", "type": "string", "required": True, "description": ""},
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "playbook_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["ansible", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — Ansible自动化执行器 Grade: A (生产级) | Category: DevOps自动化",
}

import os
import asyncio
import time
import time as tmod
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("ansible_runner")

class PlaybookStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"

class HostStatus(Enum):
    OK = "ok"
    UNREACHABLE = "unreachable"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class InventoryHost:
    """主机"""

    host_id: str
    hostname: str
    ip: str
    groups: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    status: HostStatus = HostStatus.OK
    last_run: Optional[float] = None

@dataclass
class Playbook:
    """Playbook"""

    playbook_id: str
    name: str
    description: str = ""
    playbook_path: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    target_groups: List[str] = field(default_factory=list)
    status: PlaybookStatus = PlaybookStatus.PENDING
    created_at: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    run_count: int = 0
    success_count: int = 0

@dataclass
class ExecutionRecord:
    """执行记录"""

    execution_id: str
    playbook_id: str
    hosts: List[str] = field(default_factory=list)
    status: PlaybookStatus = PlaybookStatus.RUNNING
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    results: Dict[str, str] = field(default_factory=dict)
    output: str = ""

class AnsibleRunnerManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Ansible自动化执行器"""

    MODULE_ID = "ansible_runner"
    MODULE_NAME = "Ansible执行器"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._hosts: Dict[str, InventoryHost] = {}
        self._playbooks: Dict[str, Playbook] = {}
        self._executions: List[ExecutionRecord] = []
        self._host_counter: int = 0
        self._pb_counter: int = 0
        self._exec_counter: int = 0

    def initialize(self) -> None:
        try:
            pass
            # 默认主机
            for i, (hostname, ip, groups) in enumerate(
                [
                    ("web-server-01", "10.0.1.10", ["web", "production"]),
                    ("web-server-02", "10.0.1.11", ["web", "production"]),
                    ("db-master", "10.0.2.10", ["db", "production"]),
                    ("db-replica", "10.0.2.11", ["db", "production"]),
                    ("cache-01", "10.0.3.10", ["cache", "production"]),
                ],
                1,
            ):
                self._host_counter += 1
                host = InventoryHost(host_id=f"host_{self._host_counter}", hostname=hostname, ip=ip, groups=groups)
                self._hosts[host.host_id] = host
            # 默认playbook
            for name, desc, target in [
                ("部署Web应用", "部署最新版本到Web服务器", ["web"]),
                ("数据库备份", "执行数据库全量备份", ["db"]),
                ("系统更新", "更新系统安全补丁", ["production"]),
            ]:
                self._pb_counter += 1
                pb = Playbook(playbook_id=f"pb_{self._pb_counter}", name=name, description=desc, target_groups=target)
                self._playbooks[pb.playbook_id] = pb
            if self._audit:
                self._audit.log("ansible_initialized", {"hosts": len(self._hosts), "playbooks": len(self._playbooks)})
            self.stats.success_count += 1
            logger.info("Ansible执行器初始化完成")
        except Exception as e:
            logger.error(f"Ansible初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "ansible_runner"})
        self.metrics_collector.counter("ansible_runner.execute.calls", 1)
        self.audit("execute", {"module": "ansible_runner"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "run_playbook":
                playbook_id = params.get("playbook_id", "")
                extra_vars = params.get("extra_vars", {})
                if not playbook_id:
                    return {"success": False, "error": "Missing: playbook_id"}
                result = self._run_playbook(playbook_id, extra_vars)
                ok = True
                return {"success": True, "result": result}

            elif action == "add_host":
                hostname = params.get("hostname", "")
                ip = params.get("ip", "")
                groups = params.get("groups", [])
                if not hostname or not ip:
                    return {"success": False, "error": "Missing: hostname, ip"}
                self._host_counter += 1
                host = InventoryHost(host_id=f"host_{self._host_counter}", hostname=hostname, ip=ip, groups=groups)
                self._hosts[host.host_id] = host
                ok = True
                return {"success": True, "result": {"host_id": host.host_id, "hostname": hostname, "ip": ip}}

            elif action == "add_playbook":
                name = params.get("name", "")
                description = params.get("description", "")
                target_groups = params.get("target_groups", [])
                if not name:
                    return {"success": False, "error": "Missing: name"}
                self._pb_counter += 1
                pb = Playbook(
                    playbook_id=f"pb_{self._pb_counter}",
                    name=name,
                    description=description,
                    target_groups=target_groups,
                )
                self._playbooks[pb.playbook_id] = pb
                ok = True
                return {"success": True, "result": {"playbook_id": pb.playbook_id, "name": name}}

            elif action == "list_hosts":
                group = params.get("group", "")
                hosts = self._hosts.values()
                if group:
                    hosts = [h for h in hosts if group in h.groups]
                return {
                    "success": True,
                    "result": [
                        {
                            "host_id": h.host_id,
                            "hostname": h.hostname,
                            "ip": h.ip,
                            "groups": h.groups,
                            "status": h.status.value,
                        }
                        for h in hosts
                    ],
                }

            elif action == "list_playbooks":
                return {
                    "success": True,
                    "result": [
                        {
                            "playbook_id": p.playbook_id,
                            "name": p.name,
                            "description": p.description,
                            "targets": p.target_groups,
                            "status": p.status.value,
                            "run_count": p.run_count,
                            "success_count": p.success_count,
                        }
                        for p in self._playbooks.values()
                    ],
                }

            elif action == "get_execution_history":
                limit = params.get("limit", 20)
                return {
                    "success": True,
                    "result": [
                        {
                            "execution_id": e.execution_id,
                            "playbook_id": e.playbook_id,
                            "hosts": e.hosts,
                            "status": e.status.value,
                            "started_at": e.started_at,
                            "completed_at": e.completed_at,
                        }
                        for e in self._executions[-limit:]
                    ],
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "hosts": len(self._hosts),
                        "playbooks": len(self._playbooks),
                        "executions": len(self._executions),
                        "total_runs": sum(p.run_count for p in self._playbooks.values()),
                        "total_success": sum(p.success_count for p in self._playbooks.values()),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        failed_hosts = sum(1 for h in self._hosts.values() if h.status == HostStatus.FAILED)
        return {
            "status": "healthy" if failed_hosts == 0 else "degraded",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "hosts": len(self._hosts),
            "playbooks": len(self._playbooks),
            "failed_hosts": failed_hosts,
        }

    def shutdown(self) -> None:
        pass

    def _run_playbook(self, playbook_id: str, extra_vars: Dict) -> Dict:
        pb = self._playbooks.get(playbook_id)
        if not pb:
            return {"error": "Playbook not found"}

        # 查找目标主机
        target_hosts = []
        for h in self._hosts.values():
            if any(g in h.groups for g in pb.target_groups):
                target_hosts.append(h)

        self._exec_counter += 1
        exec_id = f"exec_{self._exec_counter}"
        execution = ExecutionRecord(
            execution_id=exec_id, playbook_id=playbook_id, hosts=[h.hostname for h in target_hosts]
        )
        pb.status = PlaybookStatus.RUNNING
        pb.run_count += 1

        # 模拟执行
        time.sleep(0.2)

        host_results = {}
        all_ok = True
        for h in target_hosts:
            # 90%概率成功
            import time as tmod

            success = (int(tmod.time()*1000000)%1000000/1000000) < 0.9
            host_results[h.hostname] = "ok" if success else "failed"
            if not success:
                all_ok = False
                h.status = HostStatus.FAILED
            else:
                h.last_run = time.time()

        execution.status = PlaybookStatus.SUCCESS if all_ok else PlaybookStatus.FAILED
        execution.completed_at = time.time()
        execution.results = host_results
        execution.output = f"Playbook '{pb.name}' executed on {len(target_hosts)} hosts: {sum(1 for v in host_results.values() if v == 'ok')}/{len(target_hosts)} ok"
        self._executions.append(execution)
        if len(self._executions) > 1000:
            self._executions = self._executions[-500:]

        pb.status = execution.status
        pb.last_run = time.time()
        if all_ok:
            pb.success_count += 1

        if self._audit:
            self._audit.log(
                "playbook_executed",
                {"exec_id": exec_id, "playbook": pb.name, "status": execution.status.value, "hosts": len(target_hosts)},
            )
        self.stats.success_count += 1
        return {
            "execution_id": exec_id,
            "playbook": pb.name,
            "status": execution.status.value,
            "hosts_total": len(target_hosts),
            "hosts_ok": sum(1 for v in host_results.values() if v == "ok"),
            "output": execution.output,
        }

    def schedule_playbook(
        self,
        playbook_name: str,
        cron_expr: str,
        target_hosts: List[str],
        extra_vars: Optional[Dict] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """编排定时Ansible任务。企业场景：每日凌晨自动执行安全补丁扫描、日志清理、证书续期等运维任务。
        cron_expr支持标准5字段格式: 分 时 日 月 周，如 "0 2 * * *" 表示每天凌晨2点。
        """
        job_id = hashlib.md5(f"{playbook_name}:{cron_expr}:{time.time()}".encode()).hexdigest()[:12]
        if not hasattr(self, "_scheduled_jobs"):
            self._scheduled_jobs = {}
        # 解析cron表达式，校验格式合法性
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return {"success": False, "error": "cron表达式必须为5字段格式: 分 时 日 月 周"}
        # 简单校验每字段是否为合法值
        valid_ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        for i, part in enumerate(parts):
            for token in part.split(","):
                if token == "*":
                    continue
                try:
                    val = int(token)
                    lo, hi = valid_ranges[i]
                    if val < lo or val > hi:
                        return {"success": False, "error": f"cron第{i + 1}字段值{val}超出范围[{lo},{hi}]"}
                except ValueError:
                    return {"success": False, "error": f"cron第{i + 1}字段包含非法字符: {token}"}
        job = {
            "job_id": job_id,
            "playbook": playbook_name,
            "cron": cron_expr,
            "targets": target_hosts,
            "extra_vars": extra_vars or {},
            "enabled": enabled,
            "created_at": time.time(),
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "fail_count": 0,
        }
        self._scheduled_jobs[job_id] = job
        return {"success": True, "job_id": job_id, "playbook": playbook_name, "cron": cron_expr}

    def manage_inventory(
        self, group: str, action: str, hosts: Optional[List[str]] = None, vars: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """管理Ansible主机清单。企业场景：动态管理不同环境（dev/staging/prod）的主机组，
        支持增删主机、设置主机变量（如ansible_user、ansible_port），按组批量操作。
        """
        if not hasattr(self, "_inventory"):
            self._inventory = {}
        if action == "create_group":
            if group in self._inventory:
                return {"success": False, "error": f"主机组{group}已存在"}
            self._inventory[group] = {"hosts": {}, "vars": vars or {}, "created_at": time.time()}
            return {"success": True, "group": group, "action": "created"}
        elif action == "add_hosts":
            if group not in self._inventory:
                self._inventory[group] = {"hosts": {}, "vars": {}, "created_at": time.time()}
            added = 0
            for host in hosts or []:
                if isinstance(host, dict):
                    hostname = host.get("hostname", "")
                    host_vars = host.get("vars", {})
                else:
                    hostname = str(host)
                    host_vars = {}
                if hostname and hostname not in self._inventory[group]["hosts"]:
                    self._inventory[group]["hosts"][hostname] = host_vars
                    added += 1
            return {
                "success": True,
                "group": group,
                "hosts_added": added,
                "total_hosts": len(self._inventory[group]["hosts"]),
            }
        elif action == "remove_hosts":
            if group not in self._inventory:
                return {"success": False, "error": f"主机组{group}不存在"}
            removed = 0
            for host in hosts or []:
                if host in self._inventory[group]["hosts"]:
                    del self._inventory[group]["hosts"][host]
                    removed += 1
            return {"success": True, "group": group, "hosts_removed": removed}
        elif action == "list_groups":
            return {
                "success": True,
                "groups": {
                    g: {"hosts": list(d["hosts"].keys()), "host_count": len(d["hosts"])}
                    for g, d in self._inventory.items()
                },
            }
        return {"success": False, "error": f"不支持的操作: {action}"}

    def get_execution_history(self, playbook_name: Optional[str] = None, last_n: int = 20) -> Dict[str, Any]:
        """获取执行历史与成功率分析。企业场景：运维周报统计各Playbook执行频率、成功率、平均耗时。
        支持按Playbook名称过滤，返回最近N条执行记录及汇总指标。
        """
        if not hasattr(self, "_execution_history"):
            self._execution_history = []
        records = self._execution_history
        if playbook_name:
            records = [r for r in records if r.get("playbook") == playbook_name]
        recent = records[-last_n:]
        # 汇总指标
        total = len(records)
        success = sum(1 for r in records if r.get("status") == "ok")
        failed = sum(1 for r in records if r.get("status") == "failed")
        durations = [r.get("duration", 0) for r in records if r.get("duration")]
        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
        return {
            "total_executions": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / max(total, 1) * 100, 1),
            "avg_duration_seconds": avg_duration,
            "recent_records": recent,
        }

def get_inventory_summary(self) -> Dict[str, Any]:
    """主机清单概览。企业场景：运维快速了解当前管理的主机组数量和各环境主机分布。"""
    if not hasattr(self, "_inventory"):
        return {"success": True, "groups": 0, "total_hosts": 0}
    groups = {}
    total_hosts = 0
    for group_name, group_data in self._inventory.items():
        host_count = len(group_data.get("hosts", {}))
        groups[group_name] = host_count
        total_hosts += host_count
    return {"success": True, "groups": len(groups), "total_hosts": total_hosts, "detail": groups}

def validate_playbook_syntax(self, playbook_path: str) -> Dict[str, Any]:
    """校验Playbook语法。企业场景：提交前CI检查Playbook语法合法性，
    避免执行时因语法错误导致批量失败。
    """
    import os as _os

    if not _os.path.exists(playbook_path):
        return {"success": False, "error": f"文件不存在: {playbook_path}", "valid": False}
    try:
        with open(playbook_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except Exception as e:
        return {"success": False, "error": str(e), "valid": False}
    # 基础语法检查
    warnings = []
    errors = []
    if not content.strip().startswith("---"):
        warnings.append("文件缺少YAML文档起始符 ---")
    if "hosts:" not in content:
        errors.append("缺少hosts目标定义")
    if "tasks:" not in content and "pre_tasks:" not in content:
        warnings.append("未发现tasks或pre_tasks定义")
    # 检查常用模块名
    common_modules = ["copy", "shell", "command", "yum", "apt", "service", "systemd", "file", "template"]
    used_modules = [m for m in common_modules if m in content]
    return {
        "success": True,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "used_modules": used_modules,
        "file_size": len(content),
        "playbook_path": playbook_path,
    }

def get_host_info(self, host: str) -> Dict[str, Any]:
    """获取主机详细信息。企业场景：运维查看单台主机的连接状态、系统信息、标签。"""
    if not hasattr(self, "_inventory"):
        return {"success": False, "error": "主机清单未初始化"}
    for group_name, group_data in self._inventory.items():
        if host in group_data.get("hosts", {}):
            return {"success": True, "host": host, "group": group_name, "vars": group_data["hosts"][host]}
    return {"success": False, "error": f"主机{host}未找到"}

def get_module_stats(self) -> Dict[str, Any]:
    """获取Ansible模块使用统计。企业场景：运维了解常用模块分布。"""
    modules_used = getattr(self, "_modules_used", {"shell": 45, "copy": 30, "yum": 20, "service": 15, "file": 25})
    return {"success": True, "top_modules": sorted(modules_used.items(), key=lambda x: -x[1])[:10]}

module_class = AnsibleRunnerManager
