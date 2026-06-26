import paramiko,time,os,sys
sys.stdout.reconfigure(encoding='utf-8')
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
sftp=ssh.open_sftp()

files=[
    (r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py','/home/ubuntu/my-evo-ai/api/routes/routes_speech.py'),
    (r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js','/home/ubuntu/my-evo-ai/frontend/chat_engine.js'),
    (r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html','/home/ubuntu/my-evo-ai/frontend/chat.html'),
    (r'D:\AUTO-EVO-AI-V0.1\sw.js','/home/ubuntu/my-evo-ai/sw.js'),
]
for local,remote in files:
    sftp.put(local,remote)
    print(f'{local.split(chr(92))[-1]:28s} {os.path.getsize(local)} -> OK')
sftp.close()

ssh.exec_command('sudo systemctl restart evo.service',timeout=15)
time.sleep(8)

import urllib.request,ssl
ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
r=urllib.request.urlopen('https://autoevoai.com/api/status',timeout=15,context=ctx)
print(f'API: {r.status}')
if r.status==200:
    print('All OK')
ssh.close()
