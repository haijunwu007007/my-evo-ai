import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# Check server files
def run(cmd):
    s,o,e = ssh.exec_command(cmd, timeout=5)
    time.sleep(2)
    return (o.read().decode() or e.read().decode()).strip()

print('chat_engine.js size:', run('wc -c /home/ubuntu/my-evo-ai/frontend/chat_engine.js'))
print('_fallbackRecord count:', run('grep -c _fallbackRecord /home/ubuntu/my-evo-ai/frontend/chat_engine.js'))
print('_retryCount:', run('grep -c _retryCount /home/ubuntu/my-evo-ai/frontend/chat_engine.js'))
print('v= version:', run("grep -o 'v=[0-9]' /home/ubuntu/my-evo-ai/frontend/chat.html"))

# Check service is alive
s2,o2,e2 = ssh.exec_command('curl -s http://127.0.0.1:8765/api/v1/speech/status', timeout=10)
time.sleep(3)
print('Speech status:', o2.read().decode().strip()[:150])
ssh.close()
