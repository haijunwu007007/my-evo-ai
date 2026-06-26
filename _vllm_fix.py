import paramiko,time
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("connect.westc.seetacloud.com", port=19126, username="root", password="inoPMdJJ6Wvw", timeout=30)

sftp = s.open_sftp()

# Write check script on server
check_script = """#!/bin/bash
for p in /usr/local/bin/python3 /usr/bin/python3; do
    if [ -f "$p" ]; then
        echo -n "$p: "
        $p -c 'import vllm; print("OK",vllm.__version__)' 2>&1
    fi
done
pip3 show vllm 2>/dev/null | head -3
"""
with sftp.open("/tmp/check_py.sh", "w") as f:
    f.write(check_script)
sftp.close()

s.exec_command("chmod +x /tmp/check_py.sh && bash /tmp/check_py.sh")
i,o,e = s.exec_command("bash /tmp/check_py.sh")
print(o.read().decode()[:300])

s.close()
