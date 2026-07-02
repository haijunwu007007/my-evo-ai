import urllib.request, re
from collections import Counter

r = urllib.request.urlopen('https://autoevoai.com/', timeout=10)
c = r.read().decode('utf-8')

checks = {
    'toolbar-top': 'toolbar-top' in c,
    'tbSuggest': 'tbSuggest' in c,
    'tbCats': 'tbCats' in c,
    'cat-strip': 'cat-strip' in c,
    'tool-chip': 'tool-chip' in c,
    'input-area': 'input-area' in c,
    'topbar': 'class="topbar"' in c,
    'sidebar': 'sidebar' in c,
}
for k, v in checks.items():
    print(f'  {k}: {v}')

fonts = re.findall(r'font-size:(\d+)px', c)
print('font-sizes:', sorted(Counter(fonts).items()))
print(f'tool-chip count: {c.count("tool-chip")}')

local = open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat.html','r',encoding='utf-8').read()
print(f'local len: {len(local)}, remote len: {len(c)}')
print(f'identical: {len(local) == len(c)}')

# Check first 50 chars for login vs chat
head = c[:300].lower()
if 'login' in head or '进入系统' in head:
    print('WARNING: might be login page')
else:
    print('OK: looks like chat page')
