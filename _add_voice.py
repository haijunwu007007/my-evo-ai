import paramiko, time, os

# First, add voice button to local chat.html
with open('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check if voice button already exists
if 'voiceMic' not in html:
    # Find the input area and add voice button
    # Look for the button bar or mic area
    old = '<button class="kbd-btn" id="kbdBtn" onclick="switchToText()" title="键盘输入">'
    new = ('<button class="mic" id="voiceMic" ontouchstart="startVoiceRecord(event)" '
           'onmousedown="startVoiceRecord(event)" '
           '><span id="voiceLabel">🎤语音</span></button>\n'
           '            <button class="kbd-btn" id="kbdBtn" onclick="switchToText()" title="键盘输入">')
    if old in html:
        html = html.replace(old, new)
        with open('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'voiceMic added, new size: {len(html)}')
    else:
        print('Button not found in HTML')
else:
    print('voiceMic already exists')

# Upload to server
ssh = paramiko.SSHClient(); ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227',22,'ubuntu','Hj711201',timeout=30)
sftp = ssh.open_sftp()
sftp.put('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat.html', '/home/ubuntu/my-evo-ai/frontend/chat.html')
print('Uploaded:', os.path.getsize('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat.html'))

# Also upload chat_engine.js and sw.js
sftp.put('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat_engine.js', '/home/ubuntu/my-evo-ai/frontend/chat_engine.js')
sftp.put('D:\\AUTO-EVO-AI-V0.1\\sw.js', '/home/ubuntu/my-evo-ai/sw.js')
sftp.close()

# Restart
ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
time.sleep(10)
import urllib.request, ssl, json
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
r = urllib.request.urlopen('https://autoevoai.com/api/status', timeout=15, context=ctx)
d = json.loads(r.read())
print(f'API: {d.get(\"status\")} {d.get(\"modules_loaded\")}')
ssh.close()
