"""优先级队列"""
import logging,time,heapq
logger=logging.getLogger("evo.modules.priority_queue")
class PriorityQueue:
 def __init__(s):s._ready=True;s._queue=[];s._id=0
 def push(s,item,priority=0):
  s._id+=1;heapq.heappush(s._queue,(-priority,s._id,{"id":s._id,"item":item,"priority":priority,"time":time.time()}));return{"success":True,"id":s._id}
 def pop(s):
  if not s._queue:return{"success":False,"error":"队列为空"}
  _,_,item=heapq.heappop(s._queue);return{"success":True,"item":item}
 def size(s):return{"success":True,"size":len(s._queue)}
 def status(s):return{"name":"priority_queue","ready":s._ready,"size":len(s._queue)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="push":return s.push(p.get("item",""),p.get("priority",0))
  if a=="pop":return s.pop()
  if a=="size":return s.size()
  return s.status()
get_status=lambda:PriorityQueue().status()
register=lambda:{"name":"priority_queue","class":"PriorityQueue","description":"优先级队列"}
