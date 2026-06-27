import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# Remove partial zip, re-download with continue support
si, so, se = ssh.exec_command('rm -rf /home/ubuntu/vosk_models/* && cd /home/ubuntu/vosk_models && wget -c -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip 2>&1', timeout=600)
print('Downloading Vosk Chinese model (~42MB)...')
time.sleep(300)  # Wait 5 minutes

si2, so2, se2 = ssh.exec_command('ls -lh /home/ubuntu/vosk_models/vosk-model-small-cn-0.22.zip 2>/dev/null', timeout=5)
time.sleep(2)
sz = so2.read().decode().strip()
print(f'After 5min: {sz}')

# Unzip and restart
si3, so3, se3 = ssh.exec_command('cd /home/ubuntu/vosk_models && unzip -q vosk-model-small-cn-0.22.zip && rm -f vosk-model-small-cn-0.22.zip && ls -d */', timeout=120)
time.sleep(3)
print('Unzip:', so3.read().decode().strip()[:200])

# Restart
si4, so4, se4 = ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(15)

import urllib.request, ssl, json
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
r = urllib.request.urlopen('https://autoevoai.com/api/v1/speech/status', timeout=15, context=ctx)
print('Status:', json.loads(r.read()))

# Test recognize with a dummy wav
import struct
sr=16000; dur=1
with open('D:\\AUTO-EVO-AI-V0.1\\_test_vosk.wav','wb') as f:
    data_size=sr*dur*2
    f.write(b'RIFF'); f.write(struct.pack('<I',36+data_size)); f.write(b'WAVE')
    f.write(b'fmt '); f.write(struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16))
    f.write(b'data'); f.write(struct.pack('<I',data_size))
    f.write(bytes([0]*data_size))
sftp=ssh.open_sftp()
sftp.put('D:\\AUTO-EVO-AI-V0.1\\_test_vosk.wav','/tmp/voicetest.wav')
sftp.close()

# Test via internal curl
si5, so5, se5 = ssh.exec_command('curl -s --max-time 60 -F "file=@/tmp/voicetest.wav" http://127.0.0.1:8765/api/v1/speech/recognize', timeout=60)
time.sleep(5)
print('Recog:', so5.read().decode()[:300])

ssh.close()
