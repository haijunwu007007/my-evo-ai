import paramiko, time
ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

print('Killing evo...')
ssh.exec_command('sudo systemctl stop evo.service', timeout=10)
time.sleep(2)

print('Removing Whisper auto-load to prevent startup hang...')
# Replace the background thread with a safe version
si,so,se = ssh.exec_command(
    "sudo sed -i 's/threading.Thread(target=_preload_whisper/safe_whisper()/' /home/ubuntu/my-evo-ai/api/routes/routes_speech.py",
    timeout=5)
time.sleep(1)

print('Starting evo...')
ssh.exec_command('sudo systemctl start evo.service', timeout=10)
time.sleep(15)

si2,so2,se2 = ssh.exec_command('systemctl is-active evo.service', timeout=5)
time.sleep(1)
print('Status:', so2.read().decode().strip())

ssh.close()
