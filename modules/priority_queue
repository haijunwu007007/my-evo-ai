"""
AUTO-EVO-AI V0.1 — 优先级队列（堆排序）
"""
VERSION = "V0.1"
__module_meta__ = {"id": "priority-queue", "name": "PriorityQueue", "version": VERSION, "group": "tools"}

import json, heapq, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class PriorityQueue_(PersistMixin, EnterpriseModule):
    MODULE_ID = "priority-queue"; MODULE_NAME = "PriorityQueue"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "priority_queue")
        self._heap = []
    
    def get_status(self): return {"size": len(self._heap)}
    
    def execute(self, action, **kwargs):
        if action == "push":
            priority = kwargs.get("priority", 0)
            item = kwargs.get("item", "")
            heapq.heappush(self._heap, (-priority, time.time(), item))
            self.persist(f"q:{time.time()}", json.dumps({"p":priority,"item":item}))
            return {"pushed": True, "size": len(self._heap)}
        if action == "pop":
            if not self._heap: return {"empty": True}
            _, _, item = heapq.heappop(self._heap)
            return {"item": item, "size": len(self._heap)}
        if action == "peek":
            if not self._heap: return {"empty": True}
            p, t, item = self._heap[0]
            return {"item": item, "priority": -p}
        if action == "size": return {"size": len(self._heap)}
        if action == "clear": self._heap = []; return {"cleared": True}
        return {"error": "unknown: " + str(action)}
