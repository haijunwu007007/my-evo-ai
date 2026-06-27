import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 1. 设置国内镜像+下载模型
cmds = """
export HF_ENDPOINT=https://hf-mirror.com
pip install huggingface-hub -q
python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from huggingface_hub import snapshot_download
print('Downloading faster-whisper tiny...')
snapshot_download('guillaumeklay/faster-whisper-tiny', local_dir='/home/ubuntu/.cache/huggingface/hub/models--guillaumeklay--faster-whisper-tiny')
print('Done')
"
"""
stdin,stdout,stderr = ssh.exec_command(cmds, timeout=300)
time.sleep(5)
# 持续输出
import select
while True:
    if stdout.channel.exit_status_ready():
        break
    if stdout.channel.recv_ready():
        print(stdout.channel.recv(1024).decode('utf-8',errors='replace'), end='')
    time.sleep(1)
print("\n=== STDERR ===")
print(stderr.read().decode()[:500])
ssh.close()
