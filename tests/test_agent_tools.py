"""测试 agent_tools 工具注册和执行"""
import sys
sys.path.insert(0, "api")
from agent_tools import list_tools, exec_tool


def test_all_tools_registered():
    """所有工具已注册"""
    tools = list_tools()
    assert len(tools) >= 87


def test_tools_have_required_fields():
    """每个工具有name/category/description"""
    for t in list_tools():
        assert t.get("name")
        assert t.get("category")
        assert t.get("description")


def test_basic_tools_execute():
    """基础工具能正常执行"""
    basic = [
        ("password_manager", {}),
        ("auth_check", {}),
    ]
    for name, args in basic:
        r = exec_tool(name, args)
        assert r.get("ok") is not False, f"{name} failed: {r.get('data','')[:80]}"
