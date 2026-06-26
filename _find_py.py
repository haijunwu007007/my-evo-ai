import paramiko,time
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

# Check python with vllm
stdin, stdout, stderr = s.exec_command("for p in /usr/local/bin/python3 /usr/bin/python3 /opt/conda/bin/python3; do echo $p; $p -c 'import vllm; print(\"OK\")' 2>&1; done")
print(stdout.read().decode()[:300])

s.close()
