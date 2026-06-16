import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_hub.py','/home/ubuntu/my-evo-ai/api/routes/routes_hub.py')
sftp.close()
import time
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(8)
_,o,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print(f'Evo: {o.read().decode().strip()}')
# Test
pid='504e1bff5b8c'
_,o2,_=C.exec_command(f'curl -s --max-time 30 -X POST http://127.0.0.1:8765/api/v1/hub/projects/{pid}/integrate -H "Content-Type: application/json" -d \'{{"port":9000}}\'',timeout=40,get_pty=True)
print(f'Deploy: {o2.read().decode()[:300]}')
C.close()
