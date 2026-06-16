import paramiko, time, json
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)

# 查看hub路由的integrate实现
_,o,_=C.exec_command("grep -A15 'hub_integrate' /home/ubuntu/my-evo-ai/api/routes/routes_hub.py",timeout=10,get_pty=True)
print(o.read().decode()[:500])
C.close()
