"""Check and fix HTTPS on public server"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Check cert files
_,o1,_ = ssh.exec_command('ls -la /etc/nginx/ssl/ 2>&1', timeout=10)
print("SSL DIR:", o1.read().decode()[:500])

# Check nginx config
_,o2,_ = ssh.exec_command('ls -la /etc/nginx/conf.d/ 2>&1', timeout=10)
print("CONF:", o2.read().decode()[:500])

# Test nginx
_,o3,_ = ssh.exec_command('sudo nginx -t 2>&1', timeout=10)
print("NGINX TEST:", o3.read().decode()[:500])

# Check if port 443 is listening
_,o4,_ = ssh.exec_command('ss -tlnp | grep 443', timeout=10)
print("443:", o4.read().decode()[:300])

# Try curl using the internal IP
_,o5,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/version --max-time 5', timeout=10)
print("NGINX_80:", o5.read().decode().strip())

# Check for any nginx errors in logs
_,o6,_ = ssh.exec_command('sudo tail -20 /var/log/nginx/error.log 2>&1', timeout=10)
print("NGINX_ERR:", o6.read().decode()[:500])

ssh.close()
