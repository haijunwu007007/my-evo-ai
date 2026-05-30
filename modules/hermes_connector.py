"""AUTO-EVO-AI V0.1 — Hermes消息连接器"""
# Grade: B
VERSION="V0.1"
__module_meta__={"id":"hermes-connector","name":"HermesConnector","version":VERSION,"group":"ai"}
import json,threading,time,uuid,logging,urllib.request as ur
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, CircuitBreakerMixin

logger=logging.getLogger(__name__)

class HermesConnector(EnterpriseModule, CircuitBreakerMixin):
    MODULE_ID="hermes-connector";MODULE_NAME="HermesConnector"
    def __init__(self,c=None):
        super().__init__(c)
        self._subscribers={}
        self._messages=[]
        self._lock=threading.Lock()
        self._url=self.config.get("llm_url","http://127.0.0.1:8765/api/llm/chat")
    def initialize(self):self.status=ModuleStatus.INITIALIZING
    def health_check(self):
        from modules._base.enterprise_module import HealthReport
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    def _call(self,msg):
        d=json.dumps({"model":"zhipu:glm-4-flash","messages":[{"role":"user","content":msg}],"max_tokens":1024}).encode()
        try:return json.loads(ur.urlopen(ur.Request(self._url,data=d,headers={"Content-Type":"application/json"},method="POST"),timeout=30).read()).get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:return f"<error: {e}>"
    async def execute(self,a=None,p=None):
        p=p or{}
        try:
            if a=="send":
                topic=p.get("topic","default");content=p.get("content","")
                mid=uuid.uuid4().hex[:8]
                msg={"id":mid,"topic":topic,"content":content,"timestamp":time.time()}
                with self._lock:
                    self._messages.append(msg)
                    subs=self._subscribers.get(topic,[])[:]
                for s in subs:
                    try:
                        if callable(s):s(msg)
                    except Exception:pass
                return {"success":True,"message_id":mid,"delivered_to":len(subs)}
            if a=="broadcast":
                content=p.get("content","")
                bid=uuid.uuid4().hex[:8]
                msg={"id":bid,"topic":"*broadcast","content":content,"timestamp":time.time()}
                with self._lock:
                    self._messages.append(msg)
                    all_subs=[c for subs in self._subscribers.values() for c in subs]
                for s in all_subs:
                    try:
                        if callable(s):s(msg)
                    except Exception:pass
                return {"success":True,"broadcast_id":bid,"delivered_to":len(all_subs)}
            if a=="subscribe":
                topic=p.get("topic","default")
                cb_id=p.get("callback_id","")
                with self._lock:
                    if topic not in self._subscribers:
                        self._subscribers[topic]=[]
                    self._subscribers[topic].append(cb_id)
                return {"success":True,"topic":topic,"subscribers":len(self._subscribers[topic])}
            if a=="pending":
                since=p.get("since",0.0)
                with self._lock:
                    pending=[m for m in self._messages if m["timestamp"]>since]
                return {"success":True,"pending_count":len(pending),"messages":pending[-20:]}
            if a=="status":
                with self._lock:
                    topics=list(self._subscribers.keys())
                    sub_count=sum(len(s) for s in self._subscribers.values())
                return {"success":True,"topics":topics,"topic_count":len(topics),"subscriber_count":sub_count,"total_messages":len(self._messages)}
            return {"success":False,"error":f"unknown: {a}"}
        except Exception as e:
            logger.error("HermesConnector.execute error: %s",e)
            return {"success":False,"error":str(e)}
    async def shutdown(self):
        with self._lock:
            self._subscribers.clear();self._messages.clear()
        self.status=ModuleStatus.STOPPED
module_class=HermesConnector
