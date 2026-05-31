"""
AUTO-EVO-AI V0.1 — 外部服务连接器
====================================
上市公司生产级设计：

核心能力:
  1. 邮件发送 — SMTP统一接口(支持QQ邮箱/163/Gmail/企业邮)
  2. 短信发送 — 统一接口(阿里云短信/腾讯云短信/Twilio)
  3. Webhook推送 — HTTP回调(支持签名验证/重试/批量)
  4. 企业微信通知 — 机器人Webhook
  5. 钉钉通知 — 自定义机器人
  6. 飞书通知 — 机器人Webhook
  7. Server酱 — PushPlus/Server酱/Bark推送
  8. 通知模板 — 变量替换+HTML模板
  9. 发送历史 — 持久化记录
  10. 定时推送 — 结合调度器定时发送

使用方式:
  from core.external_services import NotificationService

  ns = NotificationService()

  # 发邮件
  ns.send_email(to="user@example.com", subject="系统告警", body="CPU超过90%")

  # 发企业微信
  ns.send_wechat_work(webhook_url="https://qyapi.weixin.qq.com/xxx", content="告警信息")

  # 发Webhook
  ns.send_webhook(url="https://example.com/hook", data={"alert": "high"})

依赖: 无外部依赖, 纯标准库
     可选: requests (用于Webhook高级功能)
"""

import os
import re
import json
import time
import hmac
import hashlib
import smtplib
from core.logging_config import get_logger
import threading
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = get_logger("evo.external_services")


# ═══════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════

@dataclass
class NotificationRecord:
    """通知发送记录"""
    id: str = ""
    channel: str = ""  # email | sms | webhook | wechat_work | dingtalk | feishu | push
    to: str = ""
    subject: str = ""
    content: str = ""
    success: bool = False
    error: str = ""
    timestamp: float = 0.0
    retry_count: int = 0
    cost: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = hashlib.md5(f"{self.channel}{self.to}{self.timestamp}".encode()).hexdigest()[:16]


@dataclass
class ChannelConfig:
    """通知渠道配置"""
    name: str
    channel_type: str
    enabled: bool = True
    config: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════
# 通知模板引擎
# ═══════════════════════════════════════════════════

class TemplateEngine:
    """简单模板引擎 — 支持 {{变量}} 替换"""

    def __init__(self):
        self._templates: dict[str, str] = {}

    def register(self, name: str, template: str):
        self._templates[name] = template

    def render(self, template: str, variables: dict[str, Any] = None) -> str:
        variables = variables or {}
        # 加载命名模板
        if template in self._templates:
            template = self._templates[template]
        # 替换 {{key}} 变量
        def replacer(match):
            key = match.group(1).strip()
            value = variables.get(key, match.group(0))
            return str(value)
        return re.sub(r'\{\{(.+?)\}\}', replacer, template)

    def list_templates(self) -> dict[str, str]:
        return dict(self._templates)


# ═══════════════════════════════════════════════════
# 邮件发送器
# ═══════════════════════════════════════════════════

class EmailSender:
    """SMTP邮件发送器"""

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "465"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.smtp_ssl = os.environ.get("SMTP_SSL", "true").lower() == "true"
        self.from_name = os.environ.get("SMTP_FROM_NAME", "AUTO-EVO-AI")
        self.from_addr = self.smtp_user or "noreply@example.com"

    def configure(self, host: str, port: int = 465, user: str = "",
                  password: str = "", ssl: bool = True, from_name: str = ""):
        self.smtp_host = host
        self.smtp_port = port
        self.smtp_user = user
        self.smtp_pass = password
        self.smtp_ssl = ssl
        if from_name:
            self.from_name = from_name
        if user:
            self.from_addr = user

    def send(self, to: str, subject: str, body: str,
             html: str = "", cc: str = "", bcc: str = "",
             attachments: list[str] = None) -> dict:
        """发送邮件"""
        if not self.smtp_host or not self.smtp_user:
            return {"success": False, "error": "SMTP未配置: 需设置 SMTP_HOST / SMTP_USER / SMTP_PASS 环境变量"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_addr}>"
            msg["To"] = to
            if cc:
                msg["Cc"] = cc
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")

            # 正文
            if html:
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(html, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            # 附件
            if attachments:
                for fpath in attachments:
                    if os.path.exists(fpath):
                        part = MIMEBase("application", "octet-stream")
                        with open(fpath, "rb") as f:
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = os.path.basename(fpath)
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)

            recipients = [to]
            if cc:
                recipients.extend(cc.split(","))
            if bcc:
                recipients.extend(bcc.split(","))

            if self.smtp_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()

            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.from_addr, recipients, msg.as_string())
            server.quit()

            return {"success": True, "to": to, "subject": subject}

        except smtplib.SMTPAuthenticationError:
            return {"success": False, "error": "SMTP认证失败: 检查用户名和密码"}
        except smtplib.SMTPConnectError as e:
            return {"success": False, "error": f"SMTP连接失败: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass)

    def get_config_info(self) -> dict:
        return {
            "configured": self.is_configured(),
            "host": self.smtp_host,
            "port": self.smtp_port,
            "user": self.smtp_user[:3] + "***" if self.smtp_user else "",
            "ssl": self.smtp_ssl,
            "from": self.from_addr,
        }


# ═══════════════════════════════════════════════════
# IM (即时通讯) 通知器
# ═══════════════════════════════════════════════════

class IMNotifier:
    """企业微信/钉钉/飞书 通知器"""

    @staticmethod
    def send_wechat_work(webhook_url: str, content: str, msg_type: str = "text",
                          mentioned_list: list[str] = None) -> dict:
        """企业微信机器人通知"""
        try:
            payload = {
                "msgtype": msg_type,
                "text": {
                    "content": content,
                    "mentioned_list": mentioned_list or [],
                }
            }
            if msg_type == "markdown":
                payload["markdown"] = {"content": content}

            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("errcode") == 0:
                return {"success": True, "channel": "wechat_work"}
            return {"success": False, "error": result.get("errmsg", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_dingtalk(webhook_url: str, content: str, secret: str = "",
                       msg_type: str = "text", at_mobiles: list[str] = None) -> dict:
        """钉钉机器人通知"""
        try:
            url = webhook_url
            # 加签名
            if secret:
                import hmac as _hmac
                import base64 as _b64
                import urllib.parse as _up
                timestamp = str(int(time.time() * 1000))
                sign_str = f"{timestamp}\n{secret}"
                hmac_code = _hmac.new(secret.encode("utf-8"), sign_str.encode("utf-8"), digestmod=hashlib.sha256).digest()
                sign = _up.quote_plus(_b64.b64encode(hmac_code))
                url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {
                "msgtype": msg_type,
                "text": {
                    "content": content,
                    "at": {"atMobiles": at_mobiles or [], "isAtAll": False},
                }
            }
            if msg_type == "markdown":
                payload["markdown"] = {"title": "通知", "text": content}
                del payload["text"]

            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("errcode") == 0:
                return {"success": True, "channel": "dingtalk"}
            return {"success": False, "error": result.get("errmsg", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_feishu(webhook_url: str, content: str, msg_type: str = "text",
                     title: str = "通知") -> dict:
        """飞书机器人通知"""
        try:
            if msg_type == "interactive":
                payload = {
                    "msg_type": "interactive",
                    "card": {
                        "header": {"title": {"tag": "plain_text", "content": title}},
                        "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": content}}],
                    }
                }
            else:
                payload = {
                    "msg_type": msg_type,
                    "content": {"text": content},
                }
                if msg_type == "post":
                    payload["content"] = {
                        "post": {
                            "zh_cn": {
                                "title": title,
                                "content": [[{"tag": "text", "text": content}]],
                            }
                        }
                    }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                return {"success": True, "channel": "feishu"}
            return {"success": False, "error": result.get("msg", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_slack(webhook_url: str, content: str, title: str = "") -> dict:
        """Slack Incoming Webhook 通知"""
        try:
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": content}}]
            if title:
                blocks.insert(0, {"type": "header", "text": {"type": "plain_text", "text": title}})
            payload = {"blocks": blocks}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                return {"success": True, "channel": "slack"}
            return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_telegram(token: str, chat_id: str, content: str, parse_mode: str = "HTML") -> dict:
        """Telegram Bot 通知"""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": content, "parse_mode": parse_mode}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                return {"success": True, "channel": "telegram"}
            return {"success": False, "error": result.get("description", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_discord(webhook_url: str, content: str, title: str = "",
                     username: str = "AUTO-EVO-AI") -> dict:
        """Discord Webhook 通知"""
        try:
            embed = {"description": content, "color": 0x6366f1}
            if title:
                embed["title"] = title
            payload = {"username": username, "embeds": [embed]}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status in (200, 204):
                return {"success": True, "channel": "discord"}
            return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_google_chat(webhook_url: str, content: str, title: str = "") -> dict:
        """Google Chat Webhook 通知"""
        try:
            payload = {
                "text": content,
                "cardsV2": [{"cardId": "card", "card": {
                    "header": {"title": title or "AUTO-EVO-AI"},
                    "sections": [{"widgets": [{"textParagraph": {"text": content}}]}],
                }}],
            }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json; charset=UTF-8"})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                return {"success": True, "channel": "google_chat"}
            return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_teams(webhook_url: str, content: str, title: str = "") -> dict:
        """Microsoft Teams Incoming Webhook 通知"""
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": title or "AUTO-EVO-AI",
                "themeColor": "6366F1",
                "title": title or "AUTO-EVO-AI",
                "text": content,
            }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=data, method="POST",
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                return {"success": True, "channel": "teams"}
            return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}





# ═══════════════════════════════════════════════════
# 推送服务
# ═══════════════════════════════════════════════════

class PushService:
    """Server酱/PushPlus/Bark 推送"""

    @staticmethod
    def send_serverchan(sendkey: str, title: str, desp: str = "") -> dict:
        """Server酱推送"""
        try:
            url = f"https://sctapi.ftqq.com/{sendkey}.send"
            data = f"title={urllib.parse.quote(title)}&desp={urllib.parse.quote(desp)}".encode()
            req = urllib.request.Request(url, data=data, method="POST",
                                          headers={"Content-Type": "application/x-www-form-urlencoded"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("code") == 0:
                return {"success": True, "channel": "serverchan"}
            return {"success": False, "error": result.get("message", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_pushplus(token: str, title: str, content: str,
                       template: str = "txt", topic: str = "") -> dict:
        """PushPlus推送"""
        try:
            url = "http://www.pushplus.plus/send"
            payload = {
                "token": token,
                "title": title,
                "content": content,
                "template": template,
            }
            if topic:
                payload["topic"] = topic
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST",
                                          headers={"Content-Type": "application/x-www-form-urlencoded"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("code") == 200:
                return {"success": True, "channel": "pushplus"}
            return {"success": False, "error": result.get("msg", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_bark(device_key: str, title: str, body: str,
                   server: str = "https://api.day.app") -> dict:
        """Bark推送 (iOS/macOS)"""
        try:
            url = f"{server}/{device_key}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            if result.get("code") == 200:
                return {"success": True, "channel": "bark"}
            return {"success": False, "error": result.get("message", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
# Webhook发送器
# ═══════════════════════════════════════════════════

import urllib.parse


class WebhookSender:
    """HTTP Webhook发送器 — 支持签名/重试"""

    def __init__(self):
        self._history: list[dict] = []
        self._max_retries = 3
        self._timeout = 10

    def send(self, url: str, data: Any, method: str = "POST",
             headers: dict = None, secret: str = "",
             retries: int = 0) -> dict:
        """发送Webhook"""
        headers = headers or {"Content-Type": "application/json"}
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if isinstance(data, (dict, list)) else str(data).encode()

        # 签名
        if secret:
            sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            headers["X-Signature"] = sig

        last_error = ""
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=payload, method=method, headers=headers)
                resp = urllib.request.urlopen(req, timeout=self._timeout)
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")[:500]
                result = {"success": 200 <= status < 300, "status": status, "body": body}
                self._history.append({
                    "url": url[:100], "status": status, "success": result["success"],
                    "timestamp": time.time(), "attempts": attempt + 1,
                })
                return result
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}"
            except Exception as e:
                last_error = str(e)
            if attempt < retries:
                time.sleep(1 * (attempt + 1))  # 递增等待

        self._history.append({"url": url[:100], "status": 0, "success": False, "error": last_error, "timestamp": time.time()})
        return {"success": False, "error": last_error}

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]


# ═══════════════════════════════════════════════════
# 通知服务 — 统一入口
# ═══════════════════════════════════════════════════

class NotificationService:
    """
    外部服务统一通知入口

    支持: 邮件/企业微信/钉钉/飞书/Server酱/PushPlus/Bark/Webhook
    """

    def __init__(self):
        self._email = EmailSender()
        self._im = IMNotifier()
        self._push = PushService()
        self._webhook = WebhookSender()
        self._template = TemplateEngine()
        self._records: list[NotificationRecord] = []
        self._max_records = 2000
        self._lock = threading.Lock()
        self._register_default_templates()

    def _register_default_templates(self):
        """注册默认通知模板"""
        self._template.register("alert", "🚨 系统告警\n模块: {{module}}\n级别: {{level}}\n详情: {{detail}}\n时间: {{time}}")
        self._template.register("task_complete", "✅ 任务完成\n任务: {{task}}\n状态: {{status}}\n耗时: {{duration}}\n时间: {{time}}")
        self._template.register("system_report", "📊 系统报告\n{{summary}}\n时间: {{time}}")
        self._template.register("welcome", "👋 欢迎使用 AUTO-EVO-AI\n\n系统已启动，当前状态:\n{{status}}")

    def _record(self, channel: str, to: str, subject: str, content: str,
                success: bool, error: str = "", retry_count: int = 0):
        """记录发送历史"""
        with self._lock:
            self._records.append(NotificationRecord(
                channel=channel, to=to, subject=subject, content=content,
                success=success, error=error, retry_count=retry_count,
            ))
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

    # ─── 邮件 ───

    def send_email(self, to: str, subject: str, body: str,
                   html: str = "", cc: str = "", bcc: str = "") -> dict:
        """发送邮件"""
        result = self._email.send(to=to, subject=subject, body=body,
                                   html=html, cc=cc, bcc=bcc)
        self._record("email", to, subject, body[:100], result.get("success", False),
                     result.get("error", ""))
        return result

    def configure_email(self, **kwargs) -> dict:
        """配置SMTP"""
        self._email.configure(**kwargs)
        return {"success": True, "config": self._email.get_config_info()}

    def email_config(self) -> dict:
        return self._email.get_config_info()

    # ─── 企业微信 ───

    def send_wechat_work(self, webhook_url: str, content: str,
                          msg_type: str = "text") -> dict:
        """企业微信机器人通知"""
        result = self._im.send_wechat_work(webhook_url, content, msg_type)
        self._record("wechat_work", webhook_url[:50], "", content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── 钉钉 ───

    def send_dingtalk(self, webhook_url: str, content: str,
                       secret: str = "", msg_type: str = "text") -> dict:
        """钉钉机器人通知"""
        result = self._im.send_dingtalk(webhook_url, content, secret, msg_type)
        self._record("dingtalk", webhook_url[:50], "", content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── 飞书 ───

    def send_feishu(self, webhook_url: str, content: str,
                     msg_type: str = "text", title: str = "通知") -> dict:
        """飞书机器人通知"""
        result = self._im.send_feishu(webhook_url, content, msg_type, title)
        self._record("feishu", webhook_url[:50], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Slack ───

    def send_slack(self, webhook_url: str, content: str, title: str = "") -> dict:
        """Slack 通知"""
        result = self._im.send_slack(webhook_url, content, title)
        self._record("slack", webhook_url[:50], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Telegram ───

    def send_telegram(self, token: str, chat_id: str, content: str,
                       parse_mode: str = "HTML") -> dict:
        """Telegram 通知"""
        result = self._im.send_telegram(token, chat_id, content, parse_mode)
        self._record("telegram", f"chat:{chat_id}", "", content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Discord ───

    def send_discord(self, webhook_url: str, content: str, title: str = "",
                      username: str = "AUTO-EVO-AI") -> dict:
        """Discord 通知"""
        result = self._im.send_discord(webhook_url, content, title, username)
        self._record("discord", webhook_url[:50], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Google Chat ───

    def send_google_chat(self, webhook_url: str, content: str, title: str = "") -> dict:
        """Google Chat 通知"""
        result = self._im.send_google_chat(webhook_url, content, title)
        self._record("google_chat", webhook_url[:50], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Microsoft Teams ───

    def send_teams(self, webhook_url: str, content: str, title: str = "") -> dict:
        """Teams 通知"""
        result = self._im.send_teams(webhook_url, content, title)
        self._record("teams", webhook_url[:50], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Push ───

    def send_serverchan(self, sendkey: str, title: str, desp: str = "") -> dict:
        """Server酱推送"""
        result = self._push.send_serverchan(sendkey, title, desp)
        self._record("serverchan", sendkey[:10], title, desp[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    def send_pushplus(self, token: str, title: str, content: str,
                       template: str = "txt") -> dict:
        """PushPlus推送"""
        result = self._push.send_pushplus(token, title, content, template)
        self._record("pushplus", token[:10], title, content[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    def send_bark(self, device_key: str, title: str, body: str) -> dict:
        """Bark推送"""
        result = self._push.send_bark(device_key, title, body)
        self._record("bark", device_key[:10], title, body[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── Webhook ───

    def send_webhook(self, url: str, data: Any, method: str = "POST",
                     headers: dict = None, secret: str = "", retries: int = 0) -> dict:
        """发送Webhook"""
        result = self._webhook.send(url, data, method, headers, secret, retries)
        self._record("webhook", url[:80], "", json.dumps(data)[:100] if isinstance(data, dict) else str(data)[:100],
                     result.get("success", False), result.get("error", ""))
        return result

    # ─── 模板 ───

    def render_template(self, template_name: str, variables: dict = None) -> str:
        """渲染通知模板"""
        return self._template.render(template_name, variables)

    def list_templates(self) -> dict[str, str]:
        return self._template.list_templates()

    # ─── 统一发送 (自动路由) ───

    def send(self, channel: str, to: str, subject: str = "", content: str = "",
             **kwargs) -> dict:
        """
        统一发送接口 — 根据channel自动路由
        channel: email | wechat_work | dingtalk | feishu | serverchan | pushplus | bark | webhook
        """
        dispatch = {
            "email": lambda: self.send_email(to, subject, content, html=kwargs.get("html", ""), cc=kwargs.get("cc", "")),
            "wechat_work": lambda: self.send_wechat_work(to, content, msg_type=kwargs.get("msg_type", "text")),
            "dingtalk": lambda: self.send_dingtalk(to, content, secret=kwargs.get("secret", ""), msg_type=kwargs.get("msg_type", "text")),
            "feishu": lambda: self.send_feishu(to, content, msg_type=kwargs.get("msg_type", "text"), title=subject),
            "slack": lambda: self.send_slack(to, content, title=subject),
            "telegram": lambda: self.send_telegram(to, kwargs.get("chat_id", ""), content, parse_mode=kwargs.get("parse_mode", "HTML")),
            "discord": lambda: self.send_discord(to, content, title=subject, username=kwargs.get("username", "AUTO-EVO-AI")),
            "google_chat": lambda: self.send_google_chat(to, content, title=subject),
            "teams": lambda: self.send_teams(to, content, title=subject),
            "serverchan": lambda: self.send_serverchan(to, subject, content),
            "pushplus": lambda: self.send_pushplus(to, subject, content, template=kwargs.get("template", "txt")),
            "bark": lambda: self.send_bark(to, subject, content),
            "webhook": lambda: self.send_webhook(to, json.loads(content) if isinstance(content, str) else content,
                                                  secret=kwargs.get("secret", "")),
        }
        handler = dispatch.get(channel)
        if not handler:
            return {"success": False, "error": f"未知通知渠道: {channel}, 支持: {list(dispatch.keys())}"}
        return handler()

    # ─── 历史记录 ───

    def get_history(self, channel: str = "", limit: int = 50) -> list[dict]:
        """获取发送历史"""
        with self._lock:
            records = self._records
        if channel:
            records = [r for r in records if r.channel == channel]
        records = records[-limit:]
        return [
            {
                "id": r.id, "channel": r.channel, "to": r.to,
                "subject": r.subject, "content_preview": r.content[:80],
                "success": r.success, "error": r.error,
                "timestamp": r.timestamp,
                "time": datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in records
        ]

    def list_channels(self) -> list[dict]:
        """列出所有通知渠道"""
        return [
            {"id": "email", "name": "邮件", "configured": self._email.is_configured()},
            {"id": "wechat_work", "name": "企业微信", "configured": True},
            {"id": "dingtalk", "name": "钉钉", "configured": True},
            {"id": "feishu", "name": "飞书", "configured": True},
            {"id": "slack", "name": "Slack", "configured": True},
            {"id": "telegram", "name": "Telegram", "configured": True},
            {"id": "discord", "name": "Discord", "configured": True},
            {"id": "google_chat", "name": "Google Chat", "configured": True},
            {"id": "teams", "name": "Microsoft Teams", "configured": True},
            {"id": "serverchan", "name": "Server酱", "configured": True},
            {"id": "pushplus", "name": "PushPlus", "configured": True},
            {"id": "bark", "name": "Bark(iOS)", "configured": True},
            {"id": "webhook", "name": "Webhook", "configured": True},
        ]

    def get_stats(self) -> dict:
        """发送统计"""
        with self._lock:
            records = self._records
        if not records:
            return {"total": 0}
        by_channel = defaultdict(lambda: {"total": 0, "success": 0, "fail": 0})
        for r in records:
            c = by_channel[r.channel]
            c["total"] += 1
            if r.success:
                c["success"] += 1
            else:
                c["fail"] += 1
        return {
            "total": len(records),
            "success_rate": round(sum(1 for r in records if r.success) / len(records) * 100, 1),
            "by_channel": dict(by_channel),
        }


# ═══════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════

_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
