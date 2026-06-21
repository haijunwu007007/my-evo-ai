c = open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', encoding='utf-8').read()
i1 = c.index('quick-actions')
i2 = c.index('input-area', i1)
block = c[i1:i2]
print('tools:', block.count('class="qa"'))
print('dividers:', block.count('border-top'))
print('headings:', block.count('font-weight:600'))
# Print the first 300 chars of the block
print('---FIRST 300---')
print(block[:300])
