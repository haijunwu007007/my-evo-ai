import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)
stdin, stdout, stderr = s.exec_command("journalctl -u evo.service --no-pager -n 50 2>&1")
data = stdout.read().decode()
s.close()
# Print any lines related to our new modules
for line in data.split("\n"):
    if "加载失败" in line:
        print(line[:200])
