import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 1. Add
r=C.exec_command("curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects -H 'Content-Type: application/json' -d '{\"id\":\"portainer\",\"name\":\"Portainer\",\"source\":\"docker\",\"description\":\"Docker管理面板\"}'",timeout=10,get_pty=True)
print("1.添加:",r[1].read().decode(errors='replace')[:150])
# 2. Deploy (port 0 = auto)
r2=C.exec_command("curl -s --max-time 60 -X POST http://127.0.0.1:8765/api/v1/hub/projects/portainer/integrate -H 'Content-Type: application/json' -d '{\"image\":\"portainer/portainer-ce\",\"port\":0,\"internal_port\":9000}' 2>/dev/null",timeout=70,get_pty=True)
print("2.部署:",r2[1].read().decode(errors='replace')[:200])
# 3. Wait for deploy
time.sleep(10)
# 4. Check status
r3=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects/portainer/status 2>/dev/null",timeout=10,get_pty=True)
print("3.状态:",r3[1].read().decode(errors='replace')[:500])
# 5. Docker ps
r4=C.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'|grep -i portainer",timeout=10,get_pty=True)
print("4.Docker:",r4[1].read().decode(errors='replace')[:200])
C.close()
