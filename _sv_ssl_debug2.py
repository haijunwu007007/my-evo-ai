"""Deep debug HTTPS"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

_,o,_ = ssh.exec_command('cat /etc/nginx/sites-enabled/evo.conf', timeout=10)
print("CONFIG:")
print(o.read().decode()[:1000])

_,o2,_ = ssh.exec_command('ls -la /etc/letsencrypt/options-ssl-nginx.conf 2>&1', timeout=10)
print("SSL_OPTIONS:", o2.read().decode()[:200])

_,o3,_ = ssh.exec_command('ls -la /etc/letsencrypt/ssl-dhparams.pem 2>&1', timeout=10)
print("DHPARAM:", o3.read().decode()[:200])

# Check what nginx is actually serving on 443
_,o4,_ = ssh.exec_command('curl -v --connect-timeout 5 https://autoevoai.com 2>&1 | head -30', timeout=15)
print("CURL_VERBOSE:")
print(o4.read().decode()[:800])

ssh.close()
