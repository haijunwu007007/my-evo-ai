import os, ast, shutil

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_dbg2'

def has_unclosed(line, q):
    cnt = 0
    i = 0
    while i < len(line):
        if i < len(line) - 2 and line[i:i+3] == q*3:
            cnt += 1; i += 3; continue
        if i > 0 and line[i-1] == '\\':
            i += 1; continue
        if line[i] == q:
            cnt += 1
        i += 1
    return cnt % 2 == 1

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read())
        return True
    except: return False

fp = os.path.join(BASE, 'atom_code.py')
print('Before fix:', verify(fp))

# Copy backup
os.makedirs(BACKUP, exist_ok=True)
shutil.copy2(fp, os.path.join(BACKUP, 'atom_code.py.bak'))

with open(fp, 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')

# Manually fix L292-293
print(f'L292: {repr(lines[291])}')
print(f'L293: {repr(lines[292])}')

# Check the actual chars
for i, ch in enumerate(lines[291]):
    if ch == '"':
        print(f'  quote at pos {i}')

# Pattern A1: L292 unclosed ", L293 starts with "
rline = lines[291].rstrip()
nstripped = lines[292].strip()

print(f'rline: {repr(rline)}')
print(f'nstripped: {repr(nstripped)}')
print(f'has_unclosed(rline, "): {has_unclosed(rline, chr(34))}')
print(f'nstripped starts with ": {nstripped.startswith(chr(34))}')

last_q = rline.rfind('"')
print(f'last_q index: {last_q}')
print(f'rline[:last_q]: {repr(rline[:last_q])}')

before = rline[:last_q]
after = nstripped[1:]  # skip leading "
merged = before + '"' + '\\n' + '"' + after
print(f'merged: {repr(merged)}')

# Apply
lines[291] = merged
del lines[292]
text = '\n'.join(lines)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(text)

print('After fix:', verify(fp))

if verify(fp):
    print('SUCCESS!')
else:
    # Restore
    shutil.copy2(os.path.join(BACKUP, 'atom_code.py.bak'), fp)
    print('FAILED, restored')
