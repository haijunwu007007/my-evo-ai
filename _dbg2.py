import paramiko,time,io,sys;sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
s=paramiko.SSHClient();s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)

# Check nginx config for root route
i,o,e=s.exec_command('sudo cat /etc/nginx/sites-available/autoevoai.com',timeout=10)
time.sleep(2)
print(o.read().decode('utf-8',errors='replace')[:3000])
print('STDERR:',e.read().decode()[:200])
s.close()
