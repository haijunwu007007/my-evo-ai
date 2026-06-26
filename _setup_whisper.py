#!/usr/bin/env python3
"""在服务器上安装 faster-whisper 并测试"""
import paramiko, time, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

sftp = ssh.open_sftp()

# 上传安装脚本
setup_script = '''#!/bin/bash
set -e
echo "=== Installing faster-whisper ==="
python3 -m pip install --quiet faster-whisper 2>&1 | tail -5
echo "=== Install done ==="
'''

test_script = '''#!/usr/bin/env python3
from faster_whisper import WhisperModel
print("Loading tiny model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Model loaded OK")
segments, info = model.transcribe("/usr/share/sounds/alsa/Front_Center.wav", language="zh")
for seg in segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
print("Transcription done")
'''

with sftp.open('/tmp/setup_whisper.sh', 'w') as f:
    f.write(setup_script)
with sftp.open('/tmp/test_whisper.py', 'w') as f:
    f.write(test_script)
sftp.close()

# 执行安装
print('[1] Installing faster-whisper...')
stdin, stdout, stderr = ssh.exec_command('bash /tmp/setup_whisper.sh', timeout=180)
import time; time.sleep(5)
o = stdout.read().decode().strip()
e = stderr.read().decode().strip()
print(o if o else e[:300])
print('Install done')

# 执行测试
print()
print('[2] Testing model load and transcription...')
stdin2, stdout2, stderr2 = ssh.exec_command('python3 /tmp/test_whisper.py', timeout=180)
time.sleep(10)
o2 = stdout2.read().decode().strip()
e2 = stderr2.read().decode().strip()
print(o2 if o2 else e2[:500])

ssh.close()
