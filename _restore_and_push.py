"""恢复chat.html + 提交 + 推送到服务器"""
import subprocess, json, urllib.request, time

# 1. 从服务器下载当前chat.html
print("1. 从服务器获取chat.html...")
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
server_html = r.read().decode(errors="replace")
print(f"   获取到 {len(server_html)} 字符")

# 2. 检查
print(f"   topbar: {server_html.count('class=\"topbar\"')}")
print(f"   cat-strip: {server_html.count('cat-strip')}")

# 3. 写回本地
with open(r"D:\AUTO-EVO-AI-V0.1\frontend\chat.html", "w", encoding="utf-8") as f:
    f.write(server_html)
print("3. 已写回本地")

# 4. 提交到Git
subprocess.run(["git", "add", "-A"], cwd=r"D:\AUTO-EVO-AI-V0.1")
subprocess.run(["git", "commit", "-m", "restore chat from server + final layout"], cwd=r"D:\AUTO-EVO-AI-V0.1")
print("4. 已提交")

# 5. 推送到GitHub
r = subprocess.run(["git", "push", "origin", "master"], 
    capture_output=True, text=True, cwd=r"D:\AUTO-EVO-AI-V0.1")
print(f"5. push: {r.returncode} {r.stdout[-100:] if r.stdout else 'ok'}")

# 6. 通知服务器重置
print("6. 通知服务器重置...")
d = json.dumps({"cmd": "git", "args": "-C /home/ubuntu/my-evo-ai fetch origin master", "timeout": 30}).encode()
req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=d,
    headers={"Content-Type": "application/json"}, method="POST")
urllib.request.urlopen(req, timeout=40)

d = json.dumps({"cmd": "git", "args": "-C /home/ubuntu/my-evo-ai reset --hard origin/master", "timeout": 30}).encode()
req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=d,
    headers={"Content-Type": "application/json"}, method="POST")
urllib.request.urlopen(req, timeout=40)
print("   已重置")

# 7. 重启
d = json.dumps({"cmd": "pkill", "args": "-f api_server", "timeout": 5}).encode()
req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=d,
    headers={"Content-Type": "application/json"}, method="POST")
try: urllib.request.urlopen(req, timeout=10)
except: pass
time.sleep(3)
print("   已杀进程")

# 写重启脚本
py = "import subprocess,os; os.chdir('/home/ubuntu/my-evo-ai'); p=subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],stdout=open('/tmp/evo_api.log','w'),stderr=2); print('OK pid='+str(p.pid))"
hex_py = py.encode().hex()
d2 = json.dumps({"cmd": "python3", "args": f"-c \"open('/tmp/restart.py','w').write(bytes.fromhex('{hex_py}').decode()); print('wrote')\"", "timeout": 10}).encode()
req2 = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=d2,
    headers={"Content-Type": "application/json"}, method="POST")
urllib.request.urlopen(req2, timeout=10)

d3 = json.dumps({"cmd": "python3", "args": "/tmp/restart.py", "timeout": 15}).encode()
req3 = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=d3,
    headers={"Content-Type": "application/json"}, method="POST")
try:
    r = urllib.request.urlopen(req3, timeout=20)
    print(f"   重启: {r.read().decode(errors='replace')[:100]}")
except Exception as e:
    print(f"   重启: {str(e)[:50]}")

# 8. 验证
time.sleep(10)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"\n首页: {r.status} tb={c.count('toolbar-top')} topbar={c.count('class=\"topbar\"')} cat-strip={c.count('cat-strip')}")
