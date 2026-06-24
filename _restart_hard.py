"""强制重启服务并等待启动完成"""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Kill and restart
s.exec_command("sudo systemctl kill evo.service")
time.sleep(1)
s.exec_command("sudo systemctl restart evo.service")
time.sleep(3)

# Wait for it to be up
for i in range(10):
    stdin, stdout, stderr = s.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>&1")
    code = stdout.read().decode().strip()
    if code == "200":
        print(f"Service UP after {3+i}s (attempt {i+1})")
        break
    time.sleep(2)
else:
    print("Service did not come up")
    stdin, stdout, stderr = s.exec_command("sudo systemctl status evo.service 2>&1 | head -5")
    print(stdout.read().decode()[:200])

s.close()
