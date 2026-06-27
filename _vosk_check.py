import paramiko, time
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)

def run(cmd):
    si,so,se=ssh.exec_command(cmd,timeout=10);time.sleep(2)
    return (so.read().decode()+se.read().decode())[:500]

print('FIND vosk:')
print(run('find / -name "vosk-model*" -type d 2>/dev/null'))
print('---')
print('VOSK_DIR:')
print(run('ls -la /home/ubuntu/vosk_models/ 2>&1'))
print('---')
print('VOSK DIR check:')
print(run('python3 -c "import os; d=\"/home/ubuntu/vosk_models\"; print(os.path.isdir(d), [x for x in os.listdir(d)][:5])" 2>&1'))
print('---')
print('VOSK module:')
print(run('python3 -c "import vosk; print(vosk.__version__)" 2>&1'))
ssh.close()
