"""AUTO-EVO-AI 基础测试"""
# TODO: 完善测试覆盖
import sys
sys.path.insert(0, '.')

def test_import():
    """验证核心模块可导入"""
    try:
        import api_server
        assert True
    except Exception:
        assert False, "api_server 模块导入失败"

def test_routes_exist():
    """验证路由文件存在"""
    import os
    routes = ['routes_auth', 'routes_cli', 'routes_tool_execute']
    for r in routes:
        path = f'api/routes/{r}.py'
        assert os.path.isfile(path), f'{path} 不存在'

def test_version():
    """验证版本号"""
    c = open('api_server.py', encoding='utf-8').read()
    assert 'VERSION_BUILD' in c, '版本号未定义'
