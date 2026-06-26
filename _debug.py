import paramiko, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

def run(cmd):
    i,o,e = ssh.exec_command(cmd, timeout=5)
    time.sleep(2)
    return o.read().decode('utf-8',errors='replace').strip()

print('[JS version]', run('grep "chat_engine.js" /home/ubuntu/my-evo-ai/frontend/chat.html')[:80])
print('[Sizes]')
print(run('wc -c /home/ubuntu/my-evo-ai/frontend/chat_engine.js /home/ubuntu/my-evo-ai/frontend/chat.html /home/ubuntu/my-evo-ai/sw.js /home/ubuntu/my-evo-ai/api/routes/routes_speech.py'))
print('[voiceMic in html]', run('grep -o "voiceMic" /home/ubuntu/my-evo-ai/frontend/chat.html | wc -l'))
print('[addEventListener]', run('grep -c "addEventListener" /home/ubuntu/my-evo-ai/frontend/chat_engine.js'))
print('[Key funcs]')
print(run('grep -n "function startVoiceRecord\\|function stopVoiceRecord\\|function cancelVoiceRecord\\|voiceMic\\|voiceLabel" /home/ubuntu/my-evo-ai/frontend/chat_engine.js | head -20'))
print('[getUserMedia]', run('grep -c "getUserMedia\\|fallbackRecord" /home/ubuntu/my-evo-ai/frontend/chat_engine.js'))
print('[Nginx 404s]')
print(run('grep " 404 " /var/log/nginx/access.log | tail -3'))
print('[Tail 50]')
print(run('tail -50 /home/ubuntu/my-evo-ai/frontend/chat_engine.js')[:800])
ssh.close()
