import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)
si, so, se = ssh.exec_command("grep -A 25 'def _wav' /home/ubuntu/my-evo-ai/api/routes/routes_speech.py", timeout=10)
time.sleep(3)
print(so.read().decode()[:500])
ssh.close()
