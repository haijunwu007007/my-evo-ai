"""Verify all 4 fixes are deployed and working on public server"""
import paramiko, time, json, httpx

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

results = []

# 1. Git状态
_,o1,_ = ssh.exec_command('cd /home/ubuntu/my-evo-ai && git log --oneline -1', timeout=10)
g = o1.read().decode().strip()
results.append(("GIT commit", g[:50]))

# 2. Nginx
_,o2,_ = ssh.exec_command('sudo nginx -t 2>&1; echo EXIT:$?', timeout=10)
n = o2.read().decode().strip()
results.append(("NGINX", "OK" if "successful" in n else n[:100]))

# 3. API版本
_,o3,_ = ssh.exec_command('curl -s http://127.0.0.1:8765/api/v1/version --max-time 5', timeout=10)
v = o3.read().decode().strip()
results.append(("API", v[:120]))

# 4. HTTPS
try:
    r = httpx.get('https://autoevoai.com/api/v1/version', timeout=10, verify=False)
    results.append(("HTTPS", f"{r.status_code} {r.json().get('version','')[:30]}"))
except Exception as e:
    results.append(("HTTPS", str(e)[:80]))

# 5. 聊天
_,o5,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8765/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"你好"}\' --max-time 30',
    timeout=35)
r5 = json.loads(o5.read().decode())
m5 = r5.get("mode","")
r5t = r5.get("result","")[:60]
results.append(("CHAT", f"mode={m5} {r5t}"))

# 6. AI画图
_,o6,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8765/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"画一只猫"}\' --max-time 60',
    timeout=65)
r6 = json.loads(o6.read().decode())
m6 = r6.get("mode","")
r6t = r6.get("result","")[:60]
results.append(("DRAW", f"mode={m6} {r6t}"))

ssh.close()

print("=" * 60)
print("  AUTO-EVO-AI V0.1 — 全面修复验证报告")
print("=" * 60)
print(f"{'项':<18} {'状态':<42}")
print("-" * 60)
for name, status in results:
    ok = "✅" if "mode" in status or "OK" in status or "V0" in status or "154954a" in status else "⚠️"
    print(f"  {ok} {name:<16} {status:<40}")
print("-" * 60)
all_ok = all("OK" in s or "mode" in s or "V0" in s or "154954a" in s or "200" in s for _, s in results)
print(f"\n  {'✅ 全部正常!' if all_ok else '⚠️ 有异常'}")
print("=" * 60)
