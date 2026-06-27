import paramiko,time,os
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
sftp=ssh.open_sftp()
local=r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py'
sftp.put(local,'/home/ubuntu/my-evo-ai/api/routes/routes_speech.py')
sftp.close()
print('Uploaded',os.path.getsize(local))
ssh.exec_command('sudo systemctl restart evo.service',timeout=15)
time.sleep(15)
import urllib.request,ssl
ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
r=urllib.request.urlopen('https://autoevoai.com/api/status',timeout=15,context=ctx)
import json
print('Status:',json.loads(r.read())['status'])
ssh.close()
