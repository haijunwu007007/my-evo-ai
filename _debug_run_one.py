import ast
import os
import shutil

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_dbg'

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except Exception as e:
        return False

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

fp = os.path.join(BASE, 'atom_code.py')
print('Before:', verify(fp))

# Read file
with open(fp, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-8')

lines = text.split('\n')
print(f'Total {len(lines)} lines')

# Show L292 context
for i in range(290, 298):
    rline = lines[i].rstrip()
    nxt = lines[i+1].rstrip() if i+1 < len(lines) else ''
    has = has_unclosed(rline, '"')
    nstarts = nxt.startswith('"') if nxt else False
    print(f'  L{i+1}: has_unclosed={has}  nxt_starts_with_q={nstarts}')
    print(f'    line: {repr(rline)}')
    if nxt:
        print(f'    next: {repr(nxt)}')
