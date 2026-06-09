"""Debug HTTPS on public server"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

_,o,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com --max-time 10 2>&1', timeout=15)
print("HTTPS_AUTOEVOAI:", o.read().decode().strip())

_,o2,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://localhost --max-time 10 2>&1', timeout=15)
print("HTTPS_LOCAL:", o2.read().decode().strip())

_,o3,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost --max-time 5 2>&1', timeout=10)
print("HTTP_LOCAL:", o3.read().decode().strip())

_,o4,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://122.51.144.227/api/v1/version --max-time 5 2>&1', timeout=10)
print("HTTP_IP:", o4.read().decode().strip())

_,o5,_ = ssh.exec_command('sudo ss -tlnp 2>&1', timeout=10)
print("LISTEN:", o5.read().decode()[:500])

_,o6,_ = ssh.exec_command('sudo tail -10 /var/log/nginx/error.log 2>&1', timeout=10)
print("ERR:", o6.read().decode()[:500])

ssh.close()
