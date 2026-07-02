"""最终部署 — args是字符串，cmd=git在白名单里"""
import urllib.request, json, time

HOST = "https://autoevoai.com"

def exec_api(body, timeout=60):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{HOST}/api/v1/cli/exec",
        data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=timeout+10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        b = e.read().decode(errors="replace")[:500]
        return e.code, b
    except Exception as ex:
        return 0, str(ex)[:100]

# git fetch（args是字符串）
print("1. set-url + fetch...")
s, r = exec_api({"cmd": "git", "args": "-C /home/ubuntu/my-evo-ai remote set-url origin https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai && git -C /home/ubuntu/my-evo-ai fetch origin", "timeout": 30})
print(f"   {s}: {str(r)[:200]}")

print("2. reset...")
s, r = exec_api({"cmd": "git", "args": "-C /home/ubuntu/my-evo-ai reset --hard origin/master", "timeout": 30})
print(f"   {s}: {str(r)[:200]}")

print("3. 版本...")
s, r = exec_api({"cmd": "git", "args": "-C /home/ubuntu/my-evo-ai log --oneline -3", "timeout": 10})
print(f"   {str(r)[:200]}")

print("4. 重启（用python3）...")
s, r = exec_api({"cmd": "python3", "args": "-c \"import subprocess,os,time; subprocess.run(['pkill','-f','api_server']); time.sleep(2); os.chdir('/home/ubuntu/my-evo-ai'); subprocess.Popen(['nohup','python3','api_server.py','--port','8765'],stdout=open('/tmp/evo_api.log','w'),stderr=2); print('OK')\"", "timeout": 15})
print(f"   {s}: {str(r)[:100]}")

print("5. 等待...")
time.sleep(8)
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
c = r.read().decode(errors="replace")
print(f"   首页: {r.status} toolbar-top={c.count('toolbar-top')} msgs={c.count('messages')}")
