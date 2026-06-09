"""全部服务器端修复：HTTPS + 搜索超时 + 清理"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# ============ Fix 1: HTTPS证书权限 ============
print("=== Fix 1: HTTPS证书权限 ===")
_,o,_ = ssh.exec_command('sudo chmod 644 /etc/letsencrypt/live/autoevoai.com/fullchain.pem 2>&1; sudo chmod 644 /etc/letsencrypt/live/autoevoai.com/privkey.pem 2>&1; sudo nginx -t 2>&1', timeout=15)
print(o.read().decode())
_,o2,_ = ssh.exec_command('sudo systemctl reload nginx 2>&1; echo RELOAD_DONE', timeout=10)
print(o2.read().decode())

# ============ Fix 2: SCP更新的agent_core.py（搜索超时修复已在本地）============
print("=== Fix 2: SCP agent_core.py ===")
sftp = ssh.open_sftp()
# 先读服务端现有版本确认
_,v,_ = ssh.exec_command('head -5 /home/ubuntu/my-evo-ai/api/agent_core.py 2>&1', timeout=5)
print("Server agent_core begins:", v.read().decode(errors='replace')[:100])

# SCP本地版本
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_core.py', 'rb') as f:
    core_content = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/agent_core.py', 'wb') as f:
    f.write(core_content)
print("SCP agent_core.py OK -", len(core_content), "bytes")

# 也SCP routes_smart_chat.py
with open(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_smart_chat.py', 'rb') as f:
    sc = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/routes/routes_smart_chat.py', 'wb') as f:
    f.write(sc)
print("SCP routes_smart_chat.py OK -", len(sc), "bytes")

# SCP routes_chat.py
with open(r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_chat.py', 'rb') as f:
    rc = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/routes/routes_chat.py', 'wb') as f:
    f.write(rc)
print("SCP routes_chat.py OK -", len(rc), "bytes")

# SCP agent_llm.py (新优先级: DeepSeek优先, 非Ollama)
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_llm.py', 'rb') as f:
    alm = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/agent_llm.py', 'wb') as f:
    f.write(alm)
print("SCP agent_llm.py OK -", len(alm), "bytes")

sftp.close()

# ============ Restart ============
print("=== Restart ===")
_,o3,_ = ssh.exec_command('sudo systemctl restart evo.service 2>&1; echo RESTART_DONE', timeout=30)
print(o3.read().decode())
time.sleep(5)

# ============ Full Verify ============
print("=== Verify ===")
tests = [
    ("GET /api/v1/version", 'curl -s http://127.0.0.1:8765/api/v1/version --max-time 10'),
    ("POST chat 你好", 'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"你好"}\' --max-time 60'),
    ("POST search", 'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"搜索Python最新版本"}\' --max-time 120'),
    ("POST draw", 'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"画一只猫"}\' --max-time 90'),
]
for label, cmd in tests:
    try:
        _,stdout,_ = ssh.exec_command(cmd, timeout=130)
        out = stdout.read().decode(errors='replace')[:300]
        print(f"[{label}] {out}")
    except Exception as e:
        print(f"[{label}] ERROR: {e}")

ssh.close()
print("=== ALL DONE ===")
