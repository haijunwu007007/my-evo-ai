"""SCP nginx config + reload"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

sftp = ssh.open_sftp()
local = r'D:\AUTO-EVO-AI-V0.1\_evo_nginx.conf'
remote = '/home/ubuntu/_evo_nginx.conf'
sftp.put(local, remote)
sftp.close()

# Copy to nginx dir and reload
_,o1,_ = ssh.exec_command('sudo cp /home/ubuntu/_evo_nginx.conf /etc/nginx/sites-enabled/evo.conf && sudo nginx -t 2>&1', timeout=10)
print('NGINX TEST:', o1.read().decode()[:300])

_,o2,_ = ssh.exec_command('sudo systemctl reload nginx 2>&1', timeout=10)
print('RELOAD:', o2.read().decode()[:200])

time.sleep(2)

# Test HTTPS
_,o3,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com/api/v1/version --max-time 10', timeout=15)
print('HTTPS:', o3.read().decode().strip())

# Test HTTP 
_,o4,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://autoevoai.com/api/v1/version --max-time 10', timeout=15)
print('HTTP:', o4.read().decode().strip())

ssh.close()
