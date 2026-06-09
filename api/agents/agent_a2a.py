"""智能体 — A2A Agent间通信协议（Google/A2A标准）"""
import json, time, uuid, sqlite3
from pathlib import Path

_db_path = None
def _get_conn():
    global _db_path
    if not _db_path:
        _db_path = Path(__file__).resolve().parent.parent / "data" / "a2a.db"
        _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY, name TEXT, url TEXT,
        capabilities TEXT, status TEXT DEFAULT 'active',
        created REAL, last_heartbeat REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY, sender TEXT, recipient TEXT,
        content TEXT, msg_type TEXT DEFAULT 'text',
        status TEXT DEFAULT 'pending', created REAL
    )""")
    conn.commit()
    return conn

def register_agent(name, url="", capabilities=None):
    """注册Agent到A2A网络"""
    conn = _get_conn()
    aid = str(uuid.uuid4())[:8]
    now = time.time()
    conn.execute("INSERT OR REPLACE INTO agents (id, name, url, capabilities, created, last_heartbeat) VALUES (?,?,?,?,?,?)",
                  (aid, name, url, json.dumps(capabilities or [], ensure_ascii=False), now, now))
    conn.commit(); conn.close()
    return {"agent_id": aid, "name": name}

def send_message(sender_id, recipient_id, content, msg_type="text"):
    """Agent间发送消息"""
    conn = _get_conn()
    mid = str(uuid.uuid4())[:12]
    now = time.time()
    conn.execute("INSERT INTO messages (id, sender, recipient, content, msg_type, created) VALUES (?,?,?,?,?,?)",
                  (mid, sender_id, recipient_id, content[:500], msg_type, now))
    conn.commit(); conn.close()
    return {"message_id": mid, "status": "sent"}

def get_messages(agent_id, limit=10):
    """获取Agent的消息"""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM messages WHERE recipient=? OR sender=? ORDER BY created DESC LIMIT ?",
                         (agent_id, agent_id, limit)).fetchall()
    conn.close()
    return [{"id":r[0],"sender":r[1],"recipient":r[2],"content":r[3][:200],"type":r[4],"status":r[5]} for r in rows]

def list_agents():
    """列出所有Agent"""
    conn = _get_conn()
    rows = conn.execute("SELECT id, name, url, capabilities, status FROM agents WHERE status='active'").fetchall()
    conn.close()
    return [{"id":r[0],"name":r[1],"url":r[2],"capabilities":r[3][:100]} for r in rows]

def heartbeat(agent_id):
    """发送心跳"""
    conn = _get_conn()
    conn.execute("UPDATE agents SET last_heartbeat=? WHERE id=?", (time.time(), agent_id))
    conn.commit(); conn.close()

def cleanup():
    """清理过期Agent（30秒无心跳）"""
    conn = _get_conn()
    cutoff = time.time() - 30
    conn.execute("UPDATE agents SET status='offline' WHERE last_heartbeat < ?", (cutoff,))

class A2AProtocol:
    """A2A协议类封装"""
    def __init__(self, db_path=None):
        global _db_path
        if db_path:
            _db_path = Path(db_path)
            _db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        _get_conn().close()
    
    def register_agent(self, name, url="", capabilities=None):
        return register_agent(name, url, capabilities)
    
    def send_message(self, sender_id, recipient_id, content, msg_type="text"):
        return send_message(sender_id, recipient_id, content, msg_type)
    
    def get_messages(self, agent_id, limit=10):
        return get_messages(agent_id, limit)
    
    def list_agents(self):
        return list_agents()
    
    def heartbeat(self, agent_id):
        return heartbeat(agent_id)

# ===== 默认注册系统内部Agent =====
_agent_a2a = None
def get_default_agents():
    global _agent_a2a
    if not _agent_a2a:
        conn = _get_conn()
        existing = conn.execute("SELECT id, name FROM agents WHERE name LIKE 'sys_%'").fetchall()
        conn.close()
        if not existing:
            _agent_a2a = [
                register_agent("sys_planner", capabilities=["任务分解","规划"]),
                register_agent("sys_coder", capabilities=["代码生成","审查"]),
                register_agent("sys_reviewer", capabilities=["代码审查","质量检查"]),
                register_agent("sys_researcher", capabilities=["搜索","信息分析"]),
            ]
    return list_agents()
