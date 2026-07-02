import sys, os
sys.stdout.reconfigure(encoding='utf-8')
c = open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html','r',encoding='utf-8').read()
print(f'lines: {c.count(chr(10))+1}')
print(f'total tool-chips: {c.count("tool-chip")}')
print(f'cat-strip: {"cat-strip" in c}')
print(f'topbar: {"topbar" in c}')
# 看看tool-chips在哪里出现
pos = 0; chips_at = []
while True:
    p = c.find('onclick="quickFill', pos)
    if p < 0: break
    chips_at.append(p)
    pos = p + 1
print(f'quickFill buttons: {len(chips_at)}')
# 看看最后一个cat-strip在哪里
cs = c.rfind('cat-strip')
msg = c.rfind('messages"')
ia = c.find('input-area')
print(f'cat-strip pos: {cs}')
print(f'messages end: {msg}')
print(f'input-area: {ia}')
print(f'cat-strip after messages: {cs > msg}')
print(f'cat-strip before input: {cs < ia}')
