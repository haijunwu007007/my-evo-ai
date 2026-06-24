"""最终修复：强制重启并等待"""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Kill process
print("Killing evo service...")
s.exec_command("sudo systemctl kill evo.service")
time.sleep(2)

# Wait for it to stop completely
for _ in range(5):
    stdin, stdout, _ = s.exec_command("systemctl is-active evo.service 2>&1")
    status = stdout.read().decode().strip()
    if status == "inactive" or status == "failed":
        s.exec_command("sudo systemctl reset-failed evo.service 2>/dev/null")
        break
    time.sleep(2)

print("Starting evo service...")
s.exec_command("sudo systemctl start evo.service")
time.sleep(3)

# Wait for it to be up
for i in range(15):
    stdin, stdout, _ = s.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>&1")
    code = stdout.read().decode().strip()
    if code == "200":
        print(f"Service UP ({code}) after {3+i}s")
        break
    time.sleep(2)
else:
    print("Service did not come up")
    stdin, stdout, _ = s.exec_command("systemctl status evo.service 2>&1 | head -5")
    print(stdout.read().decode()[:200])

s.close()
