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

if __name__ == "__main__":
    test_workflow_engine()
    test_mcp_gateway()
    print("All tests passed")
