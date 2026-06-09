"""智能体 — GEMS 多模态记忆（Agent原生多模态生成记忆，107⭐启发）"""
import json, time, re, base64
from pathlib import Path

class GEMS_Memory:
    """多模态记忆：支持图像/文本记忆存储与检索"""
    def __init__(self, BASE):
        self.db_path = BASE / "data" / "gems_memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""CREATE TABLE IF NOT EXISTS gems_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT DEFAULT 'text'
            input_text TEXT, output_text TEXT,
            thumbnail TEXT DEFAULT '',  -- base64小图
            tags TEXT DEFAULT '',
            created REAL, access_count INTEGER DEFAULT 1
        )""")
        conn.commit(); conn.close()
    def save(self, input_text, output_text, content_type="text", thumbnail="", tags=""):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT INTO gems_memory (content_type,input_text,output_text,thumbnail,tags,created) VALUES (?,?,?,?,?,?)",
                      (content_type, input_text[:200], output_text[:500], thumbnail[:1000], tags, time.time()))
        conn.commit(); conn.close()
    def search(self, query, top_k=5):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path)); conn.row_factory = sqlite3.Row
        kw = " ".join(re.findall(r'[\w\u4e00-\u9fff]{2,}', query)[:5])
        if not kw: return []
        rows = conn.execute("SELECT * FROM gems_memory WHERE input_text LIKE ? OR output_text LIKE ? OR tags LIKE ? ORDER BY created DESC LIMIT ?",
                             (f"%{kw[:10]}%", f"%{kw[:10]}%", f"%{kw[:10]}%", top_k)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    def get_stats(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        total = conn.execute("SELECT COUNT(*) FROM gems_memory").fetchone()[0]
        texts = conn.execute("SELECT COUNT(*) FROM gems_memory WHERE content_type='text'").fetchone()[0]
        codes = conn.execute("SELECT COUNT(*) FROM gems_memory WHERE content_type='code'").fetchone()[0]
        conn.close()
        return {"total": total, "texts": texts, "codes": codes}

def get_gems(BASE):
    if not hasattr(get_gems, "_instance"):
        get_gems._instance = GEMS_Memory(BASE)
    return get_gems._instance

# 别名
GEMSGenerator = GEMS_Memory
