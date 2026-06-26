import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

def run(cmd, timeout=5):
    si,so,se = ssh.exec_command(cmd, timeout=timeout)
    time.sleep(2)
    return so.read().decode()

# 1. File sizes
print('File sizes:')
print(run('wc -c /home/ubuntu/my-evo-ai/frontend/chat_engine.js /home/ubuntu/my-evo-ai/frontend/chat.html /home/ubuntu/my-evo-ai/sw.js /home/ubuntu/my-evo-ai/api/routes/routes_speech.py'))

# 2. Service status
print('Service:', run('systemctl is-active evo.service'))

# 3. Speech status via local API
print('Speech:', run("curl -s http://127.0.0.1:8765/api/v1/speech/status"))

# 4. Whisper model status
print('Whisper:', run("python3 -c 'from faster_whisper import WhisperModel; m=WhisperModel(\"tiny\",device=\"cpu\",compute_type=\"int8\"); print(\"model loaded ok\")' 2>&1", timeout=60))

# 5. Whisper test with actual audio
print('Test:', run('curl -s --max-time 120 -F "file=@/tmp/test_sine.webm" http://127.0.0.1:8765/api/v1/speech/recognize', timeout=130))

ssh.close()
