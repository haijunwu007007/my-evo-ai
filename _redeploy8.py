"""重新部署v8 — 加上Content-Type头"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def exec_cmd(cmd_str, timeout=60):
    """用python3执行命令，正确设置JSON头"""
    safe = cmd_str.replace("'", "'\\''")
    body = json.dumps({"cmd": "python3", "args": f"-c '{safe}'", "timeout": timeout}).encode()
    req = urllib.request.Request(f"{HOST}/api/v1/cli/exec",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=timeout+10)
        return r.status, r.read().decode(errors="replace")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]
    except Exception as e:
        return 0, str(e)[:100]

# Step 1: 拉取
print("1. 拉最新代码...")
sc = "import subprocess,os; os.chdir('/home/ubuntu/my-evo-ai'); r=subprocess.run(['git','remote','set-url','origin','https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai'],capture_output=True,text=True); r=subprocess.run(['git','fetch','origin'],capture_output=True,text=True); r=subprocess.run(['git','reset','--hard','origin/master'],capture_output=True,text=True); print(r.returncode,r.stdout[:200])"
s, r = exec_cmd(sc, 60)
print(f"   {s}: {r[:300]}")

# Step 2: 确认版本
print("\n2. 版本确认...")
s, r = exec_cmd("import subprocess; print(subprocess.run(['git','-C','/home/ubuntu/my-evo-ai','log','--oneline','-3'],capture_output=True,text=True).stdout)", 10)
print(f"   {r[:200]}")

# Step 3: 重启
print("\n3. 重启...")
sc2 = "import subprocess,os,time; subprocess.run(['pkill','-f','api_server'],capture_output=True); time.sleep(2); os.chdir('/home/ubuntu/my-evo-ai'); subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],stdout=open('/tmp/evo_api.log','w'),stderr=subprocess.STDOUT); print('RESTART_OK')"
s, r = exec_cmd(sc2, 15)
print(f"   {r[:100]}")

# Step 4: 验证
print("\n4. 验证...")
time.sleep(6)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} toolbar-top={c.count('toolbar-top')} msgs={c.count('messages')}")
r2 = urllib.request.urlopen("https://autoevoai.com/billion-os.html", timeout=10)
print(f"   billion: {r2.status}")
