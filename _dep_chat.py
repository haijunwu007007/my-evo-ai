import requests, json, base64, urllib.request, ssl, os, sys

url = 'https://autoevoai.com/api/v1/cli/exec'

# 读取文件
with open('frontend/chat.html', 'rb') as f:
    data = f.read()
print(f'Local file: {len(data)} bytes')

b64 = base64.b64encode(data).decode()
chunk_size = 8000
total = (len(b64) + chunk_size - 1) // chunk_size

# Step 1: 清空
r = requests.post(url, json={'cmd': 'python3', 'args': "-c open('/tmp/_dp.b64','w').close()"}, timeout=60)
print(f'Clear: {r.status_code}')

# Step 2: 逐块写入
for i in range(0, len(b64), chunk_size):
    chunk = b64[i:i+chunk_size]
    # 使用repr()来安全转义
    py = f"with open('/tmp/_dp.b64','a') as f: f.write({repr(chunk)})"
    r = requests.post(url, json={'cmd': 'python3', 'args': f"-c {repr(py)}"}, timeout=60)
    if r.status_code != 200:
        print(f'Chunk {i//chunk_size+1}/{total} FAILED: {r.status_code} {r.text[:100]}')
        sys.exit(1)
    print(f'Chunk {i//chunk_size+1}/{total} OK ({len(chunk)} chars)')

# Step 3: 解码写入
py_decode = (
    "import base64;"
    "d=open('/tmp/_dp.b64').read();"
    "out=open('/home/ubuntu/my-evo-ai/frontend/chat.html','wb');"
    "out.write(base64.b64decode(d));"
    "out.close();"
    f"print(f'Written {{len(d)}} chars -> {len(data)} bytes')"
)
r = requests.post(url, json={'cmd': 'python3', 'args': f"-c {repr(py_decode)}"}, timeout=120)
print(f'Decode: {r.status_code} {r.text[:200]}')

# Step 4: 验证chunk完整性
r2 = requests.post(url, json={'cmd': 'python3', 'args': "-c print(len(open('/tmp/_dp.b64').read()))"}, timeout=30)
print(f'Verify b64 size: {r2.text.strip()}')

# Step 5: 重启
r = requests.post(url, json={'cmd': 'bash', 'args': "-c 'pkill -f api_server; sleep 2; pkill -f uvicorn; echo done'"}, timeout=30)
print(f'Restart: {r.status_code} {r.text[:100]}')
