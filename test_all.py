import paramiko, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
def r(c,t=15):
    _,o,_=C.exec_command(c,timeout=t,get_pty=True);return o.read().decode(errors='replace')
# 1. 多平台发现
print("=== 1. 多平台发现 ===")
d=r("curl -s -m 15 http://127.0.0.1:8765/api/v1/hub/discover?source=all 2>/dev/null|head -1")[:200]
print(d[:200])
# 2. Search
print("=== 2. 搜索 ===")
s=r("curl -s -m 10 'http://127.0.0.1:8765/api/v1/hub/search?q=ollama&source=all' 2>/dev/null|head -1")[:200]
print(s[:200])
# 3. 项目列表
print("=== 3. 项目列表 ===")
p=r("curl -s -m 10 http://127.0.0.1:8765/api/v1/hub/projects 2>/dev/null|head -1")[:200]
print(p[:200])
# 4. 部署测试 - Portainer
print("=== 4. 部署 Portainer ===")
print(r("curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects/portainer01/integrate -H 'Content-Type: application/json' -d '{\"image\":\"portainer/portainer-ce\",\"port\":9000,\"internal_port\":9000}' 2>/dev/null",15)[:300])
# 5. 状态
print("=== 5. 状态 ===")
import time; time.sleep(5)
print(r("curl -s -m 10 http://127.0.0.1:8765/api/v1/hub/projects/portainer01/status 2>/dev/null",10)[:400])
C.close()
