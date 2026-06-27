import re, sys
with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'r', encoding='utf-8') as f:
    d = f.read()

# Remove the voice toggle button
d = d.replace('<button class="vt" id="voiceToggle" onclick="switchVoiceMode()">\U0001f3a4</button>', '')

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'w', encoding='utf-8') as f:
    f.write(d)

print('voiceToggle:', d.count('voiceToggle'))
print('done')
