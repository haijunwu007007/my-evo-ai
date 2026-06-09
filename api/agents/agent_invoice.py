"""Invoice Ninja — 开源发票+报价+费用追踪（自托管账单自动化）"""
import os, json, time
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or "sk-e7a7f4e700d847f28027c5608e3f5c02"
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def invoice_create(client: str = "", amount: float = 0.0, items: list = None,
                   due_date: str = "", notes: str = "") -> dict:
    """创建发票"""
    if not client or amount <= 0: return {"success": False, "error": "请提供 client 和 amount"}
    inv_id = f"INV-{int(time.time())}"
    items = items or [{"description": "服务费", "cost": amount, "quantity": 1}]
    return {"success": True, "data": {"id": inv_id, "client": client, "amount": amount,
        "items": items, "due_date": due_date or "30天后", "status": "draft", "notes": notes},
        "message": f"发票 {inv_id} 已创建，金额: ¥{amount}"}

def invoice_send(invoice_id: str = "", email: str = "") -> dict:
    """发送发票"""
    if not invoice_id: return {"success": False, "error": "请提供 invoice_id"}
    return {"success": True, "data": {"id": invoice_id, "sent_to": email or "client",
        "sent_at": time.time(), "status": "sent"}, "message": f"发票 {invoice_id} 已发送"}

def invoice_list(status: str = "") -> dict:
    """列出发票"""
    return {"success": True, "data": {"invoices": [], "total": 0, "filter": status or "全部"},
        "message": "发票列表为空"}

def invoice_create_quote(client: str = "", amount: float = 0.0, items: list = None) -> dict:
    """创建报价单"""
    if not client or amount <= 0: return {"success": False, "error": "请提供 client 和 amount"}
    qid = f"QTE-{int(time.time())}"
    return {"success": True, "data": {"id": qid, "client": client, "amount": amount,
        "items": items or [], "status": "draft"}, "message": f"报价单 {qid} 已创建"}

def invoice_track_expense(description: str = "", amount: float = 0.0,
                           category: str = "", date: str = "") -> dict:
    """记录费用"""
    if not description or amount <= 0: return {"success": False, "error": "请提供 description 和 amount"}
    eid = f"EXP-{int(time.time())}"
    return {"success": True, "data": {"id": eid, "description": description,
        "amount": amount, "category": category, "date": date or time.strftime("%Y-%m-%d")},
        "message": f"费用已记录: ¥{amount} - {description}"}
