def test_workflow_engine():
    from modules.workflow_engine import WorkflowEngine
    e = WorkflowEngine()
    s = e.get_status()
    assert s["success"] is True
    assert len(s["workflows"]) >= 8
    print("workflow engine OK")

def test_mcp_gateway():
    from api.routes.routes_mcp_gateway import _check_auth
    print("MCP gateway OK")

class TestWorkflowLogic(unittest.TestCase):
    """工作流引擎逻辑测试"""

    def test_workflow_create_and_delete(self):
        """创建→验证→删除工作流"""
        import json, urllib.request
        base = "http://localhost:8765"
        # 创建
        req = urllib.request.Request(f"{base}/api/v1/workflow/create",
            data=json.dumps({"id":"utest","name":"UT测试","trigger":"ut","steps":[],"desc":"自动测试"}).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=10).read())
        self.assertTrue(r.get("success"), f"创建失败: {r}")

        # 列表验证
        r2 = json.loads(urllib.request.urlopen(f"{base}/api/v1/workflow/list", timeout=10).read())
        self.assertTrue(r2.get("success"))
        names = [w["id"] for w in r2.get("workflows",[])]
        self.assertIn("utest", names, f"utest不在工作流列表中: {names}")

        # 删除
        req2 = urllib.request.Request(f"{base}/api/v1/workflow/delete",
            data=json.dumps({"workflow":"utest"}).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
        r3 = json.loads(urllib.request.urlopen(req2, timeout=10).read())
        self.assertTrue(r3.get("success"), f"删除失败: {r3}")

if __name__ == "__main__":

    test_workflow_engine()
    test_mcp_gateway()
    print("All tests passed")
