import paramiko, time
ssh = paramiko.SSHClient(); ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)

# Read the root handler code
si,so,se = ssh.exec_command("sed -n '211,225p' /home/ubuntu/my-evo-ai/api_server.py", timeout=5)
time.sleep(2)
print('ROOT HANDLER:')
print(so.read().decode()[:500])

# Read Nginx config
si2,so2,se2 = ssh.exec_command("grep -i 'cache\\|proxy_cache' /etc/nginx/sites-available/autoevoai.com", timeout=5)
time.sleep(2)
print('NGINX CACHE:')
print(so2.read().decode()[:500])

# Clear Nginx cache
si3,so3,se3 = ssh.exec_command('sudo rm -rf /var/cache/nginx/* && sudo systemctl reload nginx 2>&1', timeout=10)
time.sleep(2)
print('CACHE CLEAR:', so3.read().decode().strip()[:200])

ssh.close()
