"""查找错误来源"""
import urllib.request, json

def cli(cmd, args=""):
    payload = json.dumps({"cmd": cmd, "args": args, "timeout": 10}).encode()
    req = urllib.request.Request("https://autoevoai.com/api/v1/cli/exec", data=payload, headers={"Content-Type":"application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

# 在服务器代码中搜索"资源不存在"
r = cli("python3", '-c "import os; import re; root=\'/home/ubuntu/my-evo-ai\'; for dirpath, dirnames, filenames in os.walk(root): [print(f\\\"{os.path.join(dirpath,f)}: {line_no}\\\") for f in filenames if f.endswith(\\\".py\\\") for line_no,line in enumerate(open(os.path.join(dirpath,f), errors=\\\"ignore\\\"),1) if \\\"资源不存在\\\" in line]"')
print("FOUND IN:", r.get("stdout","")[:500])

# 检查是否在Nginx层
r = cli("python3", '-c "import os; [print(os.path.join(r,f)) for r,d,fs in os.walk(\'/etc/nginx\') for f in fs if not f.endswith(\\\".pem\\\") and not f.endswith(\\\".crt\\\")]"')
print("NGINX:", r.get("stdout","")[:500])

# 检查错误处理中间件
r = cli("python3", '-c "import sys; sys.path.insert(0,\'/home/ubuntu/my-evo-ai\'); from api_server import app; [print(r.path) for r in app.routes if hasattr(r,\\\"app\\\")]"')
print("MOUNTS:", r.get("stdout","")[:500])
