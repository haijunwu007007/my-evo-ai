import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 查看所有 input-row 出现位置
print('=== 所有 input-row 出现位置 ===')
for m in re.finditer(r'<div class="input-row[^"]*"[^>]*>', content):
    print(f'  at {m.start()}: {m.group()}')

print()
print('=== 文件末尾 500 字符 ===')
print(content[-500:])

print()
print('=== rightToggleBtn 到文件末尾 ===')
idx = content.find('rightToggleBtn')
print(content[idx:idx+400])

print()
print('=== right-panel HTML 结构 ===')
idx2 = content.find('right-panel')
print(content[idx2:idx2+200])
