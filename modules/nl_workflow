"""
AUTO-EVO-AI V0.1 — 自然语言工作流解析
"""
VERSION = "V0.1"
__module_meta__ = {"id": "nl-workflow", "name": "NLWorkflow", "version": VERSION, "group": "tools"}

import json, re, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class NLWorkflow(PersistMixin, EnterpriseModule):
    MODULE_ID = "nl-workflow"; MODULE_NAME = "NLWorkflow"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "nl_workflow")
        self._workflows = {}
    
    def get_status(self): return {"workflows": len(self._workflows)}
    
    def execute(self, action, **kwargs):
        if action == "parse":
            text = kwargs.get("text", "")
            steps = []
            # Simple NLP: split by 然后/接着/最后
            parts = re.split(r'[，,。.]\s*(?:然后|接着|最后|再|并)', text)
            for i, p in enumerate(parts):
                if not p.strip(): continue
                steps.append({"step": i+1, "action": p.strip(), "type": self._classify(p)})
            result = {"steps": steps, "count": len(steps)}
            self.persist(f"parse:{time.time()}", json.dumps(result))
            return result
        if action == "save_workflow":
            wid = kwargs.get("id", str(time.time()))
            self._workflows[wid] = {"steps": kwargs.get("steps",[]), "created": time.time()}
            self.persist(f"wf:{wid}", json.dumps(self._workflows[wid]))
            return {"id": wid}
        if action == "list_workflows":
            return list(self._workflows.values())
        return {"error": "unknown: " + str(action)}
    
    def _classify(self, text):
        if any(k in text for k in ["搜索","查","找"]): return "search"
        if any(k in text for k in ["发","通知","邮件"]): return "notify"
        if any(k in text for k in ["部署","发布","上线"]): return "deploy"
        if any(k in text for k in ["生成","创建","新建"]): return "create"
        return "action"
