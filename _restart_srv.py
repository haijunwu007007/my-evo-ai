import requests, time, sys
url = 'https://autoevoai.com/api/v1/cli/exec'
# 在服务器上写重启脚本
py_code = "import os,time;os.system('pkill -f api_server');time.sleep(2);os.system('pkill -f uvicorn');print('restarted')"
r = requests.post(url, json={'cmd': 'python3', 'args': f"-c {repr(py_code)}"}, timeout=30)
print(f'Restart: {r.status_code}')
print(r.text[:300])
