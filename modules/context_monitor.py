from __future__ import annotations

"""

Grade: A

AUTO-EVO-AI V0.1 — 上下文Token监控

实时Token用量追踪 + 自动告警 + /context /clear /compact 命令支持

"""



__module_meta__ = {

    "id": "context-monitor",

    "name": "上下文Token监控",

    "version": "V0.1",

    "group": "developer",

    "grade": "A",

    "description": "实时Token用量追踪 + 自动告警 + 上下文管理",

    "tags": ["context", "token", "monitor"],

}



import time, json, threading

from pathlib import Path

from datetime import datetime

from dataclasses import dataclass, field

from modules._base import Result

from modules._base.enterprise_module import EnterpriseModule





@dataclass

class ContextSnapshot:

    timestamp: float = 0

    estimated_tokens: int = 0

    message_count: int = 0

    fill_percentage: int = 0

    history_size: int = 0  # bytes





class ContextMonitor:

    """上下文监控引擎"""



    MAX_TOKENS = 128000

    WARN_THRESHOLD = 0.80

    CRIT_THRESHOLD = 0.95



    def __init__(self):

        self._messages: list[dict] = []

        self._estimated_tokens = 0

        self._snapshots: list[ContextSnapshot] = []

        self._auto_compact = False

        self._db_path = Path(__file__).parent.parent / ".evo_data" / "context.json"

        self._load()



    def _load(self):

        if self._db_path.exists():

            try:

                data = json.loads(self._db_path.read_text(encoding="utf-8"))

                self._messages = data.get("messages", [])

                self._estimated_tokens = data.get("tokens", 0)

            except Exception:

                pass



    def _save(self):

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path.write_text(

            json.dumps({"messages": self._messages[-200:], "tokens": self._estimated_tokens},

                       ensure_ascii=False),

            encoding="utf-8",

        )



    def _estimate_tokens(self, text: str) -> int:

        """估算文本token数 (中文字符≈2, 英文字符≈0.3)"""

        if not text:

            return 0

        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        english = len(text) - chinese

        return int(chinese * 2 + english * 0.3) + 10



    def add_message(self, role: str, content: str):

        self._messages.append({"role": role, "content": content, "time": time.time()})

        self._estimated_tokens += self._estimate_tokens(content)

        self._take_snapshot()

        self._save()



    def _take_snapshot(self):

        fill = min(100, int(self._estimated_tokens / self.MAX_TOKENS * 100))

        snap = ContextSnapshot(

            timestamp=time.time(),

            estimated_tokens=self._estimated_tokens,

            message_count=len(self._messages),

            fill_percentage=fill,

            history_size=len(json.dumps(self._messages)),

        )

        self._snapshots.append(snap)

        # 只保留最近100条

        if len(self._snapshots) > 100:

            self._snapshots = self._snapshots[-100:]



    def get_status(self) -> dict:

        fill = min(100, int(self._estimated_tokens / self.MAX_TOKENS * 100))

        level = "green"

        if fill >= self.CRIT_THRESHOLD * 100:

            level = "red"

        elif fill >= self.WARN_THRESHOLD * 100:

            level = "yellow"



        return {

            "estimated_tokens": self._estimated_tokens,

            "max_tokens": self.MAX_TOKENS,

            "message_count": len(self._messages),

            "fill_percentage": fill,

            "level": level,

            "auto_compact": self._auto_compact,

        }



    def compact(self) -> dict:

        """压缩上下文：保留系统消息，合并用户消息摘要"""

        before = self._estimated_tokens

        # 保留系统消息和最后的用户/助手消息

        kept = []

        for msg in self._messages:

            if msg["role"] == "system":

                kept.append(msg)



        # 保留最后20条

        recent = self._messages[-20:]

        for msg in recent:

            if msg not in kept:

                kept.append(msg)



        # 中间的消息做摘要合并

        mid_start = len(kept)

        mid_end = len(self._messages) - 20

        if mid_start < mid_end:

            mid_content = "\n".join(

                f"[{m['role']}]: {m['content'][:100]}..." for m in self._messages[mid_start:mid_end]

            )

            kept.append({"role": "system", "content": f"[压缩摘要]: {mid_content[:2000]}"})



        self._messages = kept

        self._estimated_tokens = sum(self._estimate_tokens(m["content"]) for m in self._messages)

        after = self._estimated_tokens

        self._take_snapshot()

        self._save()

        return {"before": before, "after": after, "freed": before - after, "messages_after": len(self._messages)}



    def clear(self):

        self._messages = []

        self._estimated_tokens = 0

        self._take_snapshot()

        self._save()



    def set_auto_compact(self, enabled: bool):

        self._auto_compact = enabled



    def get_history(self) -> list[dict]:

        return [{"timestamp": s.timestamp, "tokens": s.estimated_tokens,

                 "fill": s.fill_percentage, "msgs": s.message_count}

                for s in self._snapshots[-50:]]





_monitor = ContextMonitor()





def get_monitor() -> ContextMonitor:

    return _monitor





class ContextMonitorModule(EnterpriseModule):

    def __init__(self):

        super().__init__(module_id="context-monitor", name="上下文Token监控")



    async def initialize(self):

        self._status = "ready"

        return Result(success=True, message="Context Monitor 就绪")



    async def execute(self, action: str, **params) -> Result:

        m = get_monitor()

        try:

            if action == "status":

                return Result(success=True, data=m.get_status())

            elif action == "compact":

                return Result(success=True, data=m.compact())

            elif action == "clear":

                m.clear()

                return Result(success=True, data={"cleared": True})

            elif action == "history":

                return Result(success=True, data={"snapshots": m.get_history()})

            elif action == "add_message":

                m.add_message(params.get("role", "user"), params.get("content", ""))

                return Result(success=True, data=m.get_status())

            return Result(success=False, error=f"未知动作: {action}")

        except Exception as e:

            return Result(success=False, error=str(e))



    async def health_check(self):

        return Result(success=True, data={"status": self._status})

