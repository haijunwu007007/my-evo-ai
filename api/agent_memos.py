"""智能体 — MemOS风格三层记忆操作系统"""
import sqlite3, json, time, re
from pathlib import Path
from collections import defaultdict

class MemOSMemory:
    """三层记忆：短时/长时/工作记忆（MemOS架构）"""
    def __init__(self, db_path):
        self.db = Path(db_path)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db))
        now = time.time()
        conn.execute("""CREATE TABLE IF NOT EXISTS short_term (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, role TEXT, content TEXT,
            created REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS long_term (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE, solution TEXT,
            embedding TEXT DEFAULT '',  count INTEGER DEFAULT 1,
            last_used REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS work_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT, state TEXT,
            created REAL DEFAULT 0,
            expires REAL DEFAULT 0
        )""")
        conn.commit(); conn.close()
    
    def save_short(self, session_id, role, content):
        """短时记忆：保存当前对话"""
        conn = sqlite3.connect(str(self.db))
        # 清理超过1小时的旧记录
        conn.execute("DELETE FROM short_term WHERE created < ?", (time.time() - 3600,))
        conn.execute("INSERT INTO short_term (session_id, role, content) VALUES (?,?,?)",
                      (session_id, role, content[:500]))
        conn.commit(); conn.close()
    
    def search_long(self, query, top_k=3):
        """长时记忆：语义搜索历史经验（TF-IDF模拟）"""
        conn = sqlite3.connect(str(self.db))
        rows = conn.execute("SELECT pattern, solution, count FROM long_term ORDER BY last_used DESC").fetchall()
        conn.close()
        
        results = []
        query_words = set(re.findall(r'\w+', query.lower()))
        for pattern, solution, count in rows:
            pattern_words = set(re.findall(r'\w+', pattern.lower()))
            overlap = len(query_words & pattern_words)
            if overlap > 0:
                results.append({"pattern": pattern, "solution": solution, "score": overlap * count})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def save_experience(self, pattern, solution, success=True):
        """长时记忆：累积经验（越用越聪明）"""
        conn = sqlite3.connect(str(self.db))
        exists = conn.execute("SELECT count FROM long_term WHERE pattern = ?", (pattern[:100],)).fetchone()
        if exists:
            conn.execute("UPDATE long_term SET count = count + 1, solution = ?, last_used = ? WHERE pattern = ?",
                          (solution[:500], time.time(), pattern[:100]))
        else:
            conn.execute("INSERT INTO long_term (pattern, solution) VALUES (?,?)",
                          (pattern[:100], solution[:500]))
        conn.commit(); conn.close()
    
    def save_work(self, task_id, state_dict):
        """工作记忆：保存任务中间状态（断点续跑）"""
        conn = sqlite3.connect(str(self.db))
        conn.execute("DELETE FROM work_memory WHERE expires < ?", (time.time(),))
        conn.execute("INSERT OR REPLACE INTO work_memory (task_id, state) VALUES (?,?)",
                      (task_id, json.dumps(state_dict, ensure_ascii=False)))
        conn.commit(); conn.close()
    
    def load_work(self, task_id):
        """工作记忆：恢复任务状态"""
        conn = sqlite3.connect(str(self.db))
        row = conn.execute("SELECT state FROM work_memory WHERE task_id = ?", (task_id,)).fetchone()
        conn.close()
        return json.loads(row[0]) if row else {}

def get_memory():
    """单例模式"""
    if not hasattr(get_memory, "_instance"):
        get_memory._instance = MemOSMemory(
            Path(__file__).resolve().parent.parent / "data" / "memos_memory.db"
        )
    return get_memory._instance
