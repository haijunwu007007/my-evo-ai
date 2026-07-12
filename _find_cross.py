import os
lines = open('modules/atom_code.py', 'r', encoding='utf-8').readlines()
for i in range(len(lines)):
    l = lines[i]
    if i + 1 < len(lines):
        rline = l.rstrip()
        ns = lines[i+1].strip()
        if rline.endswith('"') and not rline.endswith('"""') and ns.startswith('"'):
            print(f'L{i+1}: {repr(rline)}')
            print(f'L{i+2}: {repr(ns)}')
            print()
        elif rline.endswith("'") and not rline.endswith("'''") and ns.startswith("'"):
            print(f'L{i+1}: {repr(rline)}')
            print(f'L{i+2}: {repr(ns)}')
            print()
