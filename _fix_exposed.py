import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'r', encoding='utf-8') as f:
    d = f.read()

# Find the inline voice code (starts after </div>\n\n\n and before next section)
i = d.find('\nvar _vStream=null')
if i < 0:
    print('_vStream not found')
    exit()
j = d.find('\n}\n', i + 200)  # Find end of voiceStop function
if j < 0:
    print('end not found')
    exit()

# Get the inline code
inline_code = d[i+1:j+3]  # +1 to skip leading \n, +3 for }\n

# Remove the inline code from HTML
d = d[:i+1] + d[j+3:]

# Append to chat_engine.js
with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Add voice functions at the end
js = js.rstrip() + '\n\n// Voice functions\n' + inline_code

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'w', encoding='utf-8') as f:
    f.write(js)

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html', 'w', encoding='utf-8') as f:
    f.write(d)

print('Moved voice code to chat_engine.js')
print('HTML size:', len(d))
print('JS size:', len(js))
