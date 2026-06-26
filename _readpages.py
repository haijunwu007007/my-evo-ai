import paramiko, time
s=paramiko.SSHClient();s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
i,o,e=s.exec_command('cat /home/ubuntu/my-evo-ai/frontend/pages/login.html',timeout=5)
time.sleep(2);print('LOGIN:',o.read().decode('utf-8',errors='replace')[:2000])
s.close()
