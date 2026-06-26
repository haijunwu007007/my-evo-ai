import paramiko,time
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

# Kill old processes first
s.exec_command("pkill -9 ollama 2>/dev/null; pkill -9 vllm 2>/dev/null; pkill -9 install.sh 2>/dev/null; sleep 2")

# Check GPU and CUDA
i,o,e = s.exec_command("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
gpu = o.read().decode().strip()
print("GPU:", gpu)

# Check vllm
i,o,e = s.exec_command("python3 -c 'import vllm; print(vllm.__version__)' 2>&1")
v = o.read().decode().strip()
print("vLLM:", v[:50])

# Pull model with HF mirror
if "No module" not in v:
    cmd = "HF_ENDPOINT=https://hf-mirror.com nohup python3 -m vllm.entrypoints.openai.api_server --model lordx64/Qwable-v1 --port 8767 --trust-remote-code --max-model-len 4096 --dtype auto > /tmp/vllm.log 2>&1 &"
    s.exec_command(cmd)
    print("vLLM启动中...")
    time.sleep(15)

# Check status
i,o,e = s.exec_command("cat /tmp/vllm.log 2>/dev/null | tail -3")
print("日志:", o.read().decode()[:300])
i,o,e = s.exec_command("ss -tlnp | grep 8767")
print("端口:", o.read().decode()[:100])

s.close()
