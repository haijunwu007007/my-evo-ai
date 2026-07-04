import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找 <div class="right-panel" 开始到结束
idx = content.find('class="right-panel"')
if idx < 0:
    idx = content.find('right-panel')
print(f'right-panel 开始于 {idx}')
print(content[idx:idx+800])
print('...')
# 找这个right-panel div的结束
depth = 0
start = idx
for i in range(idx, min(idx+1500, len(content))):
    c = content[i]
    if c == '<':
        # check if </
        if i+1 < len(content) and content[i+1] == '/':
            depth -= 1
        elif content[i+1] != '!' and content[i+1] != '?':
            # opening tag, but not self-closing
            # find >
            j = content.find('>', i)
            if j > i and content[j-1] != '/':
                depth += 1
    if depth == 0 and i > start + 20:
        print(f'right-panel 结束于 {i+1}')
        print(content[start:i+1])
        break
