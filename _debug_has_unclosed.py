def has_unclosed(line, q):
    cnt = 0
    i = 0
    while i < len(line):
        if i < len(line) - 2 and line[i:i+3] == q*3:
            cnt += 1
            i += 3
            continue
        if i > 0 and line[i-1] == '\\':
            i += 1
            continue
        if line[i] == q:
            cnt += 1
        i += 1
    return cnt % 2 == 1

# Test auto_summary.py
lines = open('D:/AUTO-EVO-AI-V0.1/modules/auto_summary.py','r',encoding='utf-8').readlines()
l165 = lines[164].rstrip()
l166 = lines[165].rstrip()
print('L165:', repr(l165))
print('L166:', repr(l166))
print('has_unclosed(L165, "):', has_unclosed(l165, '"'))
print('has_unclosed(L166, "):', has_unclosed(l166, '"'))
print('L166 starts with ":', l166.startswith('"'))

# Test atom_code.py
lines2 = open('D:/AUTO-EVO-AI-V0.1/modules/atom_code.py','r',encoding='utf-8').readlines()
l292 = lines2[291].rstrip()
l293 = lines2[292].rstrip()
print()
print('L292:', repr(l292))
print('L293:', repr(l293))
print('has_unclosed(L292, "):', has_unclosed(l292, '"'))
print('L293 starts with ":', l293.startswith('"'))

# Test agent_apollo.py (cross-line .join)
lines3 = open('D:/AUTO-EVO-AI-V0.1/modules/agent_apollo.py','r',encoding='utf-8').readlines()
for ln in [395, 396, 397, 398]:
    l = lines3[ln].rstrip()
    print(f'L{ln+1}:', repr(l))
    print(f'  has_unclosed("):', has_unclosed(l, '"'))
