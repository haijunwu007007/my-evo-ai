import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)
stdin, stdout, stderr = s.exec_command("journalctl -u evo.service --no-pager -n 200 2>&1")
data = stdout.read().decode()
s.close()
for line in data.split("\n"):
    if "qodo" in line.lower() or "加载失败" in line or "testsigma" in line.lower() or "airbyte" in line.lower():
        print(line[:200])
if not any(x in data.lower() for x in ["qodo", "testsigma", "加载失败"]):
    print("未找到相关日志行，打印最后20行:")
    lines = data.strip().split("\n")
    for line in lines[-20:]:
        print(line[:200])
