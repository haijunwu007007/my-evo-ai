#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=10):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode()

print("=== 检查 hub 路由注册 ===")
print(r("grep -n 'hub_router\\|company_router\\|hub_static' /home/ubuntu/my-evo-ai/api_server.py"))
print("=== 检查语法 ===")
print(r("python3 -c 'import py_compile;py_compile.compile(\"/home/ubuntu/my-evo-ai/api_server.py\",doraise=True)' 2>&1||echo ERR"))
print("=== 检查 routes_hub 路由 ===")
print(r("grep 'router = APIRouter' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py"))
print("=== 检查 routes_company 路由 ===")
print(r("grep 'router = APIRouter' /home/ubuntu/my-evo-ai/api/routes/routes_company.py"))
print("=== 尝试导入测试 ===")
print(r("cd /home/ubuntu/my-evo-ai && python3 -c 'from api.routes.routes_hub import router; print(\"hub OK\")' 2>&1"))
print(r("cd /home/ubuntu/my-evo-ai && python3 -c 'from api.routes.routes_company import router; print(\"company OK\")' 2>&1"))
C.close()
