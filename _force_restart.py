"""强制重启服务器"""
import urllib.request, json, time

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"}), timeout=15).read().decode())

# Kill by PID
r = api("python3", "-c \"import os, signal; os.kill(732943, signal.SIGKILL); print('killed')\"")
print(f"KILL: {r.get('stdout','')} {r.get('stderr','')[:100]}")

# Wait for restart
for i in range(30):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/", timeout=5)
        print(f"Server back up! ({i+1}s)")
        # Check /agents now
        import urllib.error
        try:
            r2 = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
            print(f"/agents -> {r2.status}")
            print(f"Location: {r2.headers.get('location','')}")
        except urllib.error.HTTPError as e:
            print(f"/agents -> {e.code} {e.headers.get('location','')}")
            if e.code == 302:
                print("REDIRECT WORKS!")
        break
    except:
        time.sleep(1)
else:
    print("Server didn't restart")
