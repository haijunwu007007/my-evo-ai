"""检查服务器PG状态和API"""
import paramiko, time, ssl, urllib.request, json

host = '122.51.144.227'
user = 'ubuntu'
pw = 'Hj711201'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw, timeout=15)

# 检查PG状态
stdin, stdout, stderr = ssh.exec_command("ss -tlnp 2>/dev/null | grep 5432 || echo 'PG not on public'; sudo -u postgres psql -c \"SELECT 1 as pg_ok;\" 2>&1")
print("PG状态:", stdout.read().decode().strip()[:200])

# 重启服务
stdin2, stdout2, stderr2 = ssh.exec_command("cd /home/ubuntu/my-evo-ai && nohup venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > /dev/null 2>&1 & sleep 4 && echo 'restarted'")
print("重启:", stdout2.read().decode().strip()[:200])

ssh.close()
time.sleep(8)

# 验证API
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
base = 'https://122.51.144.227'
oks = 0
for p in ['/api/v1/health', '/api/v1/version', '/']:
    try:
        r = urllib.request.urlopen(base + p, timeout=15, context=ctx)
        data = r.read().decode()
        if p == '/api/v1/health':
            j = json.loads(data)
            print(f"健康检查 driver={j.get('driver','?')} tables={j.get('tables','?')}")
        print(f"OK [{r.status}] {p}")
        oks += 1
    except Exception as e:
        print(f"FAIL {p}: {str(e)[:80]}")
print(f"{oks}/3 OK")
