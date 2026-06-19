# -*- coding: utf-8 -*-
"""自进化学习引擎 — 记录→评分→优化策略"""
from __future__ import annotations
import os, json, sqlite3, time
from typing import Optional

class SelfEvolveLearner:
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "self_evolve.db")
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
                agent TEXT, task_type TEXT, prompt TEXT, result TEXT,
                score REAL, duration REAL, feedback TEXT
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS strategies(
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_type TEXT,
                strategy TEXT, success_rate REAL, count INT
            )""")
        return self._conn
    
    def record(self, agent: str, task_type: str, prompt: str, result: str, duration: float):
        db = self._get_db()
        db.execute("INSERT INTO tasks(timestamp,agent,task_type,prompt,result,score,duration,feedback) VALUES(?,?,?,?,?,?,?,?)",
                   (time.time(), agent, task_type, prompt[:200], result[:200], 0.0, duration, ""))
        db.commit()
        return db.lastrowid
    
    def score(self, task_id: int, score: float, feedback: str = ""):
        db = self._get_db()
        db.execute("UPDATE tasks SET score=?,feedback=? WHERE id=?", (score, feedback[:100], task_id))
        db.commit()
        # Update strategy success rate
        row = db.execute("SELECT task_type,score FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row:
            ttype = row[0]
            stats = db.execute("SELECT COUNT(*),AVG(score) FROM tasks WHERE task_type=?", (ttype,)).fetchone()
            count, avg = stats[0] or 1, stats[1] or 0
            db.execute("INSERT OR REPLACE INTO strategies(task_type,strategy,success_rate,count) VALUES(?,?,?,?)",
                       (ttype, f"default_{ttype}", round(avg, 2), count))
        db.commit()
    
    def get_stats(self) -> dict:
        db = self._get_db()
        total = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        avg_score = db.execute("SELECT AVG(score) FROM tasks").fetchone()[0] or 0
        strategies = db.execute("SELECT task_type,strategy,success_rate,count FROM strategies").fetchall()
        return {"total_tasks": total, "avg_score": round(avg_score, 2),
                "strategies": [{"task_type":s[0],"strategy":s[1],"rate":s[2],"count":s[3]} for s in strategies]}
    
    def close(self):
        if self._conn: self._conn.close()
