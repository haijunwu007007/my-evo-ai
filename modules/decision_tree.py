"""决策树 — 规则引擎"""
import logging
logger = logging.getLogger('evo.modules.decision_tree')
class DecisionTree:
    def __init__(self): self._ready=True; self._rules=[]
    def add(self, condition, action, priority=0):
        self._rules.append({'condition':condition,'action':action,'priority':priority})
        self._rules.sort(key=lambda r:-r['priority'])
        return {'success':True,'rules':len(self._rules)}
    def evaluate(self, context):
        for r in self._rules:
            c=r['condition']
            try:
                if isinstance(c,str):
                    if c in str(context): return {'matched':True,'action':r['action']}
            except: pass
        return {'matched':False}
    def status(self): return {'name':'decision_tree','ready':self._ready,'rules':len(self._rules)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='add': return self.add(p.get('condition',''),p.get('action',''),p.get('priority',0))
        if a=='evaluate': return self.evaluate(p.get('context',{}))
        return self.status()
get_status=lambda:DecisionTree().status()
register=lambda:{'name':'decision_tree','class':'DecisionTree','description':'决策树 - 规则引擎'}
