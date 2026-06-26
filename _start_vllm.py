import paramiko,time
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

# Find where vllm is installed
stdin, stdout, stderr = s.exec_command("pip3 show vllm | grep Location")
loc = stdout.read().decode().strip()
print("Location:", loc)

# Start server with pip3's python
cmd = "HF_ENDPOINT=https://hf-mirror.com nohup python3 -m vllm.entrypoints.openai.api_server --model lordx64/Qwable-v1 --port 8767 --trust-remote-code --max-model-len 4096 --dtype auto > /tmp/vllm.log 2>&1 &"
s.exec_command("cd " + loc.split(": ")[-1].replace("/site-packages","") + " && " + cmd)
time.sleep(30)

stdin, stdout, stderr = s.exec_command("cat /tmp/vllm.log | tail -5")
print("Log:", stdout.read().decode()[:500])
stdin, stdout, stderr = s.exec_command("ss -tlnp | grep 8767")
print("Port:", stdout.read().decode()[:100])

s.close()
