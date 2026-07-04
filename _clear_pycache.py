"""清除Python缓存并重启"""
import urllib.request, json, time

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# 1. 删除pyc缓存
r = cli("python3", "-c \"import shutil; shutil.rmtree('/home/ubuntu/my-evo-ai/api/routes/__pycache__', ignore_errors=True); print('done')\"")
print(f"PURGE: {r.get('stdout','')}")

# 2. 强制重载模块
r = cli("python3", "-c \"import sys; [sys.modules.pop(k) for k in list(sys.modules) if 'routes_static' in k]; print('purged')\"")
print(f"MOD_PURGE: {r.get('stdout','')}")

# 3. 重启API
r = cli("pkill", "-f \"api_server\"")
print(f"RESTART: {r.get('stdout','')}")

# 4. 验证
for i in range(30):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
        print(f"[OK] /agents -> {r.status} ({i+1}s)")
        break
    except urllib.error.HTTPError as e:
        if e.code == 404:
            time.sleep(1)
        else:
            print(f"[FAIL] {e.code}")
            break
    except:
        time.sleep(1)
else:
    print("[FAIL] /agents still 404")
