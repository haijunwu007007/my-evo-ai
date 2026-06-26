import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

commands = [
    ("GPU", "nvidia-smi --query-gpu=name,memory.used --format=csv,noheader"),
    ("进程", "ps aux | grep -v grep | grep -E 'python|gpu_server|label'"),
    ("端口", "ss -tlnp | grep -E '8766|8080|8188'"),
    ("ComfyUI", "ls /root/ComfyUI/main.py 2>/dev/null && echo 'yes' || echo 'no'"),
    ("Unsloth", "python3 -c 'import unsloth; print(\"OK\")' 2>&1"),
]

for name, cmd in commands:
    i, o, e = s.exec_command(cmd)
    r = o.read().decode().strip()
    print(f"{name}: {r[:200] if r else 'N/A'}")

s.close()
