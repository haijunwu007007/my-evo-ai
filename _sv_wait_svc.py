"""等待服务启动并检查"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15)

def run(cmd, t=30):
    si,so,se = ssh.exec_command(cmd, timeout=t)
    out = so.read().decode(errors='replace')
    err = se.read().decode(errors='replace')[:500]
    return (out + err).strip()[:500]

# Wait longer
for i in range(12):
    time.sleep(5)
    out = run("curl -s http://127.0.0.1/api/v1/version 2>&1", 5)
    svc = run("sudo systemctl is-active evo.service 2>&1", 5)
    print(f"[{i*5+5}s] [{svc}] {out[:100]}")

# Check logs if still failing
out = run("sudo journalctl -u evo.service --no-pager -n 50 2>&1", 10)
print(f"\n=== LOGS ===\n{out}")

ssh.close()
