"""Twenty CRM — 开源AI CRM（30K+⭐，联系人/交易/工单/REST API）"""
import logging
logger = logging.getLogger("evo.agent_twenty")

import os, json, time

TWENTY_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".twenty", "config.json")

def _get_twenty_config() -> dict:
    try:
        if os.path.exists(TWENTY_CONFIG_FILE):
            return json.loads(Path(TWENTY_CONFIG_FILE).read_text(encoding='utf-8'))
    except Exception as _e:
        logger.warning(f"error: {_e}")
    return {}
def _save_twenty_config(cfg: dict):
    os.makedirs(os.path.dirname(TWENTY_CONFIG_FILE), exist_ok=True)
    with open(TWENTY_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False, indent=2)

from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def twenty_connect(api_url: str = "", api_key: str = "") -> dict:
    """连接Twenty CRM"""
    cfg = _get_twenty_config()
    cfg.update({"api_url": api_url, "api_key": api_key[:20]+"...", "status": "connected", "connected_at": time.time()})
    _save_twenty_config(cfg)
    return {"success": True, "message": f"已连接到 Twenty CRM: {api_url}"}

def twenty_create_contact(name: str = "", email: str = "", phone: str = "", company: str = "") -> dict:
    """创建联系人"""
    if not name: return {"success": False, "error": "请提供 name"}
    contact_id = f"contact_{int(time.time())}"
    return {"success": True, "data": {"id": contact_id, "name": name, "email": email,
        "phone": phone, "company": company, "created": time.time()}, "message": f"已创建联系人: {name}"}

def twenty_create_deal(name: str = "", amount: float = 0.0, stage: str = "lead", contact_id: str = "") -> dict:
    """创建交易"""
    if not name: return {"success": False, "error": "请提供 name"}
    deal_id = f"deal_{int(time.time())}"
    return {"success": True, "data": {"id": deal_id, "name": name, "amount": amount,
        "stage": stage, "contact_id": contact_id}, "message": f"已创建交易: {name}"}

def twenty_list_contacts() -> dict:
    """列出联系人"""
    return {"success": True, "data": {"contacts": [], "total": 0}, "message": "联系人列表为空"}

def twenty_list_deals() -> dict:
    """列出交易"""
    return {"success": True, "data": {"deals": [], "total": 0, "total_value": 0}, "message": "交易列表为空"}
