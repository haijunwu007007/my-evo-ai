#!/usr/bin/env python3
"""
修复v9：全面的跨行字符串修复，处理所有模式
"""
import ast, os, shutil, sys

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_v9'

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

def has_unclosed(line, q):
    """返回行中是否有未闭合的引号"""
    cnt = 0
    i = 0
    while i < len(line):
        if i < len(line) - 2 and line[i:i+3] == q*3:
            cnt += 1  # triple quotes: just count as 1 unit
            i += 3
            continue
        if i > 0 and line[i-1] == '\\':
            i += 1
            continue
        if line[i] == q:
            cnt += 1
        i += 1
    return cnt % 2 == 1

def fix_one(fp):
    if verify(fp):
        return True
    
    os.makedirs(BACKUP, exist_ok=True)
    shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp)+'.bak'))
    
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for rnd in range(50):
        lines = text.split('\n')
        changed = False
        new_lines = []
        skip = False
        
        i = 0
        while i < len(lines):
            if skip:
                skip = False; i += 1; continue
            
            line = lines[i]
            rline = line.rstrip()
            
            if i + 1 >= len(lines):
                new_lines.append(line); i += 1; continue
            
            nxt = lines[i+1]
            nstripped = nxt.strip()
            
            if rline.lstrip().startswith('#'):
                new_lines.append(line); i += 1; continue
            
            patched = False
            
            # === Pattern A: Simple cross-line with next line starting with quote ===
            for q in ('"', "'"):
                if not has_unclosed(rline, q):
                    continue
                
                # Pattern A1: Next line starts with same quote
                if nstripped.startswith(q):
                    # Find the last opening quote on this line
                    last_q = rline.rfind(q)
                    while last_q > 0 and rline[last_q-1] == '\\':
                        last_q = rline.rfind(q, 0, last_q)
                    
                    before = rline[:last_q]  # everything before the opening quote
                    after = nstripped[len(q):]  # everything after the closing quote on next line
                    
                    lines[i] = before + q + '\\n' + q + after
                    skip = True; changed = True; patched = True
                    break
                
                # Pattern A2: Next line has the closing quote somewhere in the middle
                # Need to find the quote in next line
                qi = nstripped.find(q)
                if qi >= 0 and not (qi > 0 and nstripped[qi-1] == '\\'):
                    # Found the closing quote in the middle of next line
                    last_q = rline.rfind(q)
                    while last_q > 0 and rline[last_q-1] == '\\':
                        last_q = rline.rfind(q, 0, last_q)
                    
                    before = rline[:last_q]
                    str_content = nstripped[:qi]  # part before the closing quote
                    rest = nstripped[qi:]  # the closing quote and everything after
                    
                    lines[i] = before + q + '\\n' + str_content + rest
                    skip = True; changed = True; patched = True
                    break
            
            if not patched:
                # === Pattern B: Extra bracket on its own line ===
                if nstripped in (')', '])', '})', ')}', ']', '}') and i > 0:
                    prev = lines[i-1].rstrip()
                    opens = prev.count('(') + prev.count('[') + prev.count('{')
                    closes = prev.count(')') + prev.count(']') + prev.count('}')
                    if opens <= closes:
                        skip = True; changed = True; patched = True
                
                # === Pattern C: logger.info(y_footprint")... ===
                if 'logger.info(y_footprint"' in rline:
                    lines[i] = rline.replace('logger.info(y_footprint"', '"memory_footprint"')
                    changed = True; patched = True
            
            if not patched:
                new_lines.append(line)
            i += 1
        
        if not changed:
            break
        text = '\n'.join(lines)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    
    if verify(fp):
        os.remove(os.path.join(BACKUP, os.path.basename(fp)+'.bak'))
        return True
    
    shutil.copy2(os.path.join(BACKUP, os.path.basename(fp)+'.bak'), fp)
    return False

# Main
err_files = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'待修复: {len(err_files)}')

fixed = 0
for f in err_files:
    fp = os.path.join(BASE, f)
    if fix_one(fp):
        fixed += 1; print('.', end='', flush=True)
    else:
        print('x', end='', flush=True)

print()
total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'总{total}, 修复{fixed}, 剩余{len(final)}')
for f in final[:10]:
    fp = os.path.join(BASE, f)
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read())
    except SyntaxError as e:
        print(f'  L{e.lineno:<5} {str(e.msg)[:50]}  {f}')
if len(final) > 10: print(f'  ...')
