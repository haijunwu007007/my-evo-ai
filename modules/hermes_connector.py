"""
AUTO-EVO-AI V0.1 — Hermes消息队列连接器
"""
VERSION = "V0.1"
__module_meta__ = {"id": "hermes", "name": "HermesConnector", "version": VERSION, "group": "mq"}

import json, time, threading, queue
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class HermesConnector(PersistMixin, EnterpriseModule):
    MODULE_ID = "hermes"; MODULE_NAME = "HermesConnector"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "hermes")
        self._queues = {}
        self._subs = {}
    
    def get_status(self): return {"queues": len(self._queues), "subscribers": len(self._subs)}
    
    def execute(self, action, **kwargs):
        if action == "publish":
            topic = kwargs.get("topic", "default")
            msg = kwargs.get("message", "")
            if topic not in self._queues: self._queues[topic] = queue.Queue()
            self._queues[topic].put({"data": msg, "ts": time.time()})
            # notify subscribers
            for cb in self._subs.get(topic, []):
                try: cb(msg)
                except: pass
            self.persist(f"msg:{topic}:{time.time()}", json.dumps({"topic":topic,"msg":msg}))
            return {"published": True, "topic": topic}
        if action == "subscribe":
            topic = kwargs.get("topic", "default")
            cb = kwargs.get("callback", "")
            if topic not in self._subs: self._subs[topic] = []
            self._subs[topic].append(cb)
            return {"subscribed": True, "topic": topic}
        if action == "consume":
            topic = kwargs.get("topic", "default")
            if topic in self._queues and not self._queues[topic].empty():
                return self._queues[topic].get()
            return {"empty": True}
        if action == "list_topics": return {"topics": list(self._queues.keys())}
        return {"error": "unknown: " + str(action)}
