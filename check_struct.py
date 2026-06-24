c = open('./frontend/chat.html', encoding='utf-8').read()
i = c.index('class="qa"')
print(repr(c[i-200:i+200]))
