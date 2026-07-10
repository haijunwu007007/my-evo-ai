"""三级RBAC"""
import logging
logger = logging.getLogger("evo.rbac")

import os, json

ROLES = {"admin": 100, "editor": 50, "viewer": 10}
USERS_FILE = "data/users.json"

def _load():
    if os.path.isfile(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {"admin": {"role": "admin", "dept": "all", "key": os.environ.get("EVO_ADMIN_KEY", "admin123")}}

def _save(u):
    os.makedirs("data", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)

def check_permission(user, required_role, dept=None):
    u = _load().get(user, {})
    user_role = u.get("role", "viewer")
    if ROLES.get(user_role, 0) < ROLES.get(required_role, 0):
        return False
    if dept and u.get("dept") not in ("all", dept):
        return False
    return True

def add_user(user, role="viewer", dept=""):
    u = _load()
    u[user] = {"role": role, "dept": dept or "all", "key": os.urandom(16).hex()}
    _save(u)
    return u[user]["key"]
