#!/usr/bin/env python3
"""检查国内镜像 + 用 hf-mirror 下载 Whisper 模型"""
import paramiko, time, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)
sftp = ssh.open_sftp()

# 安装脚本：设置 HF_ENDPOINT 为镜像站
setup = '''#!/bin/bash
set -e
export HF_ENDPOINT=https://hf-mirror.com
echo "HF_ENDPOINT=$HF_ENDPOINT"

# 下载 tiny 模型到缓存
python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from faster_whisper import WhisperModel
print('Downloading tiny model from hf-mirror...')
model = WhisperModel('tiny', device='cpu', compute_type='int8')
print('Model loaded OK')
segments, info = model.transcribe('/usr/share/sounds/alsa/Front_Center.wav', language='zh')
for seg in segments:
    print(f'[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}')
print('Transcription done')
" 2>&1
'''

with sftp.open('/tmp/setup_hf.sh', 'w') as f:
    f.write(setup)
sftp.close()

print('[1] Installing model from hf-mirror...')
stdin, stdout, stderr = ssh.exec_command('bash /tmp/setup_hf.sh', timeout=180)
time.sleep(5)
o = stdout.read().decode().strip()
e = stderr.read().decode().strip()
print(o if o else e[:500])

ssh.close()
