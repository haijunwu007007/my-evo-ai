import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 修复integrate.py - 添加git_clone别名
C.exec_command("""sudo sed -i '1i\\n# 兼容旧导入\\ngit_clone = deploy_project\\ngit_deploy = deploy_project\\nstop_project_alias = stop_project' /home/ubuntu/my-evo-ai/api/hub/integrate.py""",timeout=10)
# 同时修复routes_hub.py中的导入
C.exec_command("""sudo sed -i 's/from api.hub.integrate import deploy_project/from api.hub.integrate import deploy_project, git_clone, git_deploy, stop_project/' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py""",timeout=10)
import time
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(15)
_,o,_=C.exec_command('sudo systemctl is-active evo.service',timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
for n,p in [('Hub','/hub'),('Canvas','/canvas'),('Fork','/fork'),('Company','/company'),('API','/api/v1/hub/discover'),('CompanyAPI','/api/v1/company/status')]:
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    print(f'  {r.read().decode().strip()} {n}')
C.close()
