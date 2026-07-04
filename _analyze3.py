import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找HTML里的 right-panel
for m in re.finditer(r'<div[^>]*class="[^"]*right-panel[^"]*"[^>]*>', content):
    print(f'HTML right-panel at {m.start()}: {m.group()[:100]}')
    # 看后面800字符
    print(content[m.start():m.start()+800])
    print('---')

# 找toggleRightPanel函数
print('\n=== toggleRightPanel 函数 ===')
idx = content.find('toggleRightPanel')
if idx > 0:
    print(content[idx:idx+500])

# 看整体布局的div嵌套
print('\n=== content-flex 区域 ===')
idx2 = content.find('<div class="content-flex"')
if idx2 > 0:
    print(content[idx2:idx2+3000])
