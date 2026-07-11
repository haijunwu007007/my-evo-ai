"""优先级队列 — 基于优先级的任务队列"""
import logging, json, os, time, sqlite3, heapq
logger = logging.getLogger('evo.modules.priority_queue')
_DB=os.path.join(os.path.dirname(__file__),'..','data','priority_queue.db')
class PriorityQueue:
    def __init__(self):
        self._ready=True; self._heap=[]; self._counter=0
    def enqueue(self, item, priority=0):
        self._counter+=1
        entry = {'id':self._counter,'item':item,'priority':priority,'time':time.time()}
        heapq.heappush(self._heap, (-priority, self._counter, entry))
        return {'success':True,'entry':entry,'queue_length':len(self._heap)}
    def dequeue(self):
        if not self._heap: return {'success':False,'error':'队列为空'}
        _,_,entry = heapq.heappop(self._heap)
        return {'success':True,'entry':entry}
    def peek(self):
        if not self._heap: return {'success':False,'error':'队列为空'}
        return {'success':True,'entry':self._heap[0][2]}
    def list_all(self):
        return [e[2] for e in sorted(self._heap, key=lambda x:-x[0])]
    def status(self): return {'name':'priority_queue','ready':self._ready,'length':len(self._heap)}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='enqueue': return self.enqueue(params.get('item',''),params.get('priority',0))
        if action=='dequeue': return self.dequeue()
        if action=='peek': return self.peek()
        if action=='list': return {'success':True,'total':len(r:=self.list_all()),'items':r}
        return self.status()
get_status = lambda: PriorityQueue().status()
register = lambda: {'name':'priority_queue','class':'PriorityQueue','description':'优先级队列 - 基于优先级的任务队列'}
module_class = PriorityQueue
