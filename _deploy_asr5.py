import paramiko,time,os,urllib.request,ssl,json
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
sftp=ssh.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py','/home/ubuntu/my-evo-ai/api/routes/routes_speech.py')
print('Uploaded:',os.path.getsize(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py'))
sftp.close()
ssh.exec_command('sudo systemctl restart evo.service',timeout=15);time.sleep(15)
ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
r=urllib.request.urlopen('https://autoevoai.com/api/status',timeout=30,context=ctx);print('API:',json.loads(r.read()).get('status'))
r2=urllib.request.urlopen('https://autoevoai.com/api/v1/speech/status',timeout=30,context=ctx);print('Vosk:',json.loads(r2.read()))
ssh.close()
