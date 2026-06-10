#!/usr/bin/env python3
"""部署：Gateway增强 + 环境配置 + Admin UI"""
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('122.51.144.227', username='ubuntu', password='Hj711201',
          timeout=15, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()

D = r'D:\AUTO-EVO-AI-V0.1'
R = '/home/ubuntu/my-evo-ai'

files = [
    (f'{D}\\api\\routes\\routes_gateway.py', f'{R}/api/routes/routes_gateway.py'),
    (f'{D}\\api\\routes\\routes_env.py', f'{R}/api/routes/routes_env.py'),
    (f'{D}\\api_server.py', f'{R}/api_server.py'),
    (f'{D}\\frontend\\admin.html', f'{R}/frontend/admin.html'),
]

for local, remote in files:
    sftp.put(local, remote)
    print(f'  ✅ {local.split("\\")[-1]}', flush=True)

sftp.close()

# 重启
i, o, _ = c.exec_command('pkill -f uvicorn; sleep 1; cd /home/ubuntu/my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &', timeout=10)
o.read()
time.sleep(4)

# 验证
i, o, _ = c.exec_command('curl -s http://localhost:8765/api/v1/settings | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"Settings: {d.get(\"total\",0)} 项\")"', timeout=10)
print(f'  {o.read().decode().strip()}', flush=True)

i, o, _ = c.exec_command('curl -s http://localhost:8765/api/v1/gateway/tools/github/test -X POST | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"GitHub test: {d.get(\"result\",\"?\")}\")"', timeout=10)
print(f'  {o.read().decode().strip()}', flush=True)

c.close()
print('✅ DONE', flush=True)
