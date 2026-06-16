#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 1. 修复集成: 替换deploy_project用简单shell
C.exec_command('''sudo sed -i 's/await git_clone.*/import subprocess as _sp; import os; r=_sp.run(["git","clone","--depth","1",repo,str(local_dir)],capture_output=True,timeout=120); clone_ok=r.returncode==0/' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py''',timeout=10)
# 2. 修复公司任务路由: 加POST
C.exec_command('''sudo sed -i '/@router.get("\\/api\\/v1\\/company\\/task")/a\\\\n@router.post("\\/api\\/v1\\/company\\/task")\\nasync def company_task_post(data: dict):\\n    from api.routes.routes_company import _assign_task\\n    return await _assign_task(data.get("department",""), data.get("task",""))' /home/ubuntu/my-evo-ai/api/routes/routes_company.py''',timeout=10)
time.sleep(2)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)
# 全部验证
tests={
    '添加':'/api/v1/hub/projects',
    '集成':'/api/v1/hub/projects/test-ollama/integrate',
    '组合':'/api/v1/hub/composes',
    '模板':'/api/v1/hub/templates',
    '公司任务':'/api/v1/company/task',
    'Hub页':'/hub','画布':'/canvas','二次开发':'/fork','虚拟公司':'/company','新手引导':'/tutorial',
}
for n,p in tests.items():
    meth='-X POST' if n in ('添加','集成','组合','模板','公司任务') else ''
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 8 {meth} http://127.0.0.1:8765{p}',timeout=12,get_pty=True)
    print(f'  {"✅" if r.read().decode().strip() in("200","301") else "❌"} {n}')
C.close()
