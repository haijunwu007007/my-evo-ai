import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 看routes_hub.py的import行
_,o,_=C.exec_command("grep 'from api.hub.integrate import' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10,get_pty=True)
imports=o.read().decode().strip()
print("需要:",imports)
# 看integrate.py有什么函数
_,o2,_=C.exec_command("grep '^def \\|^async def' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10,get_pty=True)
print("已有:",o2.read().decode()[:300])
# 给integrate.py加别名
needed=["git_clone","deploy","free_port","HUBSRC"]
C.exec_command(f"echo '\n# 别名(兼容routes_hub)\nasync def git_clone(r,d): return await deploy_project(r,{{\"repo\":r,\"local_dir\":str(d)}})\ndef free_port(): return _find_free_port()\nHUBSRC=BASE_DIR\ndeploy=deploy_project\n' >> /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
import time
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(10)
_,o3,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print("Evo:",o3.read().decode().strip())
C.close()
