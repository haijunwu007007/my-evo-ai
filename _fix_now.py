import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 杀进程
si,so,se = ssh.exec_command('sudo pkill -9 -f "uvicorn api_server" 2>&1', timeout=5)
time.sleep(2)
print('Killed old process')

# 清除可能卡住的 Whisper 模型
si2,so2,se2 = ssh.exec_command('rm -rf ~/.cache/huggingface/hub/models--guillaumeklay--faster-whisper-* ~/.cache/whisper 2>&1', timeout=5)
time.sleep(2)
print('Cleared model cache')

# 用简单的版本启动（无 Whisper 预加载）
si3,so3,se3 = ssh.exec_command('cd /home/ubuntu/my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > /tmp/evo_latest.log 2>&1 &', timeout=10)
time.sleep(3)

# 等一会看端口
for i in range(6):
    time.sleep(5)
    si4,so4,se4 = ssh.exec_command('ss -tlnp | grep 8765', timeout=5)
    time.sleep(1)
    out = so4.read().decode().strip()
    if out:
        print(f'Try {i+1}: Port 8765 IS listening')
        break
    else:
        print(f'Try {i+1}: Not yet...')

# 测试
si5,so5,se5 = ssh.exec_command('curl -s --max-time 10 http://127.0.0.1:8765/api/status 2>&1', timeout=15)
time.sleep(8)
print('\nCurl:', (so5.read().decode()[:100] if so5.read().decode() else 'FAILED'))

ssh.close()
