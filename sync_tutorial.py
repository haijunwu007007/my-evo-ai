#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\frontend\tutorial.html', '/home/ubuntu/my-evo-ai/frontend/tutorial.html')
# 在hub_static.py加引导路由
_,o,_=C.exec_command("grep -l tutorial /home/ubuntu/my-evo-ai/api/routes/hub_static.py 2>/dev/null||echo no",timeout=10,get_pty=True)
if 'no' in o.read().decode():
    C.exec_command("sudo sed -i '/frontend\\/hub.html/a\\\\n@router.get(\"\\/tutorial\")\\nasync def tutorial_page():\\n    return FileResponse(FRONTEND / \"tutorial.html\")' /home/ubuntu/my-evo-ai/api/routes/hub_static.py",timeout=10)
    print('引导路由已添加')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(5)
_,o2,_=C.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/tutorial",timeout=10,get_pty=True)
print(f'Tutorial: {o2.read().decode().strip()}')
C.close()
