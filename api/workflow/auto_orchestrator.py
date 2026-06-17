"""多步编排引擎 + 长期自主Agent"""
import json, time, os, threading, logging
from datetime import datetime

logger = logging.getLogger("evo.auto_orchestrator")

TASKS_FILE = "data/auto_tasks.json"

class WorkflowOrchestrator:
    """多步工作流编排"""
    
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._load()
    
    def _load(self):
        if os.path.isfile(TASKS_FILE):
            try:
                with open(TASKS_FILE) as f:
                    self.tasks = json.load(f)
            except:
                self.tasks = {}
        else:
            self.tasks = {}
    
    def _save(self):
        with open(TASKS_FILE, "w") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def create_workflow(self, name, steps):
        """创建多步工作流"""
        wf_id = f"wf_{int(time.time())}"
        self.tasks[wf_id] = {
            "name": name,
            "steps": steps,
            "status": "pending",
            "created": datetime.now().isoformat(),
            "results": [],
            "current_step": 0
        }
        self._save()
        return wf_id
    
    def execute_workflow(self, wf_id):
        """执行工作流"""
        if wf_id not in self.tasks:
            return {"ok": False, "data": "工作流不存在"}
        
        wf = self.tasks[wf_id]
        wf["status"] = "running"
        self._save()
        
        from api.agent_tools import exec_tool
        
        for i, step in enumerate(wf["steps"]):
            wf["current_step"] = i
            tool_name = step.get("tool", "")
            args = step.get("args", {})
            
            # 支持 $prev 变量
            if wf["results"] and "$prev" in str(args):
                args_str = json.dumps(args)
                args_str = args_str.replace("$prev", json.dumps(wf["results"][-1].get("data", "")))
                args = json.loads(args_str)
            
            try:
                r = exec_tool(tool_name, args)
                wf["results"].append(r)
                if not r.get("ok", False):
                    wf["status"] = "failed"
                    wf["error"] = f"步骤{i+1}失败: {r.get('data','')}"
                    self._save()
                    return {"ok": False, "data": wf["error"], "step": i}
            except Exception as e:
                wf["status"] = "failed"
                wf["error"] = f"步骤{i+1}崩溃: {str(e)}"
                self._save()
                return {"ok": False, "data": wf["error"]}
        
        wf["status"] = "completed"
        self._save()
        return {"ok": True, "data": f"工作流完成: {len(wf['results'])}步", "wf_id": wf_id}

class LongTermAgent:
    """长期自主Agent"""
    
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()
        self._running = {}
    
    def submit_task(self, goal, steps):
        """提交长期任务"""
        wf_id = self.orchestrator.create_workflow(goal, steps)
        thread = threading.Thread(target=self._run_loop, args=(wf_id,), daemon=True)
        self._running[wf_id] = thread
        thread.start()
        return {"ok": True, "data": f"任务已提交: {wf_id}", "wf_id": wf_id}
    
    def _run_loop(self, wf_id):
        """后台执行循环"""
        try:
            self.orchestrator.execute_workflow(wf_id)
        except Exception as e:
            logger.error(f"任务{wf_id}异常: {e}")
        finally:
            self._running.pop(wf_id, None)
    
    def get_status(self, wf_id):
        """获取任务状态"""
        return self.orchestrator.tasks.get(wf_id, {})
    
    def list_tasks(self):
        return {k: {"name": v["name"], "status": v["status"], "steps": len(v["steps"])}
                for k, v in self.orchestrator.tasks.items()}
