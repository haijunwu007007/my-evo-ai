"""智能体 — 持久记忆系统（Letta式经验积累）"""
import sqlite3, json, time, re
from pathlib import Path
from collections import defaultdict

class AgentMemory:
    def __init__(self, db_path):
        self.db = Path(db_path)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input TEXT, output TEXT, success INTEGER,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '',
                model TEXT DEFAULT '',
                created REAL, duration REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE, solution TEXT,
                count INTEGER DEFAULT 1, last_used REAL
            )
        """)
        conn.commit(); conn.close()

    def remember(self, input_text, output_text, success=True, category="general", tags="", model="", duration=0):
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute(
                "INSERT INTO memory (input,output,success,category,tags,model,created,duration) VALUES (?,?,?,?,?,?,?,?)",
                (input_text[:200], str(output_text)[:500], 1 if success else 0, category, tags, model, time.time(), duration)
            )
            conn.commit(); conn.close()
        except Exception:
            pass

    def recall(self, query, limit=5):
        """基于关键词的记忆检索"""
        try:
            conn = sqlite3.connect(str(self.db)); conn.row_factory = sqlite3.Row
            kw = " ".join(re.findall(r'[\w\u4e00-\u9fff]{2,}', query)[:5])
            if not kw: return []
            rows = conn.execute(
                "SELECT * FROM memory WHERE input LIKE ? OR output LIKE ? ORDER BY created DESC LIMIT ?",
                (f"%{kw[:10]}%", f"%{kw[:10]}%", limit)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except: return []

    def learn_experience(self, pattern, solution):
        """学习经验：同类问题记住解决方案"""
        try:
            conn = sqlite3.connect(str(self.db))
            existing = conn.execute("SELECT id, count FROM experience WHERE pattern=?", (pattern,)).fetchone()
            if existing:
                conn.execute("UPDATE experience SET count=count+1, last_used=? WHERE pattern=?", (time.time(), pattern))
            else:
                conn.execute("INSERT INTO experience (pattern, solution, count, last_used) VALUES (?,?,1,?)", (pattern, solution[:200], time.time()))
            conn.commit(); conn.close()
        except Exception:
            pass

    def recall_experience(self, query):
        """回忆经验"""
        try:
            conn = sqlite3.connect(str(self.db)); conn.row_factory = sqlite3.Row
            kw = " ".join(re.findall(r'[\w\u4e00-\u9fff]{2,}', query)[:3])
            rows = conn.execute(
                "SELECT * FROM experience WHERE pattern LIKE ? ORDER BY count DESC, last_used DESC LIMIT 3",
                (f"%{kw[:10]}%",)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except: return []

    def get_stats(self):
        """记忆统计"""
        try:
            conn = sqlite3.connect(str(self.db))
            total = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
            success = conn.execute("SELECT COUNT(*) FROM memory WHERE success=1").fetchone()[0]
            exps = conn.execute("SELECT COUNT(*) FROM experience").fetchone()[0]
            conn.close()
            return {"total_memories": total, "success_rate": f"{success/total*100:.0f}%" if total else "0%", "experiences": exps}
        except: return {"error": "unavailable"}
