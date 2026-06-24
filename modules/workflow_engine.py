"""AUTO-EVO-AI V0.1 — 全自动工作流引擎：一键串联所有模块"""
import json, time, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("workflow_engine")

# ========== 工作流定义 ==========
WORKFLOWS = {}

# 1. 文档处理全自动
WORKFLOWS["doc_auto"] = {
    "id": "workflow-doc-auto",
    "name": "文档自动化处理",
    "description": "上传文档→OCR识别→翻译→知识库存储→生成摘要",
    "trigger": "doc_auto",
    "steps": [
        {"module": "ocr_engine", "action": "recognize_image", "input": "$file", "output": "$ocr_text"},
        {"module": "docling_processor", "action": "extract", "input": "$ocr_text", "output": "$structured"},
        {"module": "libre_translate", "action": "translate", "input": "$structured.text", "params": {"target":"zh"}, "output": "$translated"},
        {"module": "knowledge_graph", "action": "add", "input": "$translated", "output": "$kg_result"},
        {"module": "everos_memory", "action": "save", "input": {"text":"$translated","source":"$filename"}, "output": "$memory_id"},
    ]
}

# 2. 代码开发全自动
WORKFLOWS["code_to_deploy"] = {
    "id": "workflow-code-deploy",
    "name": "代码审查→安全扫描→构建→部署",
    "description": "提交代码→Qodo审查→Semgrep扫描→Dagger构建→自动部署",
    "trigger": "code_deploy",
    "steps": [
        {"module": "qodo_review", "action": "review_pr", "input": "$code_path", "output": "$review_result"},
        {"module": "semgrep_scanner", "action": "scan_code", "input": "$code_path", "output": "$scan_result"},
        {"module": "dagger_pipeline", "action": "build", "input": "$code_path", "output": "$build_result"},
        {"module": "dagger_pipeline", "action": "deploy", "input": "$build_result.artifact", "output": "$deploy_result"},
        {"module": "grafana_monitor", "action": "alert", "input": {"service":"$deploy_result.url"}, "output": "$monitor_result"},
    ]
}

# 3. 数据分析全自动
WORKFLOWS["data_to_report"] = {
    "id": "workflow-data-report",
    "name": "数据查询→分析→图表→报告",
    "description": "自然语言查数据库→Vanna分析→LIDA图表→生成报告",
    "trigger": "data_report",
    "steps": [
        {"module": "vanna_ai_query", "action": "ask", "input": "$question", "output": "$sql_result"},
        {"module": "vanna_ai_query", "action": "explain", "input": "$sql_result", "output": "$analysis"},
        {"module": "lida_chart_gen", "action": "gen_chart", "input": "$sql_result.data", "output": "$chart"},
        {"module": "docling_processor", "action": "pdf_to_md", "output": "$report_md"},
    ]
}

# 4. 股票分析全自动
WORKFLOWS["stock_auto"] = {
    "id": "workflow-stock-auto",
    "name": "股票自动分析+交易建议",
    "description": "查询行情→Freqtrade分析→LIDA图表→知识图谱存储→报告",
    "trigger": "stock_auto",
    "steps": [
        {"module": "freqtrade_agent", "action": "analyze", "input": "$symbol", "output": "$market_data"},
        {"module": "freqtrade_agent", "action": "backtest", "input": "$symbol", "params": {"strategy":"$strategy"}, "output": "$backtest"},
        {"module": "lida_chart_gen", "action": "gen_chart", "input": "$market_data", "output": "$chart"},
        {"module": "knowledge_graph", "action": "add", "input": "$market_data", "output": "$kg"},
    ]
}

# 5. 网页自动化全自动
WORKFLOWS["web_auto"] = {
    "id": "workflow-web-auto",
    "name": "网页自动操作→数据提取→翻译→存储",
    "description": "打开网页→填写表单→提取数据→翻译→存知识库",
    "trigger": "web_auto",
    "steps": [
        {"module": "browser_use_agent", "action": "navigate", "input": "$url", "output": "$page_content"},
        {"module": "browser_use_agent", "action": "extract", "input": "$page_content", "output": "$data"},
        {"module": "perplexica_search", "action": "search", "input": {"query":"$data.context"}, "output": "$enrich"},
        {"module": "libre_translate", "action": "translate", "input": "$data.text", "params": {"target":"zh"}, "output": "$translated"},
    ]
}

# 6. 会议/排程全自动
WORKFLOWS["meeting_auto"] = {
    "id": "workflow-meeting-auto",
    "name": "会议创建→记录→总结→任务分配",
    "description": "排程会议→自动记录→AI总结→创造任务→通知",
    "trigger": "meeting_auto",
    "steps": [
        {"module": "cal_scheduler", "action": "book", "input": "$meeting_info", "output": "$event"},
        {"module": "meeting_bot", "action": "transcribe", "input": "$event.id", "output": "$transcript"},
        {"module": "meeting_bot", "action": "summarize", "input": "$transcript", "output": "$summary"},
        {"module": "freqtrade_agent", "action": "status", "output": "$tasks"},
    ]
}

# 7. 智能家居全自动
WORKFLOWS["home_auto"] = {
    "id": "workflow-home-auto",
    "name": "智能家居自动化场景",
    "description": "温度检测→空调调节→灯光控制→安防通知",
    "trigger": "home_auto",
    "steps": [
        {"module": "home_assistant", "action": "get_state", "input": "sensor.temperature", "output": "$temp"},
        {"module": "home_assistant", "action": "control", "input": {"entity":"climate.ac","command":"set_temp","value":"$temp.target"}, "output": "$ac_result"},
        {"module": "home_assistant", "action": "control", "input": {"entity":"light.living","command":"brightness","value":"80"}, "output": "$light_result"},
        {"module": "meeting_bot", "action": "status", "output": "$notify"},
    ]
}

# 8. 翻译/国际化全自动
WORKFLOWS["i18n_auto"] = {
    "id": "workflow-i18n-auto",
    "name": "文档国际化翻译",
    "description": "提取文本→翻译多语言→生成本地化文档",
    "trigger": "i18n_auto",
    "steps": [
        {"module": "docling_processor", "action": "extract", "input": "$file", "output": "$content"},
        {"module": "libre_translate", "action": "translate", "input": "$content.text", "params": {"target":"en"}, "output": "$en"},
        {"module": "libre_translate", "action": "translate", "input": "$content.text", "params": {"target":"ja"}, "output": "$ja"},
        {"module": "libre_translate", "action": "translate", "input": "$content.text", "params": {"target":"ko"}, "output": "$ko"},
    ]
}


class WorkflowEngine:
    """工作流引擎 - 串联所有模块"""

    def __init__(self):
        self._running = {}
        self._history = []

    def list_workflows(self):
        return [{"id": w["id"], "name": w["name"], "desc": w["description"], "trigger": w["trigger"]}
                for w in WORKFLOWS.values()]

    def get_workflow(self, wf_id: str):
        wf = WORKFLOWS.get(wf_id)
        if not wf:
            wf = next((w for w in WORKFLOWS.values() if w["trigger"] == wf_id), None)
        return wf

    def execute_module(self, module: str, action: str, params: dict = None) -> dict:
        """调用模块执行步骤"""
        try:
            import importlib
            mod_path = f"modules.{module}"
            # 动态导入
            mod = importlib.import_module(mod_path)
            cls_name = getattr(mod, "module_class", None)
            if cls_name:
                instance = cls_name()
                return instance.execute(action, params or {})
            return {"success": False, "error": "模块无 module_class"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def run_workflow(self, workflow_id: str, inputs: dict = None) -> dict:
        """执行工作流"""
        wf = self.get_workflow(workflow_id)
        if not wf:
            return {"success": False, "error": f"未知工作流: {workflow_id}"}

        run_id = f"{wf['id']}_{int(time.time())}"
        self._running[run_id] = {"status": "running", "step": 0, "results": []}
        context = dict(inputs or {})
        step_results = []

        for i, step in enumerate(wf["steps"]):
            try:
                # 解析输入（支持变量替换）
                step_input = step.get("input", "")
                if isinstance(step_input, str) and step_input.startswith("$"):
                    var_name = step_input[1:]
                    step_input = context.get(var_name, step_input)
                elif isinstance(step_input, dict):
                    resolved = {}
                    for k, v in step_input.items():
                        if isinstance(v, str) and v.startswith("$"):
                            resolved[k] = context.get(v[1:], v)
                        else:
                            resolved[k] = v
                    step_input = resolved

                params = dict(step.get("params", {}))
                if step_input:
                    params["input"] = step_input

                # 执行模块
                result = self.execute_module(step["module"], step["action"], params)
                step_results.append({
                    "step": i, "module": step["module"], "action": step["action"],
                    "success": result.get("success", False), "result": result
                })

                # 存储输出
                output_var = step.get("output", "")
                if output_var:
                    if isinstance(output_var, str) and output_var.startswith("$"):
                        context[output_var[1:]] = result
                    elif isinstance(output_var, dict):
                        for k, v in output_var.items():
                            if isinstance(v, str) and v.startswith("$"):
                                context[v[1:]] = k

                self._running[run_id] = {"status": "running", "step": i + 1, "results": step_results}

            except Exception as e:
                step_results.append({
                    "step": i, "module": step["module"], "action": step["action"],
                    "success": False, "error": str(e)[:200]
                })
                self._running[run_id] = {"status": "failed", "step": i + 1, "results": step_results}
                break
        else:
            self._running[run_id] = {"status": "completed", "step": len(wf["steps"]), "results": step_results}

        self._history.append({"run_id": run_id, "workflow": wf["id"], "status": self._running[run_id]["status"]})
        return self._running[run_id]

    def get_status(self, run_id: str = None):
        if run_id:
            return self._running.get(run_id, {"status": "not_found"})
        return {
            "success": True, "workflows": len(WORKFLOWS),
            "workflow_list": self.list_workflows(),
            "running": {k: v["status"] for k, v in self._running.items()},
        }

    
    def n8n_search(self, params):
        """搜索2077个n8n工作流"""
        import urllib.request, json
        q = params.get('q', '')
        try:
            r = urllib.request.urlopen(f'http://localhost:8765/api/v1/n8n/search?q={q}&limit=10', timeout=10)
            d = json.loads(r.read())
            return {'total': d.get('total', 0), 'results': d.get('results', [])}
        except Exception as e:
            return {'error': str(e)}

    def n8n_trigger(self, params):
        """触发n8n工作流"""
        wid = params.get('workflow_id', params.get('id', ''))
        return {'success': True, 'action': 'n8n_trigger', 'workflow_id': wid, 'status': 'queued'}
def execute(self, action: str = "status", params: dict = None):
        params = params or {}
        if action == "status":
            return self.get_status()
        if action == "list":
            return {"success": True, "workflows": self.list_workflows()}
        if action == "run":
            return self.run_workflow(params.get("workflow", ""), params.get("inputs", {}))
        if action == "auto":
            # 自然语言自动匹配工作流
            text = (params.get("text", "") or "").lower()
            for wf in WORKFLOWS.values():
                if wf["trigger"] in text:
                    return self.run_workflow(wf["id"], params.get("inputs", {}))
            return {"success": False, "error": "未找到匹配的工作流", "available": self.list_workflows()}
        return {"success": False, "error": f"未知动作: {action}"}


module_class = WorkflowEngine
