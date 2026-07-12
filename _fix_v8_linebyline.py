#!/usr/bin/env python3
"""
修复v8：逐文件暴力扫描跨行字符串模式
策略：直接按行遍历，检测行尾未闭合引号+下行闭合，合并
"""
import ast, os, shutil, sys

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_v8'
os.makedirs(BACKUP, exist_ok=True)

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

def count_unclosed(line, q):
    """计算行中引号是否未闭合"""
    in_triple = False
    cnt = 0
    i = 0
    while i < len(line):
        if line[i:i+3] == q*3:
            in_triple = not in_triple
            i += 3
            continue
        if i > 0 and line[i-1] == '\\':
            i += 1
            continue
        if line[i] == q and not in_triple:
            cnt += 1
        i += 1
    return cnt % 2 == 1  # True = unclosed

def fix_file(fp):
    if verify(fp):
        return True
    
    shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp) + '.bak'))
    
    with open(fp, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8')
    
    for _round in range(30):
        lines = text.split('\n')
        changed = False
        new_lines = []
        skip_next = False
        
        i = 0
        while i < len(lines):
            if skip_next:
                skip_next = False
                i += 1
                continue
            
            line = lines[i]
            rline = line.rstrip()
            
            if i + 1 >= len(lines):
                new_lines.append(line)
                i += 1
                continue
            
            next_line = lines[i+1]
            nstripped = next_line.strip()
            
            # Skip commented lines
            if rline.lstrip().startswith('#') or nstripped.startswith('#'):
                new_lines.append(line)
                i += 1
                continue
            
            fixed = False
            
            # Check for ANY unclosed " or ' on this line (not just trailing)
            for q in ('"', "'"):
                if not count_unclosed(rline, q):
                    continue
                
                # Check if next line starts with same quote
                # (the closing quote is on the next line)
                if nstripped.startswith(q):
                    # Find the content between the quotes
                    # Split the line at the LAST unclosed quote
                    # Find the LAST occurrence of an unclosed quote
                    q_indices = []
                    for idx, ch in enumerate(rline):
                        if ch == q and (idx == 0 or rline[idx-1] != '\\'):
                            q_indices.append(idx)
                    
                    if len(q_indices) % 2 == 0:
                        # Even count - find the first opening quote and last closing quote
                        # Actually all quotes are balanced, weird
                        before = rline + '\\n'
                    else:
                        # Odd count - the LAST quote is the start of an unclosed string
                        # Actually the first odd-positioned quote (1st, 3rd, etc.) opens a string
                        # We need the LAST opening quote (last odd-positioned index)
                        # For "count odd": the indexing starts at 0 which is odd (1st position)
                        # So positions 0, 2, 4, 6... are opening quotes
                        # Position 0 = index q_indices[0] opens the first string
                        # Position 1 = index q_indices[1] closes it
                        # Position 2 = index q_indices[2] opens the next string ...
                        # Position n where n is even = opening, odd = closing
                        # The last opening is at position len(q_indices)-1 if len is odd
                        last_open_idx = q_indices[-1]  # last opening quote
                        before = rline[:last_open_idx]  # content before the opening quote
                    
                    after = nstripped[len(q):]  # remove leading quote from next line
                    merged = before + q + '\\n' + q + after
                    
                    lines[i] = merged
                    skip_next = True
                    changed = True
                    fixed = True
                    break
            
            if not fixed and nstripped in (')', '])', '})', ')}', ']', '}') and i > 0:
            
            if not fixed and nstripped in (')', '])', '})', ')}', ']', '}') and i > 0:
                # Check if prev line has balanced brackets
                prev = lines[i-1].rstrip()
                opens = prev.count('(') + prev.count('[') + prev.count('{')
                closes = prev.count(')') + prev.count(']') + prev.count('}')
                if opens <= closes:
                    skip_next = True
                    changed = True
            
            if not skip_next:
                new_lines.append(line)
            i += 1
        
        if not changed:
            break
        text = '\n'.join(new_lines)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    
    if verify(fp):
        os.remove(os.path.join(BACKUP, os.path.basename(fp) + '.bak'))
        return True
    
    shutil.copy2(os.path.join(BACKUP, os.path.basename(fp) + '.bak'), fp)
    return False

# Main
err_files = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'待修复: {len(err_files)}')

fixed = 0
for f in err_files:
    fp = os.path.join(BASE, f)
    if fix_file(fp):
        fixed += 1
        sys.stdout.write('.')
        sys.stdout.flush()
    else:
        sys.stdout.write('x')
        sys.stdout.flush()

print()
final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
print(f'\n总{total}, 修复{fixed}, 正确{total-len(final)}, 剩余{len(final)}')
for f in final[:10]:
    fp = os.path.join(BASE, f)
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read())
    except SyntaxError as e:
        print(f'  {f:<45} L{e.lineno:<5} {str(e.msg)[:50]}')
if len(final) > 10:
    print(f'  ... 还有{len(final)-10}个')
