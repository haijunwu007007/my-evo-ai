import paramiko, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

def run(cmd):
    i,o,e = ssh.exec_command(cmd, timeout=5)
    time.sleep(2)
    return o.read().decode('utf-8',errors='replace').strip()

# 检查 app.js 和 router.js
print('[app.js exists]')
print(run('ls -la /home/ubuntu/my-evo-ai/frontend/app.js 2>&1'))
print('[app.js size]')
print(run('wc -c /home/ubuntu/my-evo-ai/frontend/app.js 2>&1'))
print('[app.js voice refs]')
print(run('grep -c "voiceMic" /home/ubuntu/my-evo-ai/frontend/app.js 2>&1'))
print('[app.js startVoiceRecord]')
print(run('grep -c "startVoiceRecord" /home/ubuntu/my-evo-ai/frontend/app.js 2>&1'))

# 看 app.js 中 voiceMic 上下文
print('[app.js voice context]')
print(run('grep -n "voiceMic" /home/ubuntu/my-evo-ai/frontend/app.js 2>&1'))

# 检查 server index.html 中加载了什么
print('[index.html script tags]')
print(run('grep -o "src=[^ ]*" /home/ubuntu/my-evo-ai/frontend/index.html 2>&1 | head -5'))
# 或直接看 server 根目录 index.html
print('[root index.html]')
print(run('grep -o "src=[^ ]*" /home/ubuntu/my-evo-ai/index.html 2>&1 | head -5'))

# 看 chat.html voiceMic 放在哪里（对比）
print('[chat.html voice context]')
print(run('grep -n "voiceMic" /home/ubuntu/my-evo-ai/frontend/chat.html 2>&1'))

ssh.close()
