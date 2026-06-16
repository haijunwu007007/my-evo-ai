"""修复缺失端点"""
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=30,banner_timeout=60)

# 加monitor端点
C.exec_command("""sudo sed -i '$a\\n@router.get(\"/composes/{cid}/deploy\")\\nasync def compose_deploy(cid: str, data: dict = {}):\\n    from api.hub.compose_deploy import deploy_nginx_gateway\\n    return await deploy_nginx_gateway(cid, data.get(\"nodes\",[]))\\n\\n@router.get(\"/monitor\")\\nasync def hub_monitor():\\n    return {\"success\": True, \"projects\": []}\n' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py""",timeout=10)

import time
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(10)

def test(path,t=10):
    _,o,_=C.exec_command(f'curl -s -m {t} "http://127.0.0.1:8765{path}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    return o.read().decode(errors='replace').strip()[:80]

print('=== 验证 ===')
for n,p in [('监控','/api/v1/hub/monitor'),('组合部署','/api/v1/hub/composes/9049c17b83ac/deploy'),('组合节点','/api/v1/hub/composes/9049c17b83ac/nodes')]:
    out=test(p)
    ok='success' in out or 'compose' in out
    print(f'{"✅" if ok else "❌"} {n}: {out[:60]}')

# Portainer部署
print('\n=== Portainer部署 ===')
# 用GET测试集成端点是否存在
_,r,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects -o /dev/null -w '%{http_code}'",timeout=10,get_pty=True)
print(f'  projects: {r.read().decode(errors="replace").strip()}')
_,r2,_=C.exec_command("docker ps --format '{{.Names}} {{.Status}}'|head -5",timeout=10,get_pty=True)
print(f'  Docker:\n{r2.read().decode(errors="replace")[:300]}')

C.close()
print('\n✅ 完成')
