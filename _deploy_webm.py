import paramiko, time

ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
sftp=ssh.open_sftp()

sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py','/home/ubuntu/my-evo-ai/api/routes/routes_speech.py')
print('Uploaded')

sftp.close()

ssh.exec_command('sudo systemctl restart evo.service',timeout=15)
time.sleep(8)
si,so,se=ssh.exec_command('systemctl is-active evo.service')
time.sleep(1)
print('Service:',so.read().decode().strip())

import urllib.request,ssl,json
ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
time.sleep(3)
r=urllib.request.urlopen('https://autoevoai.com/api/v1/speech/status',timeout=15,context=ctx)
print('Speech:',json.loads(r.read()))

# Test with a proper sine wave webm
import struct, math
sr=16000; dur=0.5
samples=b''
for i in range(int(sr*dur)):
    v=int(math.sin(2*math.pi*440*i/sr)*30000)
    samples+=struct.pack('<h',v)

r2=requests.post('https://autoevoai.com/api/v1/speech/recognize',
    files={'file':('voice.wav',samples,'audio/wav')},
    verify=False,timeout=60)
print('Recog:',r2.json())

ssh.close()
