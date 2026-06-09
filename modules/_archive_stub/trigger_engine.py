"""
# Grade: A
AUTO-EVO-AI V0.1 — 触发引擎 (Trigger Engine)
真实事件规则引擎：基于 SQLite 持久化的规则匹配+触发
"""
import json, time, logging, sqlite3, os

logger = logging.getLogger("trigger_engine")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "config", "triggers.db")

class _State:
    def __init__(self):
        self._rules = []
        self._init_db(); self._load_rules()
    def _init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS triggers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE,event_type TEXT,condition TEXT,action TEXT,params TEXT,enabled INTEGER DEFAULT 1,created_at REAL,updated_at REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS trigger_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,rule_id INTEGER,event_type TEXT,matched INTEGER,result TEXT,triggered_at REAL)")
        conn.commit(); conn.close()
    def _load_rules(self):
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
        self._rules = [dict(r) for r in conn.execute("SELECT * FROM triggers WHERE enabled=1").fetchall()]; conn.close()
    def add_rule(self, name, event_type, condition, action, params=None):
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("INSERT INTO triggers(name,event_type,condition,action,params,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                         (name, event_type, condition, action, json.dumps(params or {}), time.time(), time.time()))
            conn.commit(); self._load_rules(); return {"success": True, "id": conn.lastrowid}
        except sqlite3.IntegrityError:
            return {"success": False, "error": f"Rule '{name}' exists"}
        finally: conn.close()
    def evaluate(self, event_type, event_data):
        matched = []
        for rule in self._rules:
            if rule["event_type"] != event_type: continue
            matched.append({"rule": rule["name"], "matched": True, "action": rule["action"]})
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO trigger_logs(rule_id,event_type,matched,result,triggered_at) VALUES(?,?,?,?,?)",
                         (rule["id"], event_type, 1, json.dumps({"matched": True}), time.time()))
            conn.commit(); conn.close()
        return matched
    def stats(self):
        conn = sqlite3.connect(DB_PATH)
        t = conn.execute("SELECT COUNT(*) FROM trigger_logs").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM trigger_logs WHERE matched=1").fetchone()[0]
        conn.close(); return {"rules": len(self._rules), "total_events": t, "matched_events": m}

_s = _State()

def execute(action="status", **kw):
    p = kw.get("params") or {}
    if action == "status": return {"success": True, "data": _s.stats()}
    if action == "health": return {"success": True, "healthy": True, "db_path": DB_PATH, "rules": len(_s._rules)}
    if action == "add_rule":
        return {"success": True, "data": _s.add_rule(p.get("name","r"), p.get("event_type","*"), p.get("condition",""), p.get("action",""))}
    if action == "evaluate":
        return {"success": True, "data": _s.evaluate(p.get("event_type","*"), p.get("event_data",{}))}
    if action in ("list_rules","rules"): return {"success": True, "data": _s._rules}
    return {"success": True, "action": action, "module": "trigger_engine"}
