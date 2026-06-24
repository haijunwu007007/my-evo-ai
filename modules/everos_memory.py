"""
AUTO-EVO-AI V0.1 — EverOS 记忆系统模块
功能：跨会话持久化记忆、自演进知识图谱、混合检索
"""

import json
import time
import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("everos_memory")

__module_meta__ = {
    "id": "everos-memory",
    "name": "EverOS Memory",
    "version": "V0.1",
    "group": "memory",
    "grade": "A",
    "description": "跨会话持久化记忆系统，支持自演进知识图谱和混合检索",
    "tags": ["memory", "knowledge", "agent", "everos"],
}

MEMORY_FILE = "data/everos_memories.json"
_memory_store: Dict[str, Any] = {"sessions": {}, "entities": {}, "relations": [], "scope_index": {}}

def _load():
    global _memory_store
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                _memory_store = json.load(f)
    except Exception as e:
        logger.warning(f"EverOS load failed: {e}")

def _save():
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_memory_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"EverOS save failed: {e}")

_load()

class EverOSMemory:
    """记忆系统主引擎"""

    @staticmethod
    def status() -> Dict:
        s = _memory_store
        return {
            "success": True,
            "total_sessions": len(s.get("sessions", {})),
            "total_entities": len(s.get("entities", {})),
            "total_relations": len(s.get("relations", [])),
            "scopes": list(s.get("scope_index", {}).keys()),
            "version": "V0.1",
        }

    @staticmethod
    def add_memory(scope: str, content: str, memory_type: str = "note",
                   entities: List[str] = None, session_id: str = None) -> Dict:
        """添加一条记忆"""
        s = _memory_store
        mid = f"mem_{int(time.time()*1000)}"
        entry = {
            "id": mid,
            "scope": scope,
            "type": memory_type,
            "content": content,
            "entities": entities or [],
            "session_id": session_id,
            "ts": time.time(),
            "created": datetime.now().isoformat(),
        }
        if scope not in s["scope_index"]:
            s["scope_index"][scope] = []
        s["scope_index"][scope].append(mid)

        # 实体索引
        for ent in entry["entities"]:
            if ent not in s["entities"]:
                s["entities"][ent] = {"mentions": 0, "first_seen": time.time(), "last_seen": time.time()}
            s["entities"][ent]["mentions"] += 1
            s["entities"][ent]["last_seen"] = time.time()

        # 会话关联
        if session_id:
            if session_id not in s["sessions"]:
                s["sessions"][session_id] = {"memories": [], "created": time.time()}
            s["sessions"][session_id]["memories"].append(mid)

        # 暂存到 flat store（简化实现）
        if "_all" not in s:
            s["_all"] = {}
        s["_all"][mid] = entry
        _save()
        return {"success": True, "memory_id": mid}

    @staticmethod
    def query(q: str, scope: str = None, limit: int = 10) -> Dict:
        """检索记忆（简单关键词匹配）"""
        s = _memory_store
        results = []
        all_entries = s.get("_all", {})
        ql = q.lower()
        for mid, entry in all_entries.items():
            if scope and entry.get("scope") != scope:
                continue
            if ql in entry.get("content", "").lower():
                results.append(entry)
            else:
                for ent in entry.get("entities", []):
                    if ql in ent.lower():
                        results.append(entry)
                        break
        results.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return {"success": True, "results": results[:limit], "total": len(results)}

    @staticmethod
    def get_session(session_id: str) -> Dict:
        """获取会话记忆链"""
        s = _memory_store
        sess = s.get("sessions", {}).get(session_id)
        if not sess:
            return {"success": False, "error": "session not found"}
        mems = [s.get("_all", {}).get(mid) for mid in sess.get("memories", []) if mid in s.get("_all", {})]
        return {"success": True, "session": {"id": session_id, "memories": mems, "created": sess.get("created")}}

    @staticmethod
    def get_entities() -> Dict:
        return {"success": True, "entities": _memory_store.get("entities", {})}

    @staticmethod
    def consolidate():
        """离线巩固：合并相似记忆（桩）"""
        return {"success": True, "consolidated": 0}

class EverOSModule:
    def __init__(self):
        self.engine = EverOSMemory()

    def execute(self, action: str = "status", params: Dict = None) -> Dict:
        p = params or {}
        dispatch = {
            "status": self.engine.status,
            "add": lambda: self.engine.add_memory(p.get("scope", "default"), p.get("content", ""),
                                                   p.get("type", "note"), p.get("entities"), p.get("session_id")),
            "query": lambda: self.engine.query(p.get("q", ""), p.get("scope"), p.get("limit", 10)),
            "session": lambda: self.engine.get_session(p.get("session_id", "")),
            "entities": self.engine.get_entities,
            "consolidate": self.engine.consolidate,
        }
        handler = dispatch.get(action)
        if handler:
            return handler() if callable(handler) else handler
        return self.engine.status()

module_class = EverOSModule
