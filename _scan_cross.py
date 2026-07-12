lines = open('modules/auto_summary.py', 'r', encoding='utf-8').readlines()
for i in range(len(lines) - 1):
    a = lines[i].rstrip()
    b = lines[i + 1].strip()
    if a.endswith('"') and b.startswith('"') and not a.endswith('"""'):
        print(f'L{i+1}: {a[-40:]}', end='')
        print(f' / {b[:40]}')
