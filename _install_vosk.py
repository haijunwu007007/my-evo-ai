import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 1. Create model dir + download Vosk Chinese model
si, so, se = ssh.exec_command('mkdir -p /home/ubuntu/vosk_models && cd /home/ubuntu/vosk_models && wget -q --show-progress -O vosk-cn.zip https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip 2>&1', timeout=300)
time.sleep(5)
print('Download started...')

# Wait for download (40MB)
for i in range(20):
    time.sleep(10)
    si2, so2, se2 = ssh.exec_command('ls -lh /home/ubuntu/vosk_models/vosk-cn.zip 2>/dev/null', timeout=5)
    sz = so2.read().decode().strip()
    print(f'  {i*10}s: {sz}')
    if '40M' in sz or '44M' in sz or '46M' in sz:
        print('Download complete!')
        break

# 2. Unzip
si3, so3, se3 = ssh.exec_command('cd /home/ubuntu/vosk_models && unzip -q vosk-cn.zip && rm vosk-cn.zip && ls -d */', timeout=120)
time.sleep(3)
print('Unzipped:', so3.read().decode().strip()[:200])

# 3. Restart service
si4, so4, se4 = ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(10)
si5, so5, se5 = ssh.exec_command('systemctl is-active evo.service', timeout=5)
time.sleep(2)
print('Service:', so5.read().decode().strip())

# 4. Test
import urllib.request, ssl, json
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
time.sleep(3)
r = urllib.request.urlopen('https://autoevoai.com/api/v1/speech/status', timeout=15, context=ctx)
print('Speech:', json.loads(r.read()))

ssh.close()
