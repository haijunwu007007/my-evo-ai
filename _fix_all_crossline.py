"""修复所有跨行字符串 - 基于已验证的合并逻辑"""
import os, ast

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

def has_unclosed(line, q):
    cnt = 0; i = 0
    while i < len(line):
        if i < len(line)-2 and line[i:i+3] == q*3: cnt += 1; i += 3; continue
        if i > 0 and line[i-1] == '\\': i += 1; continue
        if line[i] == q: cnt += 1
        i += 1
    return cnt % 2 == 1

def fix_all(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for rnd in range(100):
        lines = text.split('\n')
        changed = False
        skipped = set()
        
        i = 0
        while i < len(lines):
            if i in skipped: i += 1; continue
            if i >= len(lines) - 1: break
            
            rline = lines[i].rstrip()
            nstripped = lines[i+1].strip()
            
            if rline.lstrip().startswith('#'):
                i += 1; continue
            
            fixed = False
            
            # Find unclosed quote and search forward for its match
            for q in ('"', "'"):
                if not has_unclosed(rline, q):
                    continue
                
                # Find last opening quote on this line
                last_q = -1
                for idx, ch in enumerate(rline):
                    if ch == q and (idx == 0 or rline[idx-1] != '\\'):
                        last_q = idx
                
                if last_q < 0: continue
                before = rline[:last_q]
                
                # Search forward for closing quote
                content_parts = []
                close_idx = -1
                content = ''
                
                for j in range(i+1, len(lines)):
                    lj = lines[j]
                    stripped_j = lj.strip()
                    
                    # Find first unescaped q
                    qi = -1
                    for k, ch in enumerate(stripped_j):
                        if ch == q and (k == 0 or stripped_j[k-1] != '\\'):
                            qi = k
                            break
                    
                    if qi >= 0:
                        close_idx = j
                        content_before = stripped_j[:qi]
                        rest = stripped_j[qi:]  # includes q
                        
                        if content_parts or content_before:
                            all_parts = content_parts + [content_before]
                            content = '\\n'.join(p for p in all_parts if p)
                        else:
                            content = '\\n'
                        
                        # Handle special cases: .join(.split() patterns
                        if content == '\\n' and (rest.startswith('.join') or rest.startswith('.split') or rest.startswith('.count') or rest.startswith('.replace')):
                            merged = before + q + content + rest
                        elif rest and rest != q:
                            merged = before + q + content + rest
                        else:
                            merged = before + q + content + rest
                        
                        lines[i] = merged
                        for k in range(i+1, close_idx + 1):
                            skipped.add(k)
                        changed = True
                        fixed = True
                        break
                    else:
                        content_parts.append(stripped_j)
                
                if fixed:
                    break
            
            if not fixed and nstripped in (')', '])', '})', ')}', ']') and i > 0:
                prev = lines[i-1].rstrip()
                opens = prev.count('(') + prev.count('[') + prev.count('{')
                closes = prev.count(')') + prev.count(']') + prev.count('}')
                if opens <= closes:
                    skipped.add(i+1)
                    changed = True
            
            i += 1
        
        if not changed: break
        new_lines = [l for idx, l in enumerate(lines) if idx not in skipped]
        text = '\n'.join(new_lines)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
        return True
    except:
        return False

def is_ok(fp):
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
        return True
    except:
        return False

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
errs = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not is_ok(os.path.join(BASE, f))]

fixed = 0
for f in errs:
    fp = os.path.join(BASE, f)
    if fix_all(fp):
        fixed += 1

final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not is_ok(os.path.join(BASE, f))]
print(f'总{total}, 修复{fixed}, 剩余{len(final)}')
for f in final[:15]:
    fp = os.path.join(BASE, f)
    try: ast.parse(open(fp, 'r', encoding='utf-8').read())
    except SyntaxError as e:
        print(f'  L{e.lineno:<5} {str(e.msg)[:55]}  {f}')

