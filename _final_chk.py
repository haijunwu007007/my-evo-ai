import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

sftp = s.open_sftp()

checks = {
    "conda_pytorch": "/root/miniconda3/bin/python3 -c 'import torch; print(torch.__version__)' 2>&1",
    "conda_trans": "/root/miniconda3/bin/python3 -c 'import transformers; print(transformers.__version__)' 2>&1",
    "qwable_port": "ss -tlnp | grep 8767",
    "qwable_log": "tail -20 /tmp/qwable.log 2>/dev/null",
    "vllm_installed": "/root/miniconda3/bin/python3 -c 'import vllm; print(vllm.__version__)' 2>&1",
    "gpu_mem": "nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader",
}

for name, cmd in checks.items():
    script = "#!/bin/bash\n" + cmd + "\n"
    with sftp.open(f"/tmp/ck_{name}.sh", "w") as f:
        f.write(script)
    s.exec_command(f"chmod +x /tmp/ck_{name}.sh")
    i, o, e = s.exec_command(f"bash /tmp/ck_{name}.sh")
    r = o.read().decode().strip()[:150]
    print(f"{name:20s} {r}")

sftp.close()
s.close()
