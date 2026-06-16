import paramiko, time, json, hashlib
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)

# 1. 添加Portainer项目
pid = hashlib.md5(b"portainer-test").hexdigest()[:12]
proj_data = json.dumps({
    "id": pid,
    "name": "Portainer",
    "source": "docker",
    "repo_url": "https://github.com/portainer/portainer",
    "description": "Docker管理面板",
    "category": "infra",
    "status": "ready"
})

_,o,_=C.exec_command(
    f'curl -s -X POST http://127.0.0.1:8765/api/v1/hub/projects '
    f'-H "Content-Type: application/json" -d \'{proj_data}\'', timeout=10,get_pty=True)
print("1.添加:",o.read().decode()[:200])

# 2. 测试部署
cfg = json.dumps({"port":9000,"env_vars":{}})
_,o2,_=C.exec_command(
    f'curl -s --max-time 120 -X POST http://127.0.0.1:8765/api/v1/hub/projects/{pid}/integrate '
    f'-H "Content-Type: application/json" -d \'{{"port":9000}}\'', timeout=130,get_pty=True)
r2=o2.read().decode().strip()
print("2.部署:",r2[:300])

# 3. 检查状态
time.sleep(5)
_,o3,_=C.exec_command(f'curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects',timeout=10,get_pty=True)
all_proj=o3.read().decode()
print("3.项目列表:",all_proj[:300])

# 4. 检查Docker容器
_,o4,_=C.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null|head -5',timeout=10,get_pty=True)
print("4.容器:",o4.read().decode()[:300])

C.close()
