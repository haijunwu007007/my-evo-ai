import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 上传最简版integrate.py
sftp=C.open_sftp()
content = b'''"""简化版集成引擎"""
from __future__ import annotations
import os,json,time,subprocess
from pathlib import Path
from core.logging_config import get_logger
from api.hub.models import get_project, update_project, list_projects
logger=get_logger("evo.hub.integrate")
BASE_DIR=Path(__file__).resolve().parent.parent.parent

async def deploy_project(pid,cfg=None):
    proj=get_project(pid)
    if not proj: return {"success":False,"error":"不存在"}
    local=BASE_DIR/"hub_projects"/proj["name"]
    local.mkdir(parents=True,exist_ok=True)
    repo=proj.get("repo_url","")
    update_project(pid,{"status":"deploying"})
    try:
        if not (local/".git").exists() and repo:
            r=subprocess.run(["git","clone","--depth=1",repo,str(local)],capture_output=True,text=True,timeout=120)
            if r.returncode!=0: return {"success":False,"error":"git clone: "+r.stderr[:200]}
        if (local/"docker-compose.yml").exists():
            r=subprocess.run(["docker","compose","-f",str(local/"docker-compose.yml"),"up","-d"],capture_output=True,text=True,timeout=120)
            if r.returncode!=0: return {"success":False,"error":r.stderr[:200]}
            cid=subprocess.run(["docker","ps","-l","--format","{{.ID}}"],capture_output=True,text=True,timeout=10).stdout.strip()
            update_project(pid,{"status":"running","container_id":cid})
            return {"success":True,"message":"Docker部署成功","container_id":cid}
        return {"success":True,"message":"代码已下载"}
    except Exception as e: update_project(pid,{"status":"error"}); return {"success":False,"error":str(e)[:200]}

async def stop_project(pid):
    proj=get_project(pid)
    if proj and proj.get("container_id"):
        subprocess.run(["docker","stop",proj["container_id"]],capture_output=True,timeout=30)
    update_project(pid,{"status":"stopped"})
    return {"success":True}
'''
with sftp.open('/home/ubuntu/my-evo-ai/api/hub/integrate.py','w') as f: f.write(content)
sftp.close()

# 同步更新routes_hub.py
_,o,_=C.exec_command("grep 'api.hub.integrate' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10,get_pty=True)
print(o.read().decode()[:200])
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(20)
_,o2,_=C.exec_command('sudo systemctl is-active evo.service',timeout=15,get_pty=True)
e=o2.read().decode().strip()
print(f'Evo: {e}')
if e=='active':
    for n,p in [('Hub','/hub'),('Canvas','/canvas'),('API','/api/v1/hub/discover'),('CompanyAPI','/api/v1/company/status')]:
        _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
        print(f'  {r.read().decode().strip()} {n}')
C.close()
