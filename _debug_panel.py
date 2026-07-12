lines = open('modules/debug_panel.py', 'r', encoding='utf-8').readlines()
# Check L598-610
for i in range(598, min(610, len(lines))):
    r = lines[i].rstrip()
    if '✅' in r or '❌' in r:
        r = r.replace('✅', '[OK]').replace('❌', '[NO]')
    print(f'{i+1}: {repr(r)[:80]}')
