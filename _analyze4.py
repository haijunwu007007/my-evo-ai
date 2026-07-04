import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找 toggleRightPanel 函数
for m in re.finditer(r'(function toggleRightPanel|toggleRightPanel\s*=\s*function)', content):
    print(f'toggleRightPanel at {m.start()}:')
    print(content[m.start():m.start()+400])

# 找 right-toggle-btn CSS
for m in re.finditer(r'right-toggle-btn', content):
    print(f'\nright-toggle-btn at {m.start()}:')
    print(content[max(0,m.start()-50):m.start()+200])

# 找 input-row CSS
for m in re.finditer(r'\.input-row', content):
    print(f'\n.input-row at {m.start()}:')
    print(content[m.start():m.start()+200])
