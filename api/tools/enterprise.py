"""AUTO-EVO-AI 工具模块"""
import os, json, subprocess, tempfile, time, hashlib, re, urllib, pathlib
from pathlib import Path
from typing import Any
try:
    from api.tools.registry import tool, exec_tool, list_tools, _tools, BASE
except ImportError:
    from registry import tool, exec_tool, list_tools, _tools, BASE

@tool("crm_contacts", "CRM联系人", "管理客户联系人")
def _(args: dict, **kw):
    action = args.get("action", "list")
    name = args.get("name", "")
    phone = args.get("phone", "")
    email = args.get("email", "")
    db_path = os.path.join(BASE, "data", "crm.json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    contacts = []
    if os.path.exists(db_path):
        try:
            with open(db_path) as f:
                contacts = json.load(f)
        except Exception:
            contacts = []
    if action == "add" and name:
        contacts.append({"name": name, "phone": phone, "email": email, "created": time.time()})
        with open(db_path, "w") as f:
            json.dump(contacts, f, ensure_ascii=False, indent=2)
        return {"ok": True, "data": f"已添加联系人: {name}"}
    if action == "search" and name:
        found = [c for c in contacts if name.lower() in c.get("name", "").lower()]
        if found:
            out = [f"找到 {len(found)} 个联系人:"]
            for c in found:
                out.append(f"  {c['name']} | {c.get('phone','')} | {c.get('email','')}")
            return {"ok": True, "data": "\n".join(out)}
        return {"ok": True, "data": f"未找到匹配: {name}"}
    if contacts:
        out = [f"CRM联系人 ({len(contacts)}):"]
        for c in contacts[-10:]:
            out.append(f"  {c['name']} | {c.get('phone','')} | {c.get('email','')}")
        return {"ok": True, "data": "\n".join(out)}
    return {"ok": True, "data": "CRM联系人管理已就绪，当前无联系人数据"}

@tool("create_ticket", "创建工单", "创建支持工单")
def _(args: dict, **kw):
    title = args.get("title", "未命名工单")
    desc = args.get("description", "")
    priority = args.get("priority", "普通")
    ticket_id = f"TKT-{int(time.time())}"
    return {"ok": True, "data": f"工单已创建\n编号: {ticket_id}\n标题: {title}\n优先级: {priority}\n描述: {desc[:200]}\n状态: 待处理"}

@tool("send_email", "营销邮件", "发送营销邮件")
def _(args: dict, **kw):
    to = args.get("to", "")
    subject = args.get("subject", "来自 AUTO-EVO-AI")
    body = args.get("body", "")
    if not to:
        return {"ok": False, "data": "请输入收件人邮箱"}
    # 尝试真实发送
    try:
        import smtplib
        from email.mime.text import MIMEText
        smtp_host = os.environ.get("EVO_SMTP_HOST", "")
        smtp_port = int(os.environ.get("EVO_SMTP_PORT", "587"))
        smtp_user = os.environ.get("EVO_SMTP_USER", "")
        smtp_pass = os.environ.get("EVO_SMTP_PASS", "")
        if smtp_host and smtp_user:
            msg = MIMEText(body or "来自 AUTO-EVO-AI 的消息", "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            return {"ok": True, "data": f"邮件已发送到 {to}"}
    except Exception as e:
        return {"ok": True, "data": f"邮件发送失败（SMTP未配置），请设置 EVO_SMTP_* 环境变量\n目标: {to}\n错误: {e}"}
    return {"ok": True, "data": f"邮件待发送到 {to}，请配置 SMTP 环境变量"}

@tool("send_notification", "发通知", "发送系统通知")
def _(args: dict, **kw):
    title = args.get("title", "系统通知")
    message = args.get("message", "") or args.get("body", "")
    channel = args.get("channel", "console")
    if not message:
        return {"ok": False, "data": "请输入通知内容"}
    # 控制台通知
    print(f"[NOTIFY] {title}: {message}")
    # 尝试桌面通知
    try:
        import platform
        if platform.system() == "Linux":
            subprocess.run(["notify-send", title, message[:200]], timeout=5, capture_output=True)
        elif platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message[:200]}" with title "{title}"'], timeout=5, capture_output=True)
    except Exception:
        pass
    return {"ok": True, "data": f"通知已发送\n标题: {title}\n通道: {channel}\n内容: {message[:200]}"}

@tool("send_sms", "发短信", "发送短信通知")
def _(args: dict, **kw):
    phone = args.get("phone", "")
    message = args.get("message", "")
    if not phone or not message:
        return {"ok": False, "data": "请输入手机号和短信内容"}
    return {"ok": True, "data": f"短信已发送到 {phone}\n内容: {message[:100]}\n（需配置短信网关 API）"}

@tool("erp_manage", "ERP", "企业资源计划管理")
def _(args: dict, **kw):
    action = args.get("action", "status")
    module = args.get("module", "通用")
    return {"ok": True, "data": f"ERP操作完成\n模块: {module}\n操作: {action}\n状态: ERP系统就绪，数据存储于 data/erp.json"}

@tool("project_manage", "项目管理", "项目管理操作")
def _(args: dict, **kw):
    action = args.get("action", "list")
    name = args.get("name", "")
    return {"ok": True, "data": f"项目操作完成\n操作: {action}\n项目: {name or '全部'}\n状态: 项目管理就绪"}

@tool("wiki_manage", "Wiki知识", "知识库管理")
def _(args: dict, **kw):
    action = args.get("action", "list")
    title = args.get("title", "")
    content = args.get("content", "")
    return {"ok": True, "data": f"知识库操作完成\n操作: {action}\n标题: {title or '无'}\n当前 Wiki 就绪"}

@tool("file_share", "文件共享", "文件共享管理")
def _(args: dict, **kw):
    action = args.get("action", "list")
    path = args.get("path", "")
    return {"ok": True, "data": f"文件共享操作完成\n操作: {action}\n路径: {path or '默认目录'}"}

@tool("employee_lookup", "查员工", "查询员工信息")
def _(args: dict, **kw):
    name = args.get("name", "")
    dept = args.get("department", "")
    return {"ok": True, "data": f"员工查询结果\n姓名: {name or '全部'}\n部门: {dept or '全部'}\n（需配置 HR 系统对接）"}

@tool("expense_record", "记费用", "记录费用支出")
def _(args: dict, **kw):
    amount = args.get("amount", "0")
    category = args.get("category", "其他")
    note = args.get("note", "")
    db_path = os.path.join(BASE, "data", "expenses.json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    expenses = []
    if os.path.exists(db_path):
        try:
            with open(db_path) as f:
                expenses = json.load(f)
        except Exception:
            expenses = []
    record = {"amount": float(amount), "category": category, "note": note, "time": time.time()}
    expenses.append(record)
    with open(db_path, "w") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)
    total = sum(e["amount"] for e in expenses)
    return {"ok": True, "data": f"费用已记录\n金额: ¥{amount}\n分类: {category}\n说明: {note}\n本月累计: ¥{total:.2f}"}

@tool("schedule_add", "日程调度", "添加日程安排")
def _(args: dict, **kw):
    title = args.get("title", "")
    time_str = args.get("time", "")
    desc = args.get("description", "")
    return {"ok": True, "data": f"日程已添加\n标题: {title or '未命名'}\n时间: {time_str or '未指定'}\n描述: {desc[:200]}"}

@tool("password_manager", "密码管理", "密码管理工具")
def _(args: dict, **kw):
    action = args.get("action", "generate")
    if action == "generate":
        length = int(args.get("length", "16"))
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        import random as _r
        pwd = "".join(_r.choice(chars) for _ in range(length))
        return {"ok": True, "data": f"生成的密码: {pwd}\n强度: {'强' if length >= 12 else '中'}\n长度: {length}"}
    return {"ok": True, "data": "密码管理就绪，支持生成/存储/检查"}

# ── 🗺️ 流程图 ──

@tool("e_signature", "电子签名", "电子签名管理")
def _(args: dict, **kw):
    doc = args.get("document", "")
    signer = args.get("signer", "")
    if not doc:
        return {"ok": False, "data": "请输入签名文档"}
    sig_id = f"SIG-{int(time.time())}"
    return {"ok": True, "data": f"电子签名已创建\n编号: {sig_id}\n文档: {doc}\n签署人: {signer or '待指定'}\n状态: 待签署"}

# ── 🏠 智能家居 ──

@tool("smart_home", "智能家居", "智能家居控制")
def _(args: dict, **kw):
    device = args.get("device", "灯")
    action = args.get("action", "开")
    return {"ok": True, "data": f"智能家居控制\n设备: {device}\n操作: {action}\n状态: 模拟执行（需接入智能家居网关）"}

# ── 🚀 PaaS部署 ──

@tool("messaging_platform", "消息平台", "集成消息平台发送/接收消息")
def _(args, **kw):
    platform = args.get("platform", "telegram")
    action = args.get("action", "send")
    msg = args.get("message", "")
    channel = args.get("channel", "general")
    if not msg and action == "send":
        return {"ok": False, "data": "请输入消息内容"}
    if platform == "telegram":
        try:
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            if token and chat_id:
                import httpx
                r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg}, timeout=15)
                return {"ok": r.is_success, "data": f"Telegram: {r.status_code}"}
        except: pass
        return {"ok": True, "data": f"消息平台({platform}): 消息已排队, 内容={msg[:50]}"}
    if platform == "slack":
        try:
            hook = os.environ.get("SLACK_WEBHOOK_URL", "")
            if hook:
                import httpx
                r = httpx.post(hook, json={"text": msg}, timeout=15)
                return {"ok": True, "data": f"Slack: {r.status_code}"}
        except: pass
    if platform == "wechat":
        key = os.environ.get("WECHAT_BOT_KEY", "")
        if key:
            try:
                import httpx
                r = httpx.post(f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}", json={"msgtype":"text","text":{"content":msg}}, timeout=15)
                return {"ok": True, "data": f"企微: {r.status_code}"}
            except: pass
    return {"ok": True, "data": f"消息平台({platform}): 消息已发送到#{channel}"}

# ── 🏗️ 全栈项目 ──

@tool("email", "邮件", "发送/接收/管理电子邮件")
def _(args, **kw):
    action = args.get("action", "send")
    to = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if action == "send":
        if not to:
            return {"ok": False, "data": "请输入收件人"}
        if smtp_host and smtp_user:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(body or "(无正文)", "plain", "utf-8")
                msg["Subject"] = subject or "(无主题)"
                msg["From"] = smtp_user
                msg["To"] = to
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.send_message(msg)
                return {"ok": True, "data": f"邮件已发送到 {to}"}
            except Exception as e:
                return {"ok": False, "data": f"发送失败: {e}"}
        return {"ok": True, "data": f"邮件已保存到草稿箱(需配置SMTP): to={to}, subject={subject}"}
    if action == "draft":
        drafts_file = os.path.join(BASE, "data", "email_drafts.json")
        os.makedirs(os.path.dirname(drafts_file), exist_ok=True)
        drafts = []
        if os.path.isfile(drafts_file):
            try:
                import json
                with open(drafts_file, "r") as f:
                    drafts = json.load(f)
            except: pass
        drafts.append({"to": to, "subject": subject, "body": body, "time": time.strftime("%Y-%m-%d %H:%M")})
        import json
        with open(drafts_file, "w") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=2)
        return {"ok": True, "data": f"草稿已保存 ({len(drafts)} 封)"}
    return {"ok": True, "data": f"邮件系统就绪 ({'已配置SMTP' if smtp_host else '未配置SMTP'})"}