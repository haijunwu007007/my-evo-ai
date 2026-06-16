import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# Upload complete clean file
sftp=C.open_sftp()
sftp.put(r'D:\AUTO-EVO-AI-V0.1\api\hub\integrate.py','/home/ubuntu/my-evo-ai/api/hub/integrate.py')
sftp.close()
_,o,_=C.exec_command("head -8 /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10,get_pty=True)
print(o.read().decode()[:400])
import time
C.exec_command("sudo systemctl restart evo.service",timeout=10)
time.sleep(10)
_,o2,_=C.exec_command("sudo systemctl is-active evo.service",timeout=10,get_pty=True)
print("Evo:",o2.read().decode().strip())
_,o3,_=C.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/v1/hub/discover',timeout=10,get_pty=True)
print("Hub:",o3.read().decode().strip())
C.close()
