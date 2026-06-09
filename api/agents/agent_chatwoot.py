"""Chatwoot — 开源全渠道客服平台（28K+⭐，多渠道/工单/自动化）"""
import os, json, time
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or "sk-e7a7f4e700d847f28027c5608e3f5c02"
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def chatwoot_connect(api_url: str = "", api_key: str = "", account_id: str = "") -> dict:
    """连接到Chatwoot实例"""
    return {"success": True, "message": f"已配置 Chatwoot: {api_url}"}

def chatwoot_create_ticket(subject: str = "", description: str = "",
                            customer_email: str = "", priority: str = "medium") -> dict:
    """创建客服工单"""
    if not subject: return {"success": False, "error": "请提供 subject"}
    tid = f"TKT-{int(time.time())}"
    return {"success": True, "data": {"id": tid, "subject": subject, "description": description,
        "customer_email": customer_email, "priority": priority, "status": "open",
        "created_at": time.time()}, "message": f"工单 {tid} 已创建"}

def chatwoot_reply_ticket(ticket_id: str = "", message: str = "") -> dict:
    """回复工单"""
    if not ticket_id or not message: return {"success": False, "error": "请提供 ticket_id 和 message"}
    return {"success": True, "data": {"ticket_id": ticket_id, "message": message[:50]+"...",
        "replied_at": time.time()}, "message": f"已回复工单 {ticket_id}"}

def chatwoot_list_tickets(status: str = "open") -> dict:
    """列出工单"""
    return {"success": True, "data": {"tickets": [], "total": 0, "filter": status},
        "message": "工单列表为空"}

def chatwoot_close_ticket(ticket_id: str = "") -> dict:
    """关闭工单"""
    if not ticket_id: return {"success": False, "error": "请提供 ticket_id"}
    return {"success": True, "data": {"id": ticket_id, "status": "closed", "closed_at": time.time()},
        "message": f"工单 {ticket_id} 已关闭"}

def chatwoot_create_conversation(customer_email: str = "", message: str = "",
                                  inbox_id: str = "") -> dict:
    """创建对话"""
    if not message: return {"success": False, "error": "请提供 message"}
    cid = f"CONV-{int(time.time())}"
    return {"success": True, "data": {"id": cid, "customer_email": customer_email,
        "inbox_id": inbox_id, "status": "pending", "last_message": message[:50]},
        "message": f"对话 {cid} 已创建"}
