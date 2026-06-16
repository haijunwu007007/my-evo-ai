import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\canvas.html','/home/ubuntu/my-evo-ai/frontend/canvas.html')
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.close()
C.exec_command("sudo sed -i '/def hub_list_composes/a\\\\n@router.put(\"\\/composes\\/{cid}\")\\nasync def hub_update_compose(cid: str, data: dict):\\n    data[\"id\"] = cid\\n    add_compose(data)\\n    return {\"success\": True}' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10)
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
tests=[('Hub','/hub'),('Canvas','/canvas'),('Composes','/api/v1/hub/composes'),('Discover','/api/v1/hub/discover?source=gitee'),('Projects','/api/v1/hub/projects')]
for n,p in tests:
    _,r,_=C.exec_command(f'curl -s --max-time 10 "http://127.0.0.1:8765{p}" 2>/dev/null|head -1',timeout=15,get_pty=True)
    o=r.read().decode(errors='replace').strip()[:60]
    ok=o.startswith('{') or o.startswith('<!')
    print(f'{"✅" if ok else "❌"} {n}: {o[:50]}')
C.close()
