#!/usr/bin/env python3
"""
修复v11：多行跨行字符串修复 + 空内容识别
"""
import ast, os, shutil, sys

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_v11'

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

def has_unclosed(line, q):
    cnt = 0; i = 0
    while i < len(line):
        if i < len(line)-2 and line[i:i+3] == q*3: cnt += 1; i += 3; continue
        if i > 0 and line[i-1] == '\\': i += 1; continue
        if line[i] == q: cnt += 1
        i += 1
    return cnt % 2 == 1

def fix_file(fp):
    if verify(fp): return True
    
    os.makedirs(BACKUP, exist_ok=True)
    shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp)+'.bak'))
    
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for rnd in range(100):
        lines = text.split('\n')
        changed = False
        skipped = set()
        
        i = 0
        while i < len(lines):
            if i in skipped: i += 1; continue
            
            line = lines[i]
            rline = line.rstrip()
            
            if i + 1 >= len(lines):
                i += 1; continue
            
            nxt = lines[i+1]
            nstripped = nxt.strip()
            
            if rline.lstrip().startswith('#'):
                i += 1; continue
            
            patched = False
            
            # === Find cross-line strings ===
            for q in ('"', "'"):
                if not has_unclosed(rline, q):
                    continue
                
                # Find LAST opening quote on this line
                last_q = -1
                for idx, ch in enumerate(rline):
                    if ch == q and (idx == 0 or rline[idx-1] != '\\'):
                        last_q = idx
                
                if last_q < 0: continue
                before = rline[:last_q]
                
                # Search FORWARD for the closing quote
                content_parts = []
                close_idx = -1
                for j in range(i+1, len(lines)):
                    lj = lines[j]
                    stripped_j = lj.strip()
                    
                    qi = -1
                    for k, ch in enumerate(stripped_j):
                        if ch == q and (k == 0 or stripped_j[k-1] != '\\'):
                            qi = k
                            break
                    
                    if qi >= 0:
                        # Found closing quote
                        close_idx = j
                        str_content = stripped_j[:qi]
                        rest = stripped_j[qi:]
                        content_parts.append(str_content)
                        
                        # Determine content between quotes
                        if not content_parts or all(cp == '' for cp in content_parts):
                            full_content = '\\n'
                        else:
                            full_content = '\\n'.join(cp for cp in content_parts if cp)
                        
                        merged = before + q + full_content + rest
                        break
                    else:
                        content_parts.append(stripped_j)
                
                if close_idx >= 0:
                    lines[i] = merged
                    for k in range(i+1, close_idx+1):
                        skipped.add(k)
                    changed = True; patched = True
                    break
            
            if not patched:
                # Extra bracket
                if nstripped in (')', '])', '})', ')}', ']', '}') and i > 0:
                    prev = lines[i-1].rstrip()
                    opens = prev.count('(') + prev.count('[') + prev.count('{')
                    closes = prev.count(')') + prev.count(']') + prev.count('}')
                    if opens <= closes:
                        skipped.add(i+1)
                        changed = True; patched = True
                
                # logger.info typo
                if not patched and "logger.info(y_footprint" in rline:
                    lines[i] = lines[i].replace('logger.info(y_footprint"', '"memory_footprint"')
                    changed = True; patched = True
            
            i += 1
        
        if not changed:
            break
        
        new_lines = [l for idx, l in enumerate(lines) if idx not in skipped]
        text = '\n'.join(new_lines)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    
    if verify(fp):
        bak = os.path.join(BACKUP, os.path.basename(fp)+'.bak')
        if os.path.exists(bak): os.remove(bak)
        return True
    
    shutil.copy2(os.path.join(BACKUP, os.path.basename(fp)+'.bak'), fp)
    return False

# Main
total_files = len([f for f in os.listdir(BASE) if f.endswith('.py')])
err_files = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'待修复: {len(err_files)}')

fixed = 0
for f in err_files:
    fp = os.path.join(BASE, f)
    if fix_file(fp):
        fixed += 1
    print('.' if True else '', end='', flush=True)
    sys.stdout.write('\b')
    sys.stdout.write('.')
    sys.stdout.flush()

print()
final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
total_good = total_files - len(final)
print(f'总{total_files}, 修复{fixed}, 正确{total_good}, 剩余{len(final)}')
if final:
    for f in final[:20]:
        fp = os.path.join(BASE, f)
        try: ast.parse(open(fp,'r',encoding='utf-8').read())
        except SyntaxError as e:
            print(f'  L{e.lineno:<5} {str(e.msg)[:55]}  {f}')
    if len(final) > 20: print(f'  ...')
