import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

si,so,se = ssh.exec_command('head -30 /home/ubuntu/my-evo-ai/frontend/chat.html', timeout=5)
time.sleep(2)
print(so.read().decode())

si2,so2,se2 = ssh.exec_command('ls -la /home/ubuntu/my-evo-ai/frontend/chat.html /home/ubuntu/my-evo-ai/frontend/chat_engine.js /home/ubuntu/my-evo-ai/sw.js', timeout=5)
time.sleep(1)
print(so2.read().decode())

ssh.close()
