c = open('chat.html', 'r', encoding='utf8').read()

# 1. 删除 right-panel（使用栈计数找到匹配的闭合div）
start = c.find('<div class="right-panel" id="rightPanel">')
if start >= 0:
    depth = 1
    pos = start + len('<div class="right-panel" id="rightPanel">')
    while depth > 0 and pos < len(c):
        next_open = c.find('<div', pos)
        next_close = c.find('</div>', pos)
        if next_close < 0:
            break
        if next_open >= 0 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            pos = next_close + 6
    c = c[:start] + c[pos:]
    print('Removed right-panel')
else:
    print('right-panel not found')

# 2. 删除 right-toggle 按钮
start = c.find('<button class="right-toggle"')
if start >= 0:
    e = c.find('</button>', start) + 9
    c = c[:start] + c[e:]
    print('Removed right-toggle')

# 3. 删除 right-panel CSS
import re

c = re.sub(r'\.right-panel\{[^}]*\}', '', c)
c = re.sub(r'\.right-panel\.open\{[^}]*\}', '', c)
c = re.sub(r'\.right-toggle\{[^}]*\}', '', c)
print('Removed CSS')

# 4. 提取 input-area
ia_start = c.find('<div class="input-area"')
ia_end = c.find('</div>', ia_start) + 6
input_area = c[ia_start:ia_end]
print('Extracted input-area:', len(input_area))

# 5. 找到主内容区（appMain）的结束位置，把 input-area 移到底部
app_start = c.find('<div class="appMain"')
if app_start < 0:
    app_start = c.find('<div id="appMain"')
if app_start >= 0:
    # 找到 appMain 的闭合 div
    depth = 1
    pos = app_start
    while depth > 0 and pos < len(c):
        next_open = c.find('<div', pos + 1)
        next_close = c.find('</div>', pos + 1)
        if next_close < 0:
            break
        if next_open >= 0 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            pos = next_close + 6
    
    # 在 appMain 闭合之前插入 input-area
    c = c[:pos - 6] + input_area + '\n' + c[pos - 6:]
    print('Moved input-area to appMain bottom')
else:
    print('appMain not found')

open('chat.html', 'w', encoding='utf8').write(c)
print('OK', len(c), 'right-panel:', 'right-panel' in c)
