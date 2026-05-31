# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — Grafana 监控桥接（A级）
# Grade: A

桥接到 Grafana HTTP REST API，暴露 metric 查询、dashboard 列表与详情。
使用 requests 库，内置 graceful degradation。"""
__module_meta__ = {"id":"grafana-monitor","name":"Grafana Monitor","version":"V0.1","group":"monitoring","grade":"B",
    "tags":["monitoring","grafana","observability"],"description":"Grafana 监控 API 桥接"}
from core.logging_config import get_logger, json, datetime
from typing import Any, Dict, List, Optional, Tuple
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger = get_logger("evo.grafana-monitor")

# ── 底层 API 调用（独立函数） ──────────────────────────────────────

def _grafana_get(path: str, base_url: str, api_key: str) -> Tuple[bool, Any]:
    """向 Grafana REST API 发起 GET 请求。
    返回 (success, data) 元组。"""
    try:
        import requests
        url = f"{base_url.rstrip('/')}/api/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True, resp.json()
        return False, {"status_code": resp.status_code, "error": resp.text[:500]}
    except ImportError:
        logger.warning("grafana: requests 不可用，无法调用 API")
        return False, {"error": "requests not available"}
    except Exception as e:
        logger.error("grafana: GET %s 失败: %s", path, e)
        return False, {"error": str(e)}

def query_metric(url: str, api_key: str, query: str) -> Dict:
    """通过 Grafana API 查询 Prometheus 指标。
    使用 /api/ds/query 端点（datasource query proxy）。"""
    try:
        import requests
        base = url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "queries": [{
                "refId": "A",
                "expr": query,
                "queryType": "timeSeriesQuery"
            }],
            "from": (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat() + "Z",
            "to": datetime.datetime.utcnow().isoformat() + "Z"
        }
        resp = requests.post(f"{base}/api/ds/query", json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "data": resp.json()}
        return {"success": False, "status_code": resp.status_code, "error": resp.text[:500]}
    except ImportError:
        logger.warning("grafana: requests 不可用")
        return {"success": False, "error": "requests not available"}
    except Exception as e:
        logger.error("grafana: query_metric 失败: %s", e)
        return {"success": False, "error": str(e)}

def list_dashboards(url: str, api_key: str) -> List[Dict]:
    """列出 Grafana 中所有仪表盘。"""
    ok, data = _grafana_get("/search?type=dash-db", url, api_key)
    if ok and isinstance(data, list):
        return data
    return []

def get_dashboard(url: str, api_key: str, uid: str) -> Dict:
    """获取指定 UID 的仪表盘详情。"""
    ok, data = _grafana_get(f"/dashboards/uid/{uid}", url, api_key)
    if ok and isinstance(data, dict):
        return data
    return {}

# ── EnterpriseModule 类封装 ──────────────────────────────────────

class GrafanaMonitor(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "grafana-monitor"
    MODULE_NAME = "Grafana Monitor"
    VERSION = "v1.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._base_url = "http://localhost:3000"
        self._api_token = ""
        self.logger = get_logger(__name__)

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING
        logger.info("[Grafana] 桥接就绪")

    def health_check(self) -> HealthReport:
        ok, data = _grafana_get("/health", self._base_url, self._api_token)
        return HealthReport(
            status=self.status.value,
            healthy=ok,
            module_id=self.MODULE_ID,
            checks={"base_url": self._base_url, "connected": ok}
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")
        self._base_url = p.get("base_url", self._base_url)
        self._api_token = p.get("api_token", self._api_token)

        try:
            if a == "status":
                ok, data = _grafana_get("/health", self._base_url, self._api_token)
                return {
                    "success": ok,
                    "connected": ok,
                    "version": data.get("version", "") if ok else "",
                    "error": data.get("error") if not ok else None
                }

            if a == "dashboards":
                ok, data = _grafana_get("/search?type=dash-db", self._base_url, self._api_token)
                dashboards = data if isinstance(data, list) else []
                return {"success": ok, "dashboards": dashboards, "count": len(dashboards)}

            if a == "dashboard_detail":
                uid = p.get("uid", "")
                if not uid:
                    return {"success": False, "error": "uid_required"}
                ok, data = _grafana_get(f"/dashboards/uid/{uid}", self._base_url, self._api_token)
                return {"success": ok, "dashboard": data if ok else {}, "error": data.get("error") if not ok else None}

            if a == "datasources":
                ok, data = _grafana_get("/datasources", self._base_url, self._api_token)
                if ok and isinstance(data, list):
                    sources = [{"name": d.get("name", ""), "type": d.get("type", ""), "url": d.get("url", "")} for d in data]
                    return {"success": True, "datasources": sources, "count": len(sources)}
                return {"success": ok, "datasources": [], "error": data.get("error", "") if not ok else "invalid"}

            if a == "annotations":
                ok, data = _grafana_get("/annotations?limit=20", self._base_url, self._api_token)
                annotations = data if isinstance(data, list) else []
                return {"success": ok, "annotations": annotations, "count": len(annotations)}

            if a == "alerts":
                ok, data = _grafana_get("/alerts", self._base_url, self._api_token)
                alerts = data if isinstance(data, list) else []
                alerting_count = sum(1 for a_item in alerts if a_item.get("state") == "alerting")
                return {"success": ok, "alerts": alerts, "alert_count": alerting_count}

            if a == "query_metric":
                query = p.get("query", "")
                if not query:
                    return {"success": False, "error": "query_required"}
                result = query_metric(self._base_url, self._api_token, query)
                return result

            return {"success": False, "error": f"unknown_action:{a}"}

        except Exception as e:
            logger.error("[Grafana] %s 失败: %s", a, e, exc_info=True)
            return {"success": False, "error": str(e)}

    async def shutdown(self) -> None:
        self.status = ModuleStatus.STOPPED

module_class = GrafanaMonitor
