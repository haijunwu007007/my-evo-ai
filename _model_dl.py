import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# Step 1: pip install
print('Step 1: pip install modelscope...')
si, so, se = ssh.exec_command('pip3 install -q modelscope 2>&1', timeout=120)
time.sleep(5)
out = so.read().decode().strip()
err = se.read().decode().strip()
print('OUT:', out[:200])
print('ERR:', err[:200])

# Step 2: download model
print('\nStep 2: download model...')
cmd = (
    "python3 -c "
    "'from modelscope.hub.snapshot_download import snapshot_download; "
    "snapshot_download(\"alphacep/vosk-model-small-cn-0.22\", "
    "cache_dir=\"/home/ubuntu/vosk_models\")'"
    " 2>&1"
)
si2, so2, se2 = ssh.exec_command(cmd, timeout=300)
time.sleep(5)
out2 = so2.read().decode().strip()
err2 = se2.read().decode().strip()
print('OUT:', out2[:500])
print('ERR:', err2[:200])

# Step 3: check files
print('\nStep 3: check files...')
si3, so3, se3 = ssh.exec_command('find /home/ubuntu/vosk_models/ -type d | head -5; find /home/ubuntu/vosk_models/ -name "*.am" -o -name "*.conf" | head -5', timeout=10)
time.sleep(2)
print(so3.read().decode()[:500])

ssh.close()
