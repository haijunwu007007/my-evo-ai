"""Configure uvicorn to serve HTTPS on port 8765 (already open)"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# 1. Check cert files exist
_,o1,_ = ssh.exec_command('ls -la /etc/nginx/ssl/ 2>/dev/null; ls -la /etc/ssl/autoevoai/ 2>/dev/null', timeout=5)
print('CERTS:', o1.read().decode(errors='replace')[:300])

# 2. Find actual cert path
_,o2,_ = ssh.exec_command('find /etc -name "fullchain.pem" 2>/dev/null | head -5', timeout=5)
print('CERT_PATH:', o2.read().decode(errors='replace')[:200])

# 3. Modify evo.service to add SSL args
_,o3,_ = ssh.exec_command('sudo cat /etc/systemd/system/evo.service | head -30', timeout=5)
svc = o3.read().decode(errors='replace')
print('CURRENT_SVC:', svc[:300])

# 4. Check if OpenResty is used instead of nginx
_,o4,_ = ssh.exec_command('which openresty 2>/dev/null; ls /usr/local/openresty/ 2>/dev/null | head -3', timeout=5)
print('OPENRESTY:', o4.read().decode(errors='replace')[:200])

ssh.close()
