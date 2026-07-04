import base64
exec(base64.b64decode(b'''
c = open('chat.html', 'r', encoding='utf8').read()
s = c.find('right-panel hidden')
print('Start:', s)
depth = 1
pos = c.find('>', s) + 1
while depth > 0 and pos < len(c):
    next_open = c.find('<div', pos)
    next_close = c.find('</div>', pos)
    if next_close < 0: break
    if next_open >= 0 and next_open < next_close:
        depth += 1; pos = next_open + 4
    else:
        depth -= 1; pos = next_close + 6
print('End:', pos)
print(repr(c[pos-20:pos+20]))
'''))
