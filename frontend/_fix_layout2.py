import re, sys

with open('chat.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Find right-panel start (with comment)
start = c.find('<!-- 右侧面板 -->')
if start < 0:
    start = c.find('right-panel hidden')
    if start > 0:
        # Go back to find the <div
        start = c.rfind('<div', 0, start)
else:
    # Skip the comment, find the div after it
    start = c.find('<div', start)

if start < 0:
    print('right-panel not found')
    sys.exit(0)

print('Start:', start, 'Context:', c[start:start+50])

# 2. Find matching closing div
depth = 1
pos = c.find('>', start) + 1

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

print('End:', pos, 'Context:', c[pos-20:pos+20])

# 3. Remove right-panel
c = c[:start] + c[pos:]
print('Removed right-panel, size:', len(c))

# 4. Remove CSS
# Remove right-panel CSS blocks
for pattern in [
    r'\.right-panel\{[^}]*\}',
    r'\.right-panel\.hidden\s*\{[^}]*\}',
    r'\.right-panel\.open\s*\{[^}]*\}',
    r'\.right-toggle-btn\{[^}]*\}',
    r'\.right-toggle-btn::before\{[^}]*\}',
    r'\.right-panel\.hidden\s+\.right-toggle-btn\{[^}]*\}',
    r'\.right-panel\.hidden\s+\.right-toggle-btn::before\{[^}]*\}',
    r'\.right-panel:not\(\.hidden\)\s+\.right-toggle-btn\{[^}]*\}',
    r'\.right-panel:not\(\.hidden\)\s+\.right-toggle-btn::before\{[^}]*\}',
    r'\.right-content\{[^}]*\}',
    r'\.rsec\{[^}]*\}',
    r'\.ritem\{[^}]*\}',
    r'\.right-header\{[^}]*\}',
    r'\.right-header\s+h3\{[^}]*\}'
]:
    c = re.sub(pattern, '', c)

print('Removed CSS')

# 5. Save
with open('chat.html', 'w', encoding='utf-8') as f:
    f.write(c)

print('OK', len(c), 'right-panel:', 'right-panel' in c)
