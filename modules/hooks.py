"""
Grade: A
AUTO-EVO-AI V0.1 — Hooks拦截器系统
PreExec/PostExec 两阶段钩子，危险命令拦截/锁定目录/审计日志
"""
from __future__ import annotations

__module_meta__ = {
    "id": "hooks",
    "name": "Hooks拦截器",
    "version": "V0.1",
    "group": "system",
    "grade": "A",
    "description": "PreExec/PostExec 两阶段钩子，危险命令拦截/锁定目录/审计日志",
    "tags": ["hooks", "security", "audit"],
}

import json, time, re, os, threading
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass, field, asdict
from modules._base import Result
from modules._base.enterprise_module import EnterpriseModule


# 默认危险命令列表
DANGEROUS_COMMANDS = [
    r'rm\s+-rf\s+/', r'rm\s+-rf\s+\*', r'rm\s+-rf\s+~',
    r'mkfs\.', r'dd\s+if=', r'format\s+[cdefgh]:',
    r'chmod\s+-R\s+777\s+/', r'>\s+/dev/sda',
    r':\(\)\s*\{',  # fork bomb
    r'wget\s+.*\|\s*bash', r'curl\s+.*\|\s*bash',
    r'sudo\s+rm', r'shutdown', r'reboot', r'init\s+0',
    r'drop\s+table', r'drop\s+database', r'truncate\s+table',
]

PROTECTED_DIRS = [
    "/etc", "/usr", "/boot", "/sys", "/proc",
    "/.evo_data", "/.git", "/venv", "/node_modules",
]


@dataclass
class HookRule:
    id: str = ""
    name: str = ""
    type: str = "pre_exec"  # pre_exec / post_exec
    pattern: str = ""       # 正则匹配
    action: str = "block"   # block / warn / allow / audit
    enabled: bool = True
    description: str = ""
    created_at: str = ""


@dataclass
class AuditLog:
    timestamp: float = 0
    rule_id: str = ""
    rule_name: str = ""
    command: str = ""
    action_taken: str = ""  # blocked / warned / allowed
    result: str = ""
    source: str = ""


class HooksEngine:
    """Hooks拦截器引擎"""

    def __init__(self):
        self._rules: list[HookRule] = []
        self._audit_logs: list[AuditLog] = []
        self._post_hooks: list[Callable] = []
        self._lock = threading.Lock()
        self._db_path = Path(__file__).parent.parent / ".evo_data" / "hooks.json"
        self._load_defaults()
        self._load()

    def _load_defaults(self):
        now = datetime.now().isoformat()
        self._rules = [
            HookRule(id="hook_1", name="危险命令拦截", type="pre_exec",
                     pattern="|".join(DANGEROUS_COMMANDS), action="block",
                     description="拦截 rm -rf /、dd、mkfs 等危险命令", created_at=now),
            HookRule(id="hook_2", name="受保护目录", type="pre_exec",
                     pattern="|".join(re.escape(d) for d in PROTECTED_DIRS),
                     action="warn",
                     description="警告对系统目录的操作", created_at=now),
            HookRule(id="hook_3", name="所有命令审计", type="post_exec",
                     pattern=".*", action="audit",
                     description="记录所有执行命令到审计日志", created_at=now),
        ]

    def _load(self):
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text(encoding="utf-8"))
                self._rules = [HookRule(**r) for r in data.get("rules", [])]
                self._audit_logs = [AuditLog(**r) for r in data.get("logs", [])[-1000:]]
            except Exception:
                pass

    def _save(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path.write_text(
            json.dumps({
                "rules": [asdict(r) for r in self._rules],
                "logs": [asdict(r) for r in self._audit_logs[-1000:]],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_rule(self, name: str, pattern: str, action: str = "block",
                 rule_type: str = "pre_exec", description: str = "") -> HookRule:
        rule = HookRule(
            id=f"hook_{int(time.time())}",
            name=name, type=rule_type, pattern=pattern,
            action=action, description=description,
            created_at=datetime.now().isoformat(),
        )
        with self._lock:
            self._rules.append(rule)
            self._save()
        return rule

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        with self._lock:
            for r in self._rules:
                if r.id == rule_id:
                    for k, v in kwargs.items():
                        if hasattr(r, k):
                            setattr(r, k, v)
                    self._save()
                    return True
            return False

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.id != rule_id]
            if len(self._rules) < before:
                self._save()
                return True
            return False

    def get_rules(self) -> list[dict]:
        return [asdict(r) for r in self._rules]

    def check_pre_exec(self, command: str) -> dict:
        """检查命令是否允许执行 (PreExec Hook)"""
        with self._lock:
            for rule in self._rules:
                if not rule.enabled or rule.type != "pre_exec":
                    continue
                if re.search(rule.pattern, command, re.IGNORECASE):
                    log = AuditLog(
                        timestamp=time.time(),
                        rule_id=rule.id,
                        rule_name=rule.name,
                        command=command[:200],
                        action_taken=rule.action,
                        source="pre_exec",
                    )
                    self._audit_logs.append(log)
                    self._save()

                    if rule.action == "block":
                        return {
                            "allowed": False,
                            "rule": rule.name,
                            "reason": f"被规则 '{rule.name}' 拦截: {rule.description}",
                        }
                    elif rule.action == "warn":
                        return {
                            "allowed": True,
                            "warn": True,
                            "rule": rule.name,
                            "reason": f"⚠️ {rule.description}",
                        }
            return {"allowed": True}

    def post_exec(self, command: str, result: str):
        """命令执行后回调 (PostExec Hook)"""
        with self._lock:
            for rule in self._rules:
                if not rule.enabled or rule.type != "post_exec":
                    continue
                if re.search(rule.pattern, command, re.IGNORECASE):
                    log = AuditLog(
                        timestamp=time.time(),
                        rule_id=rule.id,
                        rule_name=rule.name,
                        command=command[:200],
                        action_taken="audit" if rule.action == "audit" else "logged",
                        result=result[:200],
                        source="post_exec",
                    )
                    self._audit_logs.append(log)

            # 截断日志
            if len(self._audit_logs) > 2000:
                self._audit_logs = self._audit_logs[-1000:]
            self._save()

    def register_post_hook(self, hook_fn: Callable):
        self._post_hooks.append(hook_fn)

    def get_audit_logs(self, limit: int = 200) -> list[dict]:
        return [asdict(l) for l in self._audit_logs[-limit:]]

    def get_status(self) -> dict:
        return {
            "rules_count": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules if r.enabled),
            "logs_count": len(self._audit_logs),
            "blocked_count": sum(1 for l in self._audit_logs if l.action_taken == "blocked"),
        }


_hooks_engine = HooksEngine()


def get_hooks() -> HooksEngine:
    return _hooks_engine


class HooksModule(EnterpriseModule):
    def __init__(self):
        super().__init__(module_id="hooks", name="Hooks拦截器")

    async def initialize(self):
        self._status = "ready"
        return Result(success=True, message="Hooks Engine 就绪")

    async def execute(self, action: str, **params) -> Result:
        h = get_hooks()
        try:
            if action == "check":
                r = h.check_pre_exec(params.get("command", ""))
                return Result(success=True, data=r)
            elif action == "rules":
                return Result(success=True, data={"rules": h.get_rules()})
            elif action == "add_rule":
                r = h.add_rule(
                    params.get("name", ""), params.get("pattern", ""),
                    params.get("action", "block"), params.get("type", "pre_exec"),
                    params.get("description", ""),
                )
                return Result(success=True, data=asdict(r))
            elif action == "update_rule":
                ok = h.update_rule(params.get("rule_id", ""), **params.get("updates", {}))
                return Result(success=True, data={"updated": ok})
            elif action == "delete_rule":
                ok = h.delete_rule(params.get("rule_id", ""))
                return Result(success=True, data={"deleted": ok})
            elif action == "logs":
                return Result(success=True, data={"logs": h.get_audit_logs()})
            elif action == "status":
                return Result(success=True, data=h.get_status())
            return Result(success=False, error=f"未知动作: {action}")
        except Exception as e:
            return Result(success=False, error=str(e))

    async def health_check(self):
        return Result(success=True, data={"status": self._status})
