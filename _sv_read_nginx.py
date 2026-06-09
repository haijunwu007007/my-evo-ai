"""Read nginx config"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

_,o,_ = ssh.exec_command('cat /etc/nginx/sites-enabled/evo.conf', timeout=5)
print(o.read().decode(errors='replace'))

ssh.close()
