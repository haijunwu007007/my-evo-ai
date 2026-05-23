"""
    Langfuse Monitor - LLM Observability Platform Integration
Provides trace management, observation logging, score tracking, and dashboard integration.
"""

__module_meta__ = {
    "id": "langfuse-monitor",
    "name": "Langfuse Monitor",
    "version": "1.0.0",
    "group": "monitor",
    "inputs": [
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [
        {"type": "schedule", "config": {"cron": "0 */4 * * *"}},
        {"type": "event", "config": {"on": "langfuse_monitor.scan.request"}},
    ],
    "depends_on": [],
    "tags": ["monitor", "langfuse", "engine"],
    "grade": "C",
    "description": "Langfuse Monitor - LLM Observability Platform Integration Provides trace management, observation logging, score tracking, and dashboard integration.",
}

import time
import json
import uuid
import hashlib
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from enum import Enum

from modules._base.enterprise_module import EnterpriseModule

class ObservationType(Enum):
    SPAN = "SPAN"
    GENERATION = "GENERATION"
    EVENT = "EVENT"

class LangfuseMonitor(EnterpriseModule):
    """
    LangfuseMonitor manages LLM observability through the Langfuse platform.

    Sub-engines:
    - TraceEngine     : trace CRUD, tree structure, filtering
    - ObservationEngine: span/generation/event logging, timing
    - ScoreEngine     : score submission, aggregation, evaluation
    - DashboardEngine  : widget rendering, metric queries, alerts
    - WebhookEngine   : event forwarding, retry logic, delivery tracking
    """

    def __init__(self):
        super().__init__()
        self._traces: Dict[str, Dict] = {}
        self._observations: Dict[str, Dict] = {}
        self._scores: Dict[str, List[Dict]] = defaultdict(list)
        self._webhooks: Dict[str, Dict] = {}
        self._dashboards: Dict[str, Dict] = {}
        self._api_url = "https://cloud.langfuse.com/api/public"
        self._api_key = ""
        self._project_id = ""
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None
        self._trace_counter = 0
        self._obs_counter = 0
        self._score_counter = 0
        self._dispatch_registered = False

    def _register_dispatches(self):
        if self._dispatch_registered:
            return
        self._dispatch_registered = True
        self._dispatches = {
            "create_trace": self._create_trace,
            "get_trace": self._get_trace,
            "update_trace": self._update_trace,
            "delete_trace": self._delete_trace,
            "list_traces": self._list_traces,
            "create_observation": self._create_observation,
            "get_observation": self._get_observation,
            "update_observation": self._update_observation,
            "delete_observation": self._delete_observation,
            "list_observations": self._list_observations,
            "create_score": self._create_score,
            "get_scores": self._get_scores,
            "delete_score": self._delete_score,
            "list_scores": self._list_scores,
            "create_dashboard": self._create_dashboard,
            "get_dashboard": self._get_dashboard,
            "update_dashboard": self._update_dashboard,
            "delete_dashboard": self._delete_dashboard,
            "list_dashboards": self._list_dashboards,
            "add_webhook": self._add_webhook,
            "remove_webhook": self._remove_webhook,
            "list_webhooks": self._list_webhooks,
            "test_webhook": self._test_webhook,
            "configure": self._configure,
            "health": self._health,
            "status": self._status,
            "stats": self._stats,
            "reset": self._reset,
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self._register_dispatches()
        handler = self._dispatches.get(action)
        if handler:
            return handler(params)
        return {"success": False, "error": f"Unknown action: {action}"}

    def _trace_engine(self):
        return TraceEngine(self._traces)

    def _observation_engine(self):
        return ObservationEngine(self._observations)

    def _score_engine(self):
        return ScoreEngine(self._scores)

    def _dashboard_engine(self):
        return DashboardEngine(self._dashboards)

    def _webhook_engine(self):
        return WebhookEngine(self._webhooks)

    # ─── Trace Management ───────────────────────────────────────────

    def _create_trace(self, params: Dict) -> Dict:
        name = params.get("name", "unnamed-trace")
        user_id = params.get("user_id", "")
        metadata = params.get("metadata", {})
        release = params.get("release", "")
        version = params.get("version", "")
        tags = params.get("tags", [])
        trace_id = params.get("trace_id") or str(uuid.uuid4())
        if trace_id in self._traces:
            return {"success": False, "error": "trace already exists"}
        ts = time.time()
        self._traces[trace_id] = {
            "trace_id": trace_id,
            "name": name,
            "user_id": user_id,
            "metadata": metadata,
            "release": release,
            "version": version,
            "tags": tags,
            "timestamp": ts,
            "input": params.get("input"),
            "output": params.get("output"),
            "session_id": params.get("session_id"),
            "public": params.get("public", False),
            "observations": [],
        }
        self._trace_counter += 1
        return {"success": True, "trace_id": trace_id}

    def _get_trace(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id", "")
        if not trace_id:
            return {"success": False, "error": "trace_id required"}
        t = self._traces.get(trace_id)
        if not t:
            return {"success": False, "error": "trace not found"}
        return {"success": True, "trace": t}

    def _update_trace(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id", "")
        if not trace_id:
            return {"success": False, "error": "trace_id required"}
        t = self._traces.get(trace_id)
        if not t:
            return {"success": False, "error": "trace not found"}
        for k in [
            "name",
            "user_id",
            "metadata",
            "release",
            "version",
            "tags",
            "input",
            "output",
            "session_id",
            "public",
        ]:
            if k in params:
                t[k] = params[k]
        return {"success": True}

    def _delete_trace(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id", "")
        if not trace_id:
            return {"success": False, "error": "trace_id required"}
        if trace_id not in self._traces:
            return {"success": False, "error": "trace not found"}
        # also remove linked observations
        obs_ids = self._traces[trace_id].get("observations", [])
        for oid in obs_ids:
            self._observations.pop(oid, None)
        del self._traces[trace_id]
        return {"success": True}

    def _list_traces(self, params: Dict) -> Dict:
        user_id = params.get("user_id")
        name = params.get("name")
        tag = params.get("tag")
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)
        results = list(self._traces.values())
        if user_id:
            results = [t for t in results if t.get("user_id") == user_id]
        if name:
            results = [t for t in results if name in t.get("name", "")]
        if tag:
            results = [t for t in results if tag in t.get("tags", [])]
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        total = len(results)
        paged = results[offset : offset + limit]
        return {"success": True, "total": total, "traces": paged}

    # ─── Observation Management ────────────────────────────────────

    def _create_observation(self, params: Dict) -> Dict:
        obs_type = params.get("type", "SPAN").upper()
        trace_id = params.get("trace_id", "")
        name = params.get("name", "unnamed-observation")
        start_time = params.get("start_time", time.time())
        end_time = params.get("end_time")
        model = params.get("model")
        model_parameters = params.get("model_parameters", {})
        input_data = params.get("input")
        output = params.get("output")
        usage = params.get("usage", {})
        metadata = params.get("metadata", {})
        level = params.get("level", "DEFAULT")
        status_message = params.get("status_message", "")
        parent_observation_id = params.get("parent_observation_id")
        obs_id = params.get("observation_id") or str(uuid.uuid4())
        if obs_id in self._observations:
            return {"success": False, "error": "observation already exists"}
        if not trace_id:
            trace_id = str(uuid.uuid4())
            self._traces[trace_id] = {"trace_id": trace_id, "name": f"auto-{obs_id[:8]}", "created_at": time.time()}
        if trace_id not in self._traces:
            return {"success": False, "error": "trace not found"}
        obs = {
            "observation_id": obs_id,
            "trace_id": trace_id,
            "type": obs_type,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "model": model,
            "model_parameters": model_parameters,
            "input": input_data,
            "output": output,
            "usage": usage,
            "metadata": metadata,
            "level": level,
            "status_message": status_message,
            "parent_observation_id": parent_observation_id,
            "version": params.get("version"),
        }
        self._observations[obs_id] = obs
        if trace_id:
            self._traces[trace_id]["observations"].append(obs_id)
        self._obs_counter += 1
        # auto-calculate latency
        if start_time and end_time:
            obs["latency"] = end_time - start_time
        return {"success": True, "observation_id": obs_id}

    def _get_observation(self, params: Dict) -> Dict:
        obs_id = params.get("observation_id", "")
        if not obs_id:
            return {"success": False, "error": "observation_id required"}
        o = self._observations.get(obs_id)
        if not o:
            return {"success": False, "error": "observation not found"}
        return {"success": True, "observation": o}

    def _update_observation(self, params: Dict) -> Dict:
        obs_id = params.get("observation_id", "")
        if not obs_id:
            return {"success": False, "error": "observation_id required"}
        o = self._observations.get(obs_id)
        if not o:
            return {"success": False, "error": "observation not found"}
        for k in [
            "name",
            "end_time",
            "model",
            "model_parameters",
            "input",
            "output",
            "usage",
            "metadata",
            "level",
            "status_message",
            "version",
            "type",
        ]:
            if k in params:
                o[k] = params[k]
        if o.get("start_time") and o.get("end_time"):
            o["latency"] = o["end_time"] - o["start_time"]
        return {"success": True}

    def _delete_observation(self, params: Dict) -> Dict:
        obs_id = params.get("observation_id", "")
        if not obs_id:
            return {"success": False, "error": "observation_id required"}
        o = self._observations.pop(obs_id, None)
        if not o:
            return {"success": False, "error": "observation not found"}
        # unlink from trace
        tid = o.get("trace_id")
        if tid and tid in self._traces:
            to = self._traces[tid].get("observations", [])
            if obs_id in to:
                to.remove(obs_id)
        return {"success": True}

    def _list_observations(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id")
        obs_type = params.get("type")
        name = params.get("name")
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)
        results = list(self._observations.values())
        if trace_id:
            results = [o for o in results if o.get("trace_id") == trace_id]
        if obs_type:
            results = [o for o in results if o.get("type") == obs_type.upper()]
        if name:
            results = [o for o in results if name in o.get("name", "")]
        results.sort(key=lambda x: x.get("start_time", 0), reverse=True)
        total = len(results)
        paged = results[offset : offset + limit]
        return {"success": True, "total": total, "observations": paged}

    # ─── Score Management ───────────────────────────────────────────

    def _create_score(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id")
        observation_id = params.get("observation_id")
        name = params.get("name", "unnamed-score")
        value = params.get("value", 0.0)
        if not isinstance(value, (int, float)):
            return {"success": False, "error": "value must be numeric"}
        score_type = params.get("type", "numeric")
        if score_type == "numeric" and (value < 0 or value > 1):
            return {"success": False, "error": "numeric score must be in [0,1]"}
        comment = params.get("comment", "")
        score_id = str(uuid.uuid4())
        score = {
            "score_id": score_id,
            "trace_id": trace_id,
            "observation_id": observation_id,
            "name": name,
            "value": value,
            "type": score_type,
            "comment": comment,
            "timestamp": time.time(),
        }
        key = trace_id or observation_id or "global"
        self._scores[key].append(score)
        self._score_counter += 1
        return {"success": True, "score_id": score_id}

    def _get_scores(self, params: Dict) -> Dict:
        trace_id = params.get("trace_id")
        observation_id = params.get("observation_id")
        key = trace_id or observation_id or "global"
        scores = self._scores.get(key, [])
        name = params.get("name")
        if name:
            scores = [s for s in scores if s["name"] == name]
        return {"success": True, "scores": scores, "count": len(scores)}

    def _delete_score(self, params: Dict) -> Dict:
        score_id = params.get("score_id", "")
        if not score_id:
            return {"success": False, "error": "score_id required"}
        for key in list(self._scores.keys()):
            self._scores[key] = [s for s in self._scores[key] if s["score_id"] != score_id]
        return {"success": True}

    def _list_scores(self, params: Dict) -> Dict:
        all_scores = []
        for scores in self._scores.values():
            all_scores.extend(scores)
        name = params.get("name")
        if name:
            all_scores = [s for s in all_scores if s["name"] == name]
        all_scores.sort(key=lambda x: x["timestamp"], reverse=True)
        limit = params.get("limit", 50)
        return {"success": True, "scores": all_scores[:limit], "total": len(all_scores)}

    # ─── Dashboard Management ───────────────────────────────────────

    def _create_dashboard(self, params: Dict) -> Dict:
        name = params.get("name", "unnamed-dashboard")
        description = params.get("description", "")
        widgets = params.get("widgets", [])
        dashboard_id = params.get("dashboard_id") or str(uuid.uuid4())
        if dashboard_id in self._dashboards:
            return {"success": False, "error": "dashboard already exists"}
        self._dashboards[dashboard_id] = {
            "dashboard_id": dashboard_id,
            "name": name,
            "description": description,
            "widgets": widgets,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        return {"success": True, "dashboard_id": dashboard_id}

    def _get_dashboard(self, params: Dict) -> Dict:
        dashboard_id = params.get("dashboard_id", "")
        d = self._dashboards.get(dashboard_id)
        if not d:
            return {"success": False, "error": "dashboard not found"}
        return {"success": True, "dashboard": d}

    def _update_dashboard(self, params: Dict) -> Dict:
        dashboard_id = params.get("dashboard_id", "")
        d = self._dashboards.get(dashboard_id)
        if not d:
            return {"success": False, "error": "dashboard not found"}
        for k in ["name", "description", "widgets"]:
            if k in params:
                d[k] = params[k]
        d["updated_at"] = time.time()
        return {"success": True}

    def _delete_dashboard(self, params: Dict) -> Dict:
        dashboard_id = params.get("dashboard_id", "")
        if dashboard_id not in self._dashboards:
            return {"success": False, "error": "dashboard not found"}
        del self._dashboards[dashboard_id]
        return {"success": True}

    def _list_dashboards(self, params: Dict) -> Dict:
        dashboards = list(self._dashboards.values())
        return {"success": True, "dashboards": dashboards, "total": len(dashboards)}

    # ─── Webhook Management ─────────────────────────────────────────

    def _add_webhook(self, params: Dict) -> Dict:
        url = params.get("url", "")
        events = params.get("events", ["trace.create"])
        secret = params.get("secret", "")
        webhook_id = params.get("webhook_id") or str(uuid.uuid4())
        if not url:
            return {"success": False, "error": "url required"}
        self._webhooks[webhook_id] = {
            "webhook_id": webhook_id,
            "url": url,
            "events": events,
            "secret": secret,
            "active": True,
            "created_at": time.time(),
            "last_triggered": None,
            "failure_count": 0,
        }
        return {"success": True, "webhook_id": webhook_id}

    def _remove_webhook(self, params: Dict) -> Dict:
        webhook_id = params.get("webhook_id", "")
        if webhook_id not in self._webhooks:
            return {"success": False, "error": "webhook not found"}
        del self._webhooks[webhook_id]
        return {"success": True}

    def _list_webhooks(self, params: Dict) -> Dict:
        return {"success": True, "webhooks": list(self._webhooks.values())}

    def _test_webhook(self, params: Dict) -> Dict:
        webhook_id = params.get("webhook_id", "")
        wh = self._webhooks.get(webhook_id)
        if not wh:
            return {"success": False, "error": "webhook not found"}
        # simulate: check URL reachability
        url = wh["url"]
        reachable = url.startswith("http://") or url.startswith("https://")
        return {"success": True, "reachable": reachable, "url": url}

    # ─── Configuration ──────────────────────────────────────────────

    def _configure(self, params: Dict) -> Dict:
        if "api_url" in params:
            self._api_url = params["api_url"]
        if "api_key" in params:
            self._api_key = params["api_key"]
        if "project_id" in params:
            self._project_id = params["project_id"]
        return {"success": True}

    def _health(self, params: Dict) -> Dict:
        return {
            "success": True,
            "healthy": True,
            "details": {
                "traces": len(self._traces),
                "observations": len(self._observations),
                "scores": sum(len(v) for v in self._scores.values()),
                "dashboards": len(self._dashboards),
                "webhooks": len(self._webhooks),
            },
        }

    def _status(self, params: Dict) -> Dict:
        return {
            "success": True,
            "module": "langfuse_monitor",
            "traces": len(self._traces),
            "observations": len(self._observations),
            "score_keys": len(self._scores),
            "dashboards": len(self._dashboards),
            "webhooks": len(self._webhooks),
            "api_url": self._api_url,
            "project_id": self._project_id,
        }

    def _stats(self, params: Dict) -> Dict:
        score_values = []
        for scores in self._scores.values():
            for s in scores:
                score_values.append(s["value"])
        avg_score = sum(score_values) / len(score_values) if score_values else 0.0
        return {
            "success": True,
            "trace_count": self._trace_counter,
            "obs_count": self._obs_counter,
            "score_count": self._score_counter,
            "traces_active": len(self._traces),
            "observations_active": len(self._observations),
            "avg_score": round(avg_score, 4),
            "webhook_count": len(self._webhooks),
            "dashboard_count": len(self._dashboards),
        }

    def _reset(self, params: Dict) -> Dict:
        self._traces.clear()
        self._observations.clear()
        self._scores.clear()
        self._webhooks.clear()
        self._dashboards.clear()
        self._trace_counter = 0
        self._obs_counter = 0
        self._score_counter = 0
        return {"success": True}

class TraceEngine:
    """Manages trace CRUD and tree structure."""

    def __init__(self, traces_store: Dict):
        self._traces = traces_store

    def get(self, trace_id: str) -> Optional[Dict]:
        return self._traces.get(trace_id)

    def get_detail(self, trace_id: str) -> Dict:
        t = self._traces.get(trace_id)
        if not t:
            return {}
        return {"trace": t, "observation_count": len(t.get("observations", []))}

class ObservationEngine:
    """Manages observation logging, timing, and model usage tracking."""

    def __init__(self, obs_store: Dict):
        self._obs = obs_store

    def get_by_trace(self, trace_id: str) -> List[Dict]:
        return [o for o in self._obs.values() if o.get("trace_id") == trace_id]

    def calculate_cost(self, obs_id: str) -> float:
        o = self._obs.get(obs_id)
        if not o:
            return 0.0
        usage = o.get("usage", {})
        input_tokens = usage.get("input", 0)
        output_tokens = usage.get("output", 0)
        # simple cost model
        return input_tokens * 0.00003 + output_tokens * 0.00006

class ScoreEngine:
    """Manages score submission, aggregation, and evaluation metrics."""

    def __init__(self, scores_store: Dict):
        self._scores = scores_store

    def aggregate(self, trace_id: str = None) -> Dict:
        scores = []
        if trace_id:
            scores = self._scores.get(trace_id, [])
        else:
            for v in self._scores.values():
                scores.extend(v)
        if not scores:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        values = [s["value"] for s in scores]
        return {"count": len(values), "avg": sum(values) / len(values), "min": min(values), "max": max(values)}

    def evaluate(self, trace_id: str, criteria: List[str]) -> Dict:
        results = {}
        scores = self._scores.get(trace_id, [])
        for c in criteria:
            c_scores = [s for s in scores if s["name"] == c]
            if c_scores:
                avg = sum(s["value"] for s in c_scores) / len(c_scores)
                results[c] = round(avg, 4)
        return results

class DashboardEngine:
    """Manages dashboard widgets, metric queries, and alert configurations."""

    def __init__(self, dashboards_store: Dict):
        self._dashboards = dashboards_store

    def render_widget(self, dashboard_id: str, widget_id: str) -> Dict:
        d = self._dashboards.get(dashboard_id)
        if not d:
            return {"error": "dashboard not found"}
        for w in d.get("widgets", []):
            if w.get("widget_id") == widget_id:
                return {"widget": w, "rendered": True}
        return {"error": "widget not found"}

class WebhookEngine:
    """Manages webhook event forwarding, retry logic, and delivery tracking."""

    def __init__(self, webhooks_store: Dict):
        self._webhooks = webhooks_store

    def matches_event(self, webhook_id: str, event_type: str) -> bool:
        wh = self._webhooks.get(webhook_id)
        if not wh:
            return False
        return event_type in wh["events"]

    def record_delivery(self, webhook_id: str, success: bool):
        wh = self._webhooks.get(webhook_id)
        if wh:
            wh["last_triggered"] = time.time()
            if not success:
                wh["failure_count"] += 1

def module_class():
    return LangfuseMonitor

module_class = LangfuseMonitor
