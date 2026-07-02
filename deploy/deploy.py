"""后台部署：scp 上传 + ssh 执行 git pull 重启"""
import subprocess, time, os, sys, threading

HOST = "122.51.144.227"
USER = "ubuntu"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

files = [
    ("frontend/chat.html", "frontend/"),
    ("frontend/chat_engine.js", "frontend/"),
    ("frontend/chat_engine_deployed.js", "frontend/"),
    ("frontend/billion-os.html", "frontend/"),
    ("api_server.py", ""),
    ("api/routes/routes_evo_v2.py", "api/routes/"),
    ("api/routes/routes_query.py", "api/routes/"),
    ("api/routes/routes_raven.py", "api/routes/"),
    ("api/routes/routes_chat_storage.py", "api/routes/"),
    ("api/agents/yoyo_evolve.py", "api/agents/"),
    ("api/agents/agent_raven.py", "api/agents/"),
]

def upload(file_local, file_remote_dir):
    src = os.path.join(BASE, file_local).replace("\\", "/")
    dst = f"{USER}@{HOST}:/home/ubuntu/my-evo-ai/{file_remote_dir}"
    cmd = f'scp "{src}" {dst}'
    try:
        subprocess.run(cmd, shell=True, timeout=60, input=b"Hj711201\n", capture_output=True)
    except:
        pass

def restart():
    time.sleep(10)
    cmd = f'ssh {USER}@{HOST} "cd /home/ubuntu/my-evo-ai && git pull origin master 2>&1; pkill -f api_server 2>/dev/null; sleep 2; nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &"'
    try:
        subprocess.run(cmd, shell=True, timeout=30, input=b"Hj711201\n", capture_output=True)
    except:
        pass

# 并行上传
threads = []
for local, remote in files:
    t = threading.Thread(target=upload, args=(local, remote))
    t.start()
    threads.append(t)
for t in threads:
    t.join()

# 后台重启
threading.Thread(target=restart, daemon=True).start()
print("Deploy started. Check https://autoevoai.com in 30s.")
