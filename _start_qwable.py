import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

# Kill old processes
s.exec_command("pkill -9 -f vllm 2>/dev/null; pkill -9 -f qwable 2>/dev/null")

# Use HF mirror to download and serve
script = """#!/bin/bash
export HF_ENDPOINT=https://hf-mirror.com
nohup /root/miniconda3/bin/python3 -m vllm.entrypoints.openai.api_server \\
  --model lordx64/Qwable-v1 \\
  --port 8767 \\
  --trust-remote-code \\
  --max-model-len 8192 \\
  --dtype auto \\
  --gpu-memory-utilization 0.9 \\
  --download-dir /root/models \\
  > /tmp/qwable_v1.log 2>&1 &
echo "Started PID: $!"
"""
with s.open_sftp().open("/tmp/start_qwable.sh", "w") as f:
    f.write(script)
s.exec_command("chmod +x /tmp/start_qwable.sh && bash /tmp/start_qwable.sh")

import time
time.sleep(10)
i,o,e = s.exec_command("cat /tmp/qwable_v1.log 2>/dev/null | tail -5")
print(o.read().decode()[:300])
s.close()
