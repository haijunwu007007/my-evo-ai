from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule
# -*- coding: utf-8 -*-
"""多渠道Agent — 消息通道抽象层"""
import os, json, sqlite3, time
from typing import Optional

class ChannelAgent(EnterpriseModule):
    """多渠道消息收发抽象层"""
    
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "channel.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._channels = {}
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS channels(
                name TEXT PRIMARY KEY, type TEXT, config TEXT, enabled INT DEFAULT 1
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT,
                direction TEXT, content TEXT, meta TEXT, timestamp REAL
            )""")
        return self._conn
    
    def register(self, name: str, channel_type: str, config: dict = {}):
        db = self._get_db()
        db.execute("INSERT OR REPLACE INTO channels VALUES(?,?,?,1)",
                   (name, channel_type, json.dumps(config)))
        db.commit()
        return {"channel": name, "type": channel_type, "status": "registered"}
    
    def send(self, channel: str, content: str) -> dict:
        db = self._get_db()
        row = db.execute("SELECT type,config,enabled FROM channels WHERE name=?", (channel,)).fetchone()
        if not row: return {"success": False, "error": "通道未注册"}
        if not row[2]: return {"success": False, "error": "通道已禁用"}
        db.execute("INSERT INTO messages(channel,direction,content,meta,timestamp) VALUES(?,?,?,?,?)",
                   (channel, "out", content[:500], json.dumps({"type":row[0]}), time.time()))
        db.commit()
        return {"success": True, "channel": channel, "content": content[:100]}
    
    def get_channels(self) -> list:
        db = self._get_db()
        rows = db.execute("SELECT name,type,enabled FROM channels").fetchall()
        return [{"name":r[0],"type":r[1],"enabled":bool(r[2])} for r in rows]
    
    def get_history(self, channel: str = "", limit: int = 20) -> list:
        db = self._get_db()
        if channel:
            rows = db.execute("SELECT * FROM messages WHERE channel=? ORDER BY id DESC LIMIT ?", (channel, limit)).fetchall()
        else:
            rows = db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id":r[0],"channel":r[1],"dir":r[2],"content":r[3][:100],"time":r[5]} for r in rows]
    
    def close(self):
        if self._conn: self._conn.close()
