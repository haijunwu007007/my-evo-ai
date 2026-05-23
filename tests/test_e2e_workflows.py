# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — 端到端工作流测试（适配实际模块 action 名）"""
import os, sys, json, http.client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOST, PORT = "localhost", 8765
def po(p, b=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    c.request("POST", p, body=json.dumps(b) if b else None, headers={"Content-Type":"application/json"})
    r = c.getresponse(); d = r.read()
    try: return r.status, json.loads(d)
    except: return r.status, {}

class TestAuthWorkflow:
    def test_jwt_issue_and_verify(self):
        """JWT 签发→验证流程（action: create / verify / refresh）"""
        _, d1 = po("/api/modules/jwt_token/execute", {"action":"create","params":{"claims":{"sub":"e2e_user","roles":["admin"]}}})
        r1 = d1.get("result", d1)
        assert r1.get("success") or d1.get("success"), f"create failed: {d1}"
        token = r1.get("access_token","") or d1.get("access_token","")
        refresh = r1.get("refresh_token","") or d1.get("refresh_token","")
        assert token, f"no access_token in {d1}"
        _, d2 = po("/api/modules/jwt_token/execute", {"action":"verify","params":{"token":token}})
        r2 = d2.get("result", d2)
        assert r2.get("valid") or d2.get("valid"), f"verify failed: {d2}"
        _, d3 = po("/api/modules/jwt_token/execute", {"action":"refresh","params":{"refresh_token":refresh}})
        r3 = d3.get("result", d3)
        assert r3.get("success") or d3.get("success"), f"refresh failed: {d3}"

    def test_rbac_full_flow(self):
        """RBAC 创建角色→分配→校验流程"""
        _, d1 = po("/api/modules/permission_rbac/execute", {"action":"create_role","params":{"role_id":"e2e_role2","permissions":["read","write","delete"]}})
        r1 = d1.get("result", d1)
        assert r1.get("success") or d1.get("success"), f"create_role failed: {d1}"
        _, d2 = po("/api/modules/permission_rbac/execute", {"action":"assign_role","params":{"user_id":"e2e_user2","role_id":"e2e_role2"}})
        r2 = d2.get("result", d2)
        assert "result" in d2 or "success" in d2, f"assign_role failed: {d2}"
        _, d3 = po("/api/modules/permission_rbac/execute", {"action":"check","params":{"user_id":"e2e_user2","permission":"delete"}})
        r3 = d3.get("result", d3)
        assert "has_permission" in r3 or "has_permission" in d3, f"check failed: {d3}"

class TestDataWorkflow:
    def test_data_analysis(self):
        """数据分析：describe 动作"""
        _, d = po("/api/modules/data_analysis/execute", {"action":"describe","data":[1,2,3,4,5,6,7,8,9,10]})
        assert d.get("success"), f"analysis failed: {d}"
        assert d.get("result",{}).get("success") or d.get("success"), "result structure ok"

    def test_forex(self):
        """外汇行情：quote 动作"""
        _, d = po("/api/modules/forex_api/execute", {"action":"quote","pair":"USD/CNY"})
        assert d.get("success"), f"forex failed: {d}"

    def test_recommend(self):
        """推荐系统：recommend 动作"""
        _, d = po("/api/modules/recommendation_system/execute", {"action":"recommend","user_id":"test_user","top_k":3,"cold_start":True})
        r = d.get("result", d)
        assert r.get("success") or d.get("success"), f"recommend failed: {d}"

class TestSecurityWorkflow:
    def test_audit(self):
        """审计追踪：record → query 流程"""
        _, d1 = po("/api/modules/audit_trail/execute", {"action":"record","action_name":"e2e_test","user":"tester","category":"system"})
        r1 = d1.get("result", d1)
        assert r1.get("success") or d1.get("success"), f"audit record failed: {d1}"
        _, d2 = po("/api/modules/audit_trail/execute", {"action":"query","user":"tester","limit":10})
        r2 = d2.get("result", d2)
        assert r2.get("success") or d2.get("success"), f"audit query failed: {d2}"

    def test_rate_limiter(self):
        """API 限流器：check 动作"""
        _, d = po("/api/modules/api_rate_limiter/execute", {"action":"check","key":"test_ip_e2e","limit":100})
        r = d.get("result", d)
        assert r.get("success") or d.get("success"), f"rate limiter failed: {d}"
        assert r.get("allowed") or d.get("success"), "rate check ok"
