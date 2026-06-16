import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)

old='''
async def hub_integrate(pid: str):
    """一键集成：git clone → 分析 → 部署"""
    proj = get_project(pid)
    if not proj: return {"success": False, "error": "项目不存在"}
    update_project(pid, {"status": "downloading"})

    # git clone
    local_dir = HUBSRC / proj["name"]
    repo = proj.get("repo_url","")
    if not repo: return {"success": False, "error": "没有仓库地址"}

    clone_ok = await git_clone(repo, local_dir)
    if not clone_ok:
        update_project(pid, {"status": "error"})
        return {"success": False, "error": "下载失败（网络/超时）"}

    update_project(pid, {"status": "deploying"})
    port = free_port()
    result = await deploy(proj, local_dir, port)
    if result.get("success"):
        update_project(pid, {"status": "running", "port": port,'''

new='''
async def hub_integrate(pid: str):
    """一键集成：分析 → 部署"""
    proj = get_project(pid)
    if not proj: return {"success": False, "error": "项目不存在"}
    update_project(pid, {"status": "deploying"})
    result = await deploy_project(pid, {"port": 0})
    if result.get("success"):
        update_project(pid, {"status": "running", "port": result.get("port",0),'''

# SFTP to read and replace
_,o,_=C.exec_command("cat /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10,get_pty=True)
content=o.read().decode()
content=content.replace(old.strip(),new.strip())
sftp=C.open_sftp()
with sftp.open('/tmp/hub_fixed.py','w') as f:
    f.write(content)
sftp.close()
C.exec_command("sudo cp /tmp/hub_fixed.py /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10)
import time
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(8)
_,o2,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
r=o2.read().decode().strip()
_,o3,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:8765/api/v1/hub/discover',timeout=10,get_pty=True)
print(f"Evo:{r} Hub:{o3.read().decode().strip()}")
C.close()
