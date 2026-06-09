"""排查公网502问题"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

def run(cmd):
    stdin,stdout,stderr = ssh.exec_command(cmd, timeout=10)
    return stdout.read().decode(errors='replace')[:2000]

# 1. nginx sites
print("=== nginx sites ===")
print(run("ls /etc/nginx/sites-enabled/"))
print(run("cat /etc/nginx/sites-enabled/default 2>/dev/null | head -40"))

# 2. ports
print("=== listening ports ===")
print(run("ss -tlnp | head -20"))

# 3. service file
print("=== evo.service ===")
print(run("cat /etc/systemd/system/evo.service"))

# 4. evo.service env
print("=== env.conf ===")
print(run("cat /etc/systemd/system/evo.service.d/env.conf"))

# 5. try restart again and wait
print("=== restarting ===")
print(run("sudo systemctl restart evo.service"))
time.sleep(5)
print(run("sudo systemctl status evo.service 2>&1 | head -15"))

# 6. test local
print("=== local test ===")
print(run("curl -s http://127.0.0.1:8765/api/v1/version 2>&1 | head -5"))
print(run("curl -s http://127.0.0.1:8766/api/v1/version 2>&1 | head -5"))

ssh.close()
print("DONE")
