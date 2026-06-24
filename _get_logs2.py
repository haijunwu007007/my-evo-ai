import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)
stdin, stdout, stderr = s.exec_command("journalctl -u evo.service --no-pager -n 300 2>&1")
data = stdout.read().decode()
s.close()
# Find lines about module loading errors
for line in data.split("\n"):
    if any(kw in line.lower() for kw in ["error", "fail", "加载失", "cannot import", "qodo", "testsigma"]):
        print(line[:200])
print("---")
lines = data.strip().split("\n")
for line in lines[-10:]:
    print(line[:200])
