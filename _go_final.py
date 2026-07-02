"""最终部署 — 单步执行，不用shell操作符"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def cli(cmd, args="", timeout=30):
    data = json.dumps({"cmd": cmd, "args": args, "timeout": timeout}).encode()
    req = urllib.request.Request(f"{HOST}/api/v1/cli/exec",
        data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=timeout+10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as ex:
        return 0, str(ex)[:100]

# 1. 设置ghproxy
print("1. set-url...")
s, r = cli("git", f"-C /home/ubuntu/my-evo-ai remote set-url origin https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai", 10)
print(f"   {s}: {str(r)[:100]}")

# 2. fetch
print("2. fetch...")
s, r = cli("git", "-C /home/ubuntu/my-evo-ai fetch origin", 30)
print(f"   {s}: {str(r)[:200]}")

# 3. reset
print("3. reset...")
s, r = cli("git", "-C /home/ubuntu/my-evo-ai reset --hard origin/master", 30)
print(f"   {s}: {str(r)[:200]}")

# 4. 版本
print("4. 版本...")
s, r = cli("git", "-C /home/ubuntu/my-evo-ai log --oneline -3", 10)
print(f"   {str(r)[:200]}")

# 5. 重启
print("5. 重启...")
s, r = cli("pkill", "-f api_server", 5)
print(f"   kill: {s}")
time.sleep(3)
cli("bash", "-c 'cd /home/ubuntu/my-evo-ai && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &'", 5)
# 试python3方式
s, r = cli("python3", "-c \"import subprocess,os,time; os.chdir('/home/ubuntu/my-evo-ai'); subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],stdout=open('/tmp/evo_api.log','w'),stderr=2); print('OK')\"", 15)
print(f"   start: {s} {str(r)[:100]}")

# 6. 验证
print("6. 等待...")
time.sleep(10)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} tb={c.count('toolbar-top')} msg={c.count('messages')}")
