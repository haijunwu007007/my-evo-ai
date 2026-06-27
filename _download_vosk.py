import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# Try different URLs - alphacephei main site might be faster
si, so, se = ssh.exec_command("cd /home/ubuntu/vosk_models && rm -rf * && wget -q -O vosk.zip 'https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip' 2>&1 && echo 'DONE' && ls -lh vosk.zip", timeout=600)
print('Downloading (may take a few minutes)...')
time.sleep(120)
result = so.read().decode().strip()
print('RESULT:', result[:200])

# Check size
si2, so2, se2 = ssh.exec_command('ls -lh /home/ubuntu/vosk_models/vosk.zip 2>/dev/null', timeout=5)
time.sleep(2)
sz = so2.read().decode().strip()
print('Size:', sz)

ssh.close()
