"""查看语音请求日志 + 直接测试"""
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 1. 查看最近语音请求的日志
stdin, stdout, stderr = ssh.exec_command('sudo journalctl -u evo.service --no-pager -n 100 | grep -i "speech\|recognize\|whisper\|转码\|识别\|音频\|recording\|ffmpeg" | tail -20', timeout=10)
time.sleep(3)
print("=== SPEECH LOGS ===")
print(stdout.read().decode()[:1500])
print(stderr.read().decode()[:200])

# 2. 确认 routes_speech.py 版本
stdin2, stdout2, stderr2 = ssh.exec_command('head -3 /home/ubuntu/my-evo-ai/api/routes/routes_speech.py && wc -c /home/ubuntu/my-evo-ai/api/routes/routes_speech.py', timeout=5)
time.sleep(2)
print("\n=== FILE CHECK ===")
print(stdout2.read().decode().strip())

# 3. 检查 Whisper 是否已加载
stdin3, stdout3, stderr3 = ssh.exec_command('ps aux | grep python | head -3', timeout=5)
time.sleep(1)
print("\n=== PYTHON PROCESSES ===")
print(stdout3.read().decode()[:500])

ssh.close()
