"""修复/agents路由 - 改为重定向到/frontend/agents.html"""
import urllib.request, json, base64

REMOTE = "https://autoevoai.com"

def api(cmd, args=""):
    p = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request(f"{REMOTE}/api/v1/cli/exec", data=p, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

# 读取现存routes_static.py
r = api("python3", "-c " + "'" * 3 + "import binascii; print(binascii.hexlify(open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py','rb').read()).decode())" + "'" * 3)
# 直接用hex解码：从现存文件中找到/agents路由定义并修改
# 简单方法：写一个新版本到服务器
local = open(r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py", "r", encoding="utf-8").read()

# 把/agents的处理函数改为重定向
old = '''@router.get("/agents")
async def agents_page():
    p = BASE_DIR / "frontend" / "agents.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)'''

# Actually the indentation differs. Let me just do a direct string replacement
new = '''@router.get("/agents")
async def agents_page():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/frontend/agents.html")'''

local = local.replace(old, new)

# Verify
print(f"Updated: {old in local}")
print(f"New: {new in local}")

# Deploy as hex chunks
hex_data = local.encode("utf-8").hex()
CHUNK = 200
for i in range(0, len(hex_data), CHUNK):
    chunk = hex_data[i:i+CHUNK]
    mode = "wb" if i == 0 else "ab"
    r = api("python3", f"-c \"import binascii; open('/home/ubuntu/my-evo-ai/api/routes/routes_static.py','{mode}').write(binascii.unhexlify('{chunk}'))\"")
    if not r.get("success"):
        print(f"CHUNK {i} FAIL")
        exit(1)
print("Write done")

# Restart
api("pkill", "-f api_server")
import time
time.sleep(2)

# Test
for i in range(20):
    try:
        r = urllib.request.urlopen(f"{REMOTE}/agents", timeout=5)
        print(f"OK /agents -> {r.status} ({i+1}s)")
        print(r.read().decode()[:100])
        break
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print(f"OK /agents redirects to {e.headers.get('location','')}")
            break
        if i < 18:
            time.sleep(1)
        else:
            print(f"FAIL: HTTP {e.code}")
            break
    except:
        time.sleep(1)
