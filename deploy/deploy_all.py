"""AUTO-EVO-AI 一键部署（纯Python，无需sshpass）"""
import subprocess, time, os

HOST = "122.51.144.227"
USER = "ubuntu"
PASS = "Hj711201"
BASE = r"D:\AUTO-EVO-AI-V0.1"

files = [
    f"{BASE}\\frontend\\chat.html",
    f"{BASE}\\frontend\\chat_engine.js",
    f"{BASE}\\frontend\\chat_engine_deployed.js",
    f"{BASE}\\frontend\\billion-os.html",
    f"{BASE}\\api_server.py",
    f"{BASE}\\api\\routes\\routes_evo_v2.py",
    f"{BASE}\\api\\routes\\routes_query.py",
    f"{BASE}\\api\\routes\\routes_raven.py",
    f"{BASE}\\api\\routes\\routes_chat_storage.py",
    f"{BASE}\\api\\agents\\yoyo_evolve.py",
    f"{BASE}\\api\\agents\\agent_raven.py",
]

print("上传文件...")
for f in files:
    dest = f"/home/ubuntu/my-evo-ai/{os.path.relpath(f, BASE).replace(chr(92), '/')}"
    cmd = f'echo {PASS} | scp "{f}" {USER}@{HOST}:{dest}'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    status = "OK" if r.returncode == 0 else "FAIL"
    print(f"  [{status}] {os.path.basename(f)}")

print("\n重启服务...")
cmd = f'ssh {USER}@{HOST} "cd /home/ubuntu/my-evo-ai && pkill -f api_server 2>/dev/null; sleep 2; nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &"'
echo_cmd = f'echo {PASS} | {cmd}'
r = subprocess.run(echo_cmd, shell=True, capture_output=True, text=True, timeout=15)
print("  restart sent")

print("\n验证...")
time.sleep(6)
import urllib.request
for ep, name in [("/","首页"),("/billion-os.html","billion"),("/api/v1/evo/status","自进化")]:
    try:
        r = urllib.request.urlopen(f"https://autoevoai.com{ep}", timeout=10)
        print(f"  [OK] {name}: {r.status}")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")

print("\n完成!")
