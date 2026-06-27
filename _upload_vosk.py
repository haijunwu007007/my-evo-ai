import paramiko, time, os, io, sys
sys.stdout.reconfigure(encoding='utf-8')

local_zip = r'D:\AUTO-EVO-AI-V0.1\vosk-cn.zip'
print(f'Local zip: {os.path.getsize(local_zip)} bytes')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 1. Upload zip directly
sftp = ssh.open_sftp()
dest = '/home/ubuntu/vosk_models/vosk-model-small-cn-0.22.zip'
print(f'Uploading {os.path.getsize(local_zip)} bytes to {dest}...')
sftp.put(local_zip, dest)
sftp.stat(dest)
print('Upload OK')

# 2. Extract on server
si, so, se = ssh.exec_command(
    'cd /home/ubuntu/vosk_models && unzip -q vosk-model-small-cn-0.22.zip && ls -d */ 2>&1',
    timeout=120
)
time.sleep(30)
out = so.read().decode().strip()[:500]
err = se.read().decode().strip()[:200]
print('EXTRACT:', out if out else err)

# 3. Check model dir
si2, so2, se2 = ssh.exec_command('ls /home/ubuntu/vosk_models/', timeout=5)
time.sleep(2)
print('MODELS:', so2.read().decode().strip())

# 4. Restart
si3, so3, se3 = ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(15)
import urllib.request, ssl, json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 5. Verify
for i in range(6):
    time.sleep(5)
    try:
        r = urllib.request.urlopen('https://autoevoai.com/api/status', timeout=10, context=ctx)
        d = json.loads(r.read())
        print(f'TRY {i+1}: {d.get("status")} / modules: {d.get("modules_loaded")}')
        break
    except Exception as e:
        print(f'TRY {i+1}: waiting... {str(e)[:50]}')

r2 = urllib.request.urlopen('https://autoevoai.com/api/v1/speech/status', timeout=10, context=ctx)
print('SPEECH:', json.loads(r2.read()))

sftp.close()
ssh.close()
