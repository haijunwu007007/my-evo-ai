import paramiko,time
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

# Check if conda exists
stdin, stdout, stderr = s.exec_command("which conda 2>/dev/null; conda --version 2>/dev/null")
print("Conda:", stdout.read().decode()[:100])

# Check if there's a conda env with vllm
stdin, stdout, stderr = s.exec_command("conda env list 2>/dev/null | head -10")
print("Envs:", stdout.read().decode()[:200])

# Try sglang or llama.cpp
stdin, stdout, stderr = s.exec_command("python3 -c 'from transformers import AutoModel; print(\"transformers OK\")' 2>&1")
print("HF:", stdout.read().decode()[:100])

s.close()
