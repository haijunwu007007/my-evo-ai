"""验证公网"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

def run(cmd):
    stdin,stdout,stderr = ssh.exec_command(cmd, timeout=10)
    return stdout.read().decode(errors='replace')[:1000]

print("=== nginx conf ===")
print(run("cat /etc/nginx/sites-enabled/evo.conf"))

print("=== curl test ===")
print(run("curl -sk https://122.51.144.227/api/v1/version"))

print("=== localhost 8765 ===")
print(run("curl -s http://127.0.0.1:8765/api/v1/version"))

print("=== localhost 8766 ===")
print(run("curl -s http://127.0.0.1:8766/api/v1/version"))

print("=== evo.service active ===")
print(run("sudo systemctl is-active evo.service"))

ssh.close()
