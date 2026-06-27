import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'r', encoding='utf-8') as f:
    d = f.read()

# Remove ALL inline <script> blocks that contain voice functions
d = re.sub(r'<script>\s*var _vStream.*?</script>', '', d, flags=re.DOTALL)
d = re.sub(r'<script>\s*function voiceStart.*?</script>', '', d, flags=re.DOTALL)

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'w', encoding='utf-8') as f:
    f.write(d)

scripts = re.findall(r'<script[^>]*>.*?</script>', d, re.DOTALL)
print('Remaining scripts:', len(scripts))
if scripts:
    for s in scripts:
        if '_vStream' in s:
            print('STILL HAS VOICE:', s[:60])
        else:
            print('OK:', s[:60])
else:
    print('No scripts in HTML')
print('_vStream count:', d.count('_vStream'))
print('voiceBtn count:', d.count('voiceBtn'))
print('Size:', len(d))
