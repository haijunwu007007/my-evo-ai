import paramiko, time, os

local_zip = r'D:\AUTO-EVO-AI-V0.1\vosk-cn.zip'
local_size = os.path.getsize(local_zip)
print('Local:', local_size // 1024 // 1024, 'MB')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=120)
sftp = ssh.open_sftp()

print('Uploading...')
sftp.put(local_zip, '/home/ubuntu/vosk_models/vosk-cn.zip')
st = sftp.stat('/home/ubuntu/vosk_models/vosk-cn.zip')
print('Uploaded:', st.st_size // 1024 // 1024, 'MB')
sftp.close()

print('Extracting...')
si, so, se = ssh.exec_command(
    "cd /home/ubuntu/vosk_models && unzip -q vosk-cn.zip && rm -f vosk-cn.zip",
    timeout=120
)
time.sleep(5)
out = so.read().decode().strip()[:200]
err = se.read().decode().strip()[:200]
print('Extract:', out if out else err)

si2, so2, se2 = ssh.exec_command("ls /home/ubuntu/vosk_models/vosk-model-small-cn-0.22/ | head -5", timeout=10)
time.sleep(1)
print('Files:', so2.read().decode().strip()[:300])

ssh.close()
