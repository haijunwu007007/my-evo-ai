import paramiko, time, sys
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 1. Add project
C.exec_command("curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects -H 'Content-Type: application/json' -d '{\"id\":\"pt-test\",\"name\":\"Portainer\",\"source\":\"docker\",\"repo_url\":\"\",\"description\":\"Docker管理面板\"}'",timeout=10)
print("1. 项目已添加")
# 2. Deploy Portainer
r=C.exec_command("curl -s --max-time 120 -X POST http://127.0.0.1:8765/api/v1/hub/projects/pt-test/integrate -H 'Content-Type: application/json' -d '{\"image\":\"portainer/portainer-ce\",\"port\":9000,\"internal_port\":9000}' 2>/dev/null",timeout=130,get_pty=True)
print("2. 部署:",r[1].read().decode(errors='replace')[:300])
# 3. Status
time.sleep(3)
r2=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects/pt-test/status 2>/dev/null",timeout=10,get_pty=True)
print("3. 状态:",r2[1].read().decode(errors='replace')[:300])
C.close()
