import re
c = open('frontend/chat.html', 'r', encoding='utf-8').read()
btns = re.findall(r'<button class="sbtn"[^>]*>.*?</button>', c)
print(f'sbtn总数: {len(btns)}')
for b in btns:
    txt = re.sub(r'<[^>]+>', ' ', b).strip()
    print(f'  {txt[:60]}')
groups = re.findall(r'<button class="sgroup-header"[^>]*>.*?<span', c)
print(f'\n分组数: {len(groups)}')
for g in groups:
    txt = re.sub(r'<[^>]+>', ' ', g).strip()
    print(f'  {txt}')
