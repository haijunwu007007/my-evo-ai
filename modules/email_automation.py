# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI V0.1 - 邮件自动化（A级生产实现）
============================================
模块ID: email-automation
功能：企业级邮件收发 — SMTP发送、IMAP收信、模板引擎、定时发送、附件管理。

核心能力：
  1. SMTP发送 — 支持HTML/纯文本/附件/抄送密送
  2. IMAP收信 — 读取收件箱、搜索过滤、标记已读
  3. 邮件模板 — 变量替换、HTML模板渲染
  4. 定时发送 — 指定时间发送、周期性报告邮件
  5. 附件管理 — 文件附加、附件提取保存
  6. 发送队列 — 异步发送、失败重试、速率控制
"""

__module_meta__ = {
    "id": "email-automation",
    "name": "Email Automation",
    "version": "V0.1",
    "group": "messaging",
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
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "success", "type": "bool", "description": "是否成功"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "email", "engine", "config"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - 邮件自动化（A级生产实现） ============================================",
}

import time
import asyncio
import logging
import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate, parseaddr
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules._base.enterprise_module import (
    EnterpriseModule,
    ModuleStatus,
    HealthReport,
    CircuitBreakerMixin,
    RateLimiterMixin,
    Result,
)
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.registry import get_registry

logger = logging.getLogger("evo.email-automation")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

class EmailPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

@dataclass
class EmailMessage:
    """邮件消息"""

    msg_id: str = ""
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    cc_addrs: List[str] = field(default_factory=list)
    bcc_addrs: List[str] = field(default_factory=list)
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    attachments: List[str] = field(default_factory=list)
    priority: EmailPriority = EmailPriority.NORMAL
    template: str = ""
    template_vars: Dict[str, str] = field(default_factory=dict)
    send_at: str = ""  # 定时发送时间（ISO格式）
    status: str = "draft"  # draft/queued/sent/failed
    sent_at: str = ""
    error: str = ""
    created_at: str = ""
    retry_count: int = 0
    msg_uid: str = ""  # IMAP UID
    folder: str = "INBOX"

def __post_init__(self):
    if not self.msg_id:
        self.msg_id = f"E-{int(time.time() * 1000) % 10000000}"
    if not self.created_at:
        self.created_at = datetime.now().isoformat()

@dataclass
class EmailConfig:
    """邮件服务器配置"""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = True
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    username: str = ""
    password: str = ""
    from_name: str = "AUTO-EVO-AI"
    from_addr: str = ""
    reply_to: str = ""
    max_retries: int = 3
    send_delay: float = 2.0  # 发送间隔（秒）
    max_per_minute: int = 30

class EmailTemplateEngine(object):
    """邮件模板引擎"""

    def __init__(self):
        self._templates: Dict[str, Dict[str, str]] = {
            "system_report": {
                "subject": "【系统报告】{title} - {date}",
                "body_html": """<html><body>
<h2>系统报告: {title}</h2>
<p>报告时间: {date}</p>
<table border="1" cellpadding="8">{content}</table>
<p>本邮件由 AUTO-EVO-AI 自动生成</p>
</body></html>""",
                "body_text": "系统报告: {title}\n报告时间: {date}\n{content}",
            },
            "alert_notification": {
                "subject": "【告警】{module} - {alert_type}",
                "body_html": """<html><body>
<h2 style="color:red;">⚠️ {module} 告警</h2>
<p><b>类型:</b> {alert_type}</p>
<p><b>详情:</b> {detail}</p>
<p><b>时间:</b> {time}</p>
<p><b>严重程度:</b> {severity}</p>
</body></html>""",
                "body_text": "告警: {module} - {alert_type}\n详情: {detail}\n时间: {time}",
            },
            "task_result": {
                "subject": "【任务完成】{task_name}",
                "body_html": """<html><body>
<h2>任务完成通知</h2>
<p><b>任务:</b> {task_name}</p>
<p><b>状态:</b> {status}</p>
<p><b>耗时:</b> {duration}ms</p>
<pre>{result}</pre>
</body></html>""",
                "body_text": "任务完成: {task_name}\n状态: {status}\n{result}",
            },
        }

    def render(self, template_name: str, variables: Dict[str, str]) -> Tuple[str, str, str]:
        """渲染模板，返回 (subject, body_html, body_text)"""
        tmpl = self._templates.get(template_name)
        if not tmpl:
            return f"[模板: {template_name}]", "", variables.get("body", "")
        now = datetime.now()
        variables.setdefault("date", now.strftime("%Y-%m-%d"))
        variables.setdefault("time", now.strftime("%Y-%m-%d %H:%M:%S"))
        subject = tmpl["subject"].format(**variables)
        body_html = tmpl["body_html"].format(**variables) if tmpl.get("body_html") else ""
        body_text = tmpl["body_text"].format(**variables) if tmpl.get("body_text") else ""
        return subject, body_html, body_text

    def list_templates(self) -> Dict[str, str]:
        return {name: t["subject"] for name, t in self._templates.items()}

    def add_template(self, name: str, subject: str, body_html: str = "", body_text: str = ""):
        self._templates[name] = {"subject": subject, "body_html": body_html, "body_text": body_text}

class EmailAutomation(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    """邮件自动化模块"""

    MODULE_ID = "email-automation"
    MODULE_NAME = "邮件自动化"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        self._circuits = {}
        self._buckets = {}
        self._windows = {}

        email_cfg = self.config.get("email", {})
        self.email_config = EmailConfig(
            **{k: email_cfg.get(k, getattr(EmailConfig(), k)) for k in EmailConfig.__dataclass_fields__}
        )
        self.template_engine = EmailTemplateEngine()
        self._send_queue: deque = deque(maxlen=500)
        self._sent_history: deque = deque(maxlen=1000)
        self._send_times: deque = deque(maxlen=200)
        self._bg_sender: Optional[asyncio.Task] = None
        self._bg_checker: Optional[asyncio.Task] = None
        self.check_interval = self.config.get("check_interval", 300)

    def initialize(self) -> None:
        self.info("初始化邮件自动化...")
        self.record_metrics("email-automation.init", 1)
        self._setup_rate_limit(rate=20, burst=40)

        # 测试SMTP连接
        if self.email_config.smtp_host and self.email_config.username:
            connected = self._test_smtp_connection()
            if connected:
                self.info("SMTP连接测试成功")
            else:
                self.warning("SMTP连接测试失败，将使用队列模式")

        try:
            self._bg_sender = asyncio.create_task(self._send_loop())
            self._bg_checker = asyncio.create_task(self._check_loop())
        except RuntimeError:
            self._bg_sender = None
            self._bg_checker = None
            self.warning("无运行中的事件循环，跳过后台任务创建")
        self.status = ModuleStatus.RUNNING
        self.stats.start_time = datetime.now()
        self.audit("initialize", f"smtp={self.email_config.smtp_host or '未配置'}")
        self.info("邮件自动化就绪")

    async def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        _ = self.trace("execute")
        metrics_collector.counter("email_automation_ops_total", labels={"action": action})
        params = params or {}
        return self._safe_execute(action, params, self._dispatch)

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "email-automation"},
        )

    def shutdown(self) -> None:
        self.info("关闭邮件自动化...")
        if self._bg_sender:
            self._bg_sender.cancel()
        if self._bg_checker:
            self._bg_checker.cancel()
        # 刷新队列
        remaining = len(self._send_queue)
        if remaining:
            self.info(f"队列中剩余 {remaining} 封邮件待发送")
        self.status = ModuleStatus.STOPPED

    # ── SMTP核心 ──

    def _test_smtp_connection(self) -> bool:
        """测试SMTP连接"""
        try:
            if self.email_config.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.email_config.smtp_host, self.email_config.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port, timeout=10)
                if self.email_config.smtp_use_tls:
                    server.starttls()
            server.login(self.email_config.username, self.email_config.password)
            server.quit()
            return True
        except Exception as e:
            logger.warning(f"SMTP连接测试失败: {e}")
            return False

    def _build_mime(self, msg: EmailMessage) -> MIMEMultipart:
        """构建MIME消息"""
        mime = MIMEMultipart("alternative")
        mime["Subject"] = msg.subject
        mime["From"] = formataddr((self.email_config.from_name, self.email_config.from_addr or msg.from_addr))
        mime["To"] = ", ".join(msg.to_addrs)
        if msg.cc_addrs:
            mime["Cc"] = ", ".join(msg.cc_addrs)
        mime["Date"] = formatdate(localtime=True)
        mime["X-Priority"] = {"high": "1", "normal": "3", "low": "5"}.get(msg.priority.value, "3")

        # 正文
        if msg.body_html:
            mime.attach(MIMEText(msg.body_html, "html", "utf-8"))
        if msg.body_text:
            mime.attach(MIMEText(msg.body_text, "plain", "utf-8"))

        # 附件
        for filepath in msg.attachments:
            if os.path.exists(filepath):
                filename = os.path.basename(filepath)
                try:
                    with open(filepath, "rb") as f:
                        part = MIMEApplication(f.read(), Name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    mime.attach(part)
                except Exception as e:
                    self.warning(f"添加附件失败 {filepath}: {e}")
        return mime

    def _do_send_smtp(self, mime: MIMEMultipart, to_addrs: List[str]) -> bool:
        """通过SMTP发送"""
        try:
            if self.email_config.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.email_config.smtp_host, self.email_config.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port, timeout=15)
                if self.email_config.smtp_use_tls:
                    server.starttls()
            server.login(self.email_config.username, self.email_config.password)
            all_recipients = list(set(to_addrs))
            server.sendmail(self.email_config.from_addr, all_recipients, mime.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"SMTP发送失败: {e}")
            return False

    # ── IMAP收信 ──

    def _imap_connect(self) -> Optional[imaplib.IMAP4_SSL]:
        """连接IMAP服务器"""
        try:
            if self.email_config.imap_use_ssl:
                conn = imaplib.IMAP4_SSL(self.email_config.imap_host, self.email_config.imap_port, timeout=15)
            else:
                conn = imaplib.IMAP4(self.email_config.imap_host, self.email_config.imap_port, timeout=15)
            conn.login(self.email_config.username, self.email_config.password)
            return conn
        except Exception as e:
            logger.error(f"IMAP连接失败: {e}")
            return None

    def _fetch_emails(self, folder: str = "INBOX", criteria: str = "UNSEEN", limit: int = 20) -> List[Dict[str, Any]]:
        """获取邮件列表"""
        conn = self._imap_connect()
        if not conn:
            return []
        try:
            conn.select(folder, readonly=True)
            status, data = conn.search(None, criteria)
            if status != "OK":
                return []

            email_ids = data[0].split()
            email_ids = email_ids[-limit:]  # 取最新的N封
            results = []

            for eid in email_ids:
                status, msg_data = conn.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                parsed = email.message_from_bytes(raw)

                body_text = ""
                body_html = ""
                if parsed.is_multipart():
                    for part in parsed.walk():
                        ct = part.get_content_type()
                        if ct == "text/plain":
                            body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        elif ct == "text/html":
                            body_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                else:
                    body_text = (
                        parsed.get_payload(decode=True).decode("utf-8", errors="ignore") if parsed.get_payload() else ""
                    )

                results.append(
                    {
                        "uid": eid.decode() if isinstance(eid, bytes) else str(eid),
                        "from": parsed.get("From", ""),
                        "to": parsed.get("To", ""),
                        "subject": parsed.get("Subject", ""),
                        "date": parsed.get("Date", ""),
                        "body_text": body_text[:500],
                        "body_html": body_html[:500],
                        "has_attachments": any(
                            part.get_content_disposition() == "attachment"
                            for part in parsed.walk()
                            if parsed.is_multipart()
                        ),
                    }
                )
            conn.logout()
            return results
        except Exception as e:
            logger.error(f"获取邮件失败: {e}")
            try:
                conn.logout()
            except Exception:
                pass
            return []

    # ── 动作分发 ──

    def _dispatch(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "")
        handlers = {
            "send": self._action_send,
            "send_template": self._action_send_template,
            "schedule": self._action_schedule,
            "fetch": self._action_fetch,
            "get_history": self._action_history,
            "get_queue": self._action_queue,
            "get_templates": self._action_templates,
            "test_connection": self._action_test_conn,
            "get_stats": self._action_stats,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"未知动作: {action}", "available": list(handlers.keys())}
        return handler(params)

    def _action_send(self, params: Dict) -> Dict:
        """发送邮件"""
        msg = EmailMessage(
            to_addrs=params.get("to", []),
            cc_addrs=params.get("cc", []),
            bcc_addrs=params.get("bcc", []),
            subject=params.get("subject", ""),
            body_text=params.get("body", ""),
            body_html=params.get("body_html", ""),
            attachments=params.get("attachments", []),
            priority=EmailPriority(params.get("priority", "normal")),
            from_addr=params.get("from_addr", self.email_config.from_addr),
        )
        if not msg.to_addrs and not msg.cc_addrs:
            return {"error": "缺少收件人"}
        if not msg.subject and not msg.body_text:
            return {"error": "缺少邮件内容"}

        return self._queue_and_send(msg)

    def _action_send_template(self, params: Dict) -> Dict:
        """模板发送"""
        tmpl_name = params.get("template", "")
        tmpl_vars = params.get("vars", {})
        subject, body_html, body_text = self.template_engine.render(tmpl_name, tmpl_vars)

        msg = EmailMessage(
            to_addrs=params.get("to", []),
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            template=tmpl_name,
            template_vars=tmpl_vars,
        )
        return self._queue_and_send(msg)

    def _action_schedule(self, params: Dict) -> Dict:
        """定时发送"""
        msg = EmailMessage(
            to_addrs=params.get("to", []),
            subject=params.get("subject", ""),
            body_text=params.get("body", ""),
            body_html=params.get("body_html", ""),
            send_at=params.get("send_at", ""),
        )
        if not msg.send_at:
            return {"error": "缺少 send_at 时间参数"}
        msg.status = "scheduled"
        self._send_queue.append(msg)
        return {"msg_id": msg.msg_id, "status": "scheduled", "send_at": msg.send_at}

    def _action_fetch(self, params: Dict) -> Dict:
        """收取邮件"""
        folder = params.get("folder", "INBOX")
        criteria = params.get("criteria", "UNSEEN")
        limit = params.get("limit", 20)
        emails = self._fetch_emails(folder, criteria, limit)
        self.record_metrics("emails_fetched", len(emails))
        return {"total": len(emails), "emails": emails}

    def _action_history(self, params: Dict) -> Dict:
        limit = params.get("limit", 50)
        return {
            "total": len(self._sent_history),
            "items": [
                {
                    "msg_id": m.msg_id,
                    "subject": m.subject,
                    "to": m.to_addrs,
                    "status": m.status,
                    "priority": m.priority.value,
                    "created_at": m.created_at,
                    "sent_at": m.sent_at,
                    "error": m.error,
                }
                for m in list(self._sent_history)[-limit:]
            ],
        }

    def _action_queue(self, params: Dict) -> Dict:
        return {
            "queue_size": len(self._send_queue),
            "items": [
                {
                    "msg_id": m.msg_id,
                    "subject": m.subject,
                    "status": m.status,
                    "send_at": m.send_at,
                    "retry_count": m.retry_count,
                }
                for m in list(self._send_queue)
            ],
        }

    def _action_templates(self, params: Dict) -> Dict:
        return {"templates": self.template_engine.list_templates()}

    def _action_test_conn(self, params: Dict) -> Dict:
        smtp = self._test_smtp_connection()
        return {"smtp": smtp, "imap": bool(self.email_config.imap_host)}

    def _action_stats(self, params: Dict) -> Dict:
        return {
            "sent": self.stats.request_count,
            "failed": self.stats.error_count,
            "queue": len(self._send_queue),
            "templates": len(self.template_engine._templates),
            "error_rate": self.stats.error_rate,
        }

    # ── 队列发送 ──

    def _queue_and_send(self, msg: EmailMessage) -> Dict:
        """加入发送队列"""
        msg.status = "queued"
        self._send_queue.append(msg)
        return {"msg_id": msg.msg_id, "status": "queued", "subject": msg.subject}

    def _send_loop(self):
        """后台发送循环"""
        try:
            while self.status == ModuleStatus.RUNNING:
                time.sleep(1)
                if not self._send_queue:
                    continue
                msg = self._send_queue[0]

                # 定时发送检查
                if msg.send_at:
                    send_time = datetime.fromisoformat(msg.send_at)
                    if datetime.now() < send_time:
                        continue

                # 速率限制
                now = time.time()
                while self._send_times and now - self._send_times[0] > 60:
                    self._send_times.popleft()
                if len(self._send_times) >= self.email_config.max_per_minute:
                    continue

                # 执行发送
                try:
                    self._send_times.append(now)
                    all_recipients = msg.to_addrs + msg.cc_addrs + msg.bcc_addrs
                    mime = self._build_mime(msg)
                    sent = self._do_send_smtp(mime, all_recipients)
                    msg.sent_at = self._now()

                    if sent:
                        msg.status = "sent"
                        self.stats.request_count += 1
                        self.record_metrics("email_sent", 1, {"priority": msg.priority.value})
                        self.audit("send", f"to={msg.to_addrs} subject={msg.subject}")
                    else:
                        msg.retry_count += 1
                        if msg.retry_count >= self.email_config.max_retries:
                            msg.status = "failed"
                            msg.error = "max_retries_exceeded"
                            self._send_queue.popleft()
                            self.stats.error_count += 1
                        time.sleep(self.email_config.send_delay * msg.retry_count)
                        continue

                except Exception as e:
                    msg.error = str(e)
                    msg.retry_count += 1
                    if msg.retry_count >= self.email_config.max_retries:
                        msg.status = "failed"
                        self._send_queue.popleft()
                        self.stats.error_count += 1

                self._sent_history.append(msg)
                self._send_queue.popleft()
                time.sleep(self.email_config.send_delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.error(f"发送循环异常: {e}")

    def _check_loop(self):
        """后台邮件检查循环"""
        try:
            while self.status == ModuleStatus.RUNNING:
                time.sleep(self.check_interval)
                if self.status != ModuleStatus.RUNNING:
                    break
                try:
                    new_emails = self._fetch_emails("INBOX", "UNSEEN", 10)
                    if new_emails:
                        self.info(f"收到 {len(new_emails)} 封新邮件")
                        self.record_metrics("new_emails", len(new_emails))
                except Exception as e:
                    self.error(f"检查邮件异常: {e}")
        except asyncio.CancelledError:
            pass

    # ── 标准Action处理器（自动注入）──

    def _do_get_status(self, params):
        """标准action: 模块状态"""
        try:
            status = self.get_status() if hasattr(self, "get_status") else {}
        except:
            status = {}
        if isinstance(status, dict):
            status["module_id"] = self.module_id
            status["version"] = getattr(self, "version", "")
            status["actions"] = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        return status

    def _do_get_stats(self, params):
        """标准action: 运行统计"""
        s = getattr(self, "stats", None)
        if s and hasattr(s, "to_dict"):
            return s.to_dict()
        return {"message": "no stats available"}

    def _do_list_actions(self, params):
        """标准action: 列出可用操作"""
        actions = [k for k in dir(self) if k.startswith("_do_") and callable(getattr(self, k))]
        # Clean up method names
        clean = [a.replace("_do_", "").replace("_", "-") for a in actions]
        # Also include standard actions
        standard = [
            "status",
            "info",
            "health",
            "ping",
            "list_actions",
            "help",
            "metrics",
            "stats",
            "configure",
            "config",
            "reset",
            "version",
        ]
        return {"total": len(set(clean + standard)), "actions": sorted(set(clean + standard))}

    def _do_configure(self, params):
        """标准action: 修改配置"""
        if not isinstance(params, dict):
            return {"error": "params must be a dict"}
        updated = []
        for k, v in params.items():
            if k in ("action",):
                continue
            if hasattr(self, "config"):
                self.config[k] = v
                updated.append(k)
        return {"success": True, "updated": updated}

    def _do_version(self, params):
        """标准action: 版本信息"""
        return {
            "module_id": self.module_id,
            "version": getattr(self, "version", "unknown"),
            "class": self.__class__.__name__,
        }

    def _do_reset(self, params):
        """标准action: 重置"""
        if hasattr(self, "stats"):
            self.stats.request_count = 0
            self.stats.error_count = 0
            self.stats.success_count = 0
            self.stats.latencies = []
        return {"success": True, "message": "reset done"}

module_class = EmailAutomation
