import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 清理失败的容器
C.exec_command("docker rm -f evo-Portainer 2>/dev/null",timeout=10)
# 用动态端口部署Portainer
r=C.exec_command("curl -s --max-time 60 -X POST http://127.0.0.1:8765/api/v1/hub/projects/pt-demo/integrate -H 'Content-Type: application/json' -d '{\"image\":\"portainer/portainer-ce\",\"port\":0,\"internal_port\":9000}' 2>/dev/null",timeout=70,get_pty=True)
print("部署:",r[1].read().decode(errors='replace')[:300])
import time;time.sleep(8)
_,o,_=C.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'|grep evo",timeout=10,get_pty=True)
print("容器:",o.read().decode(errors='replace')[:200])
_,o2,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8000 2>/dev/null|head -1",timeout=10,get_pty=True)
print("8000:",o2.read().decode(errors='replace')[:50])
_,o3,_=C.exec_command("curl -s http://127.0.0.1:8765/api/v1/hub/projects/pt-demo/status -m 5 2>/dev/null",timeout=10,get_pty=True)
print("状态:",o3.read().decode(errors='replace')[:300])
C.close()
