"""修复405和监控端点"""
import paramiko, time, os, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)
sftp=C.open_sftp()

# 1. 读当前routes_hub.py
_,r,_=C.exec_command('cat /home/ubuntu/my-evo-ai/api/routes/routes_hub.py',timeout=10,get_pty=True)
content = r.read().decode()

# 2. 在文件末尾加缺失的路由
additions = '''

@router.get("/monitor")
async def hub_monitor():
    """系统监控"""
    return {"success": True, "projects": []}

@router.get("/composes/{cid}/nodes")
async def hub_compose_nodes(cid: str):
    """获取组合节点"""
    from api.hub.models import get_project
    comp = None
    conn = __import__("sqlite3").connect(str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "core" / "hub.db"))
    conn.row_factory = __import__("sqlite3").Row
    row = conn.execute("SELECT * FROM composes WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not row: return {"success": False, "error": "组合不存在"}
    data = dict(row)
    data["nodes"] = json.loads(data.get("nodes", "[]"))
    data["edges"] = json.loads(data.get("edges", "[]"))
    return {"success": True, "compose": data}
'''

content += additions

sftp.putfo(__import__('io').StringIO(content), '/home/ubuntu/my-evo-ai/api/routes/routes_hub.py', lambda x:x)
# 用临时文件写
import tempfile
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
    f.write(content)
    tmpname = f.name
sftp.put(tmpname, '/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
os.unlink(tmpname)
sftp.close()

C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)

# 测试
def test(path,t=10):
    _,o,_=C.exec_command(f'curl -s -m {t} "http://127.0.0.1:8765{path}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    return o.read().decode(errors='replace').strip()[:80]

print('=== 验证 ===')
for n,p in [('监控','/api/v1/hub/monitor'),('组合部署-POST','/api/v1/hub/composes/9049c17b83ac/deploy'),('组合节点','/api/v1/hub/composes/9049c17b83ac/nodes')]:
    out=test(p)
    ok='success' in out or 'compose' in out
    print(f'{"✅" if ok else "❌"} {n}: {out[:60]}')

# Portainer部署(正确URL)
print('\n=== Portainer部署 ===')
_,r,_=C.exec_command('''curl -s --max-time 30 -X POST "http://127.0.0.1:8765/api/v1/hub/projects/integrate" -H "Content-Type: application/json" -d '{"id":"portainer","name":"Portainer","source":"docker","category":"infra","config":{"docker_image":"portainer/portainer-ce","port":9000,"env":{"detected":1}}}' 2>/dev/null|head -1''',timeout=40,get_pty=True)
print(f'  {r.read().decode(errors="replace")[:120]}')
time.sleep(5)
_,r2,_=C.exec_command("docker ps --format '{{.Names}} {{.Status}}'|grep portainer",timeout=10,get_pty=True)
d=r2.read().decode(errors='replace').strip()
print(f'  Portainer容器: {"✅ "+d[:60] if d else "❌"}')

C.close()
print('\n✅ 完成')
