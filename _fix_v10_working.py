#!/usr/bin/env python3
"""
修复v10：基于验证过的跨行字符串修复逻辑 + 增强f-string支持
"""
import ast, os, shutil, sys

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_v10'

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
        skip_next = [False] * len(lines)
        new_lines = []
        
        i = 0
        while i < len(lines):
            if i < len(skip_next) and skip_next[i]:
                i += 1; continue
            
            line = lines[i]
            rline = line.rstrip()
            
            if i + 1 >= len(lines):
                new_lines.append(line); i += 1; continue
            
            nxt = lines[i+1]
            nstripped = nxt.strip()
            
            if rline.lstrip().startswith('#'):
                new_lines.append(line); i += 1; continue
            
            patched = False
            
            # === Pattern A: Cross-line strings ===
            for q in ('"', "'"):
                if not has_unclosed(rline, q):
                    continue
                
                # Find the LAST opening quote on this line
                # (the one that's unclosed)
                qi = nstripped.find(q)
                if qi < 0:
                    # No closing quote on next line at all
                    # Could be multi-line f-string: skip
                    continue
                
                last_q = -1
                for idx, ch in enumerate(rline):
                    if ch == q and (idx == 0 or rline[idx-1] != '\\'):
                        last_q = idx
                
                if last_q < 0:
                    continue
                
                before = rline[:last_q]
                str_content = nstripped[:qi]
                rest = nstripped[qi:]
                
                # Handle special cases
                # .join / .split / .count: the string content is \n
                if rest.startswith('.join') or rest.startswith('.split') or rest.startswith('.count'):
                    merged = before + q + '\\n' + rest
                else:
                    merged = before + q + '\\n' + str_content + rest
                
                lines[i] = merged
                skip_next[i+1] = True
                changed = True
                patched = True
                break
            
            if not patched:
                # === Pattern B: .split("\n")\n") patterns (pure format) ===
                # Line ends with something like .split(" and next line is ")
                for meth in ['.split(', '.join(', '.count(', '.replace(']:
                    if rline.rstrip().endswith(meth + '"') and nstripped == '"' + ')':
                        lines[i] = rline[:-1] + '\\\\n")'
                        skip_next[i+1] = True
                        changed = True; patched = True
                        break
                    if rline.rstrip().endswith(meth + "'") and nstripped == "'" + ')':
                        lines[i] = rline[:-1] + "\\\\n')"
                        skip_next[i+1] = True
                        changed = True; patched = True
                        break
            
            if not patched:
                # === Pattern C: Extra closing bracket ===
                if nstripped in (')', '])', '})', ')}', ']', '}') and i > 0:
                    prev = lines[i-1].rstrip()
                    opens = prev.count('(') + prev.count('[') + prev.count('{')
                    closes = prev.count(')') + prev.count(']') + prev.count('}')
                    if opens <= closes:
                        skip_next[i+1] = True
                        changed = True; patched = True
            
            if not patched:
                # === Pattern D: logger.info(y_footprint"...) ===
                if "logger.info(y_footprint" in rline:
                    lines[i] = lines[i].replace('logger.info(y_footprint"', '"memory_footprint"')
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
    sys.stdout.write('.' if fixed else 'x')
    sys.stdout.flush()

print()
final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'总{total_files}, 修复{fixed}, 正确{total_files-len(final)}, 剩余{len(final)}')
if final:
    for f in final[:15]:
        fp = os.path.join(BASE, f)
        try: ast.parse(open(fp,'r',encoding='utf-8').read())
        except SyntaxError as e:
            print(f'  L{e.lineno:<5} {str(e.msg)[:55]}  {f}')
    if len(final) > 15: print(f'  ...')
