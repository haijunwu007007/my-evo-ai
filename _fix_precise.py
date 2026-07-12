#!/usr/bin/env python3
"""精准修复剩余语法错误，只修已知模式，失败回滚"""
import ast, os, shutil, re

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_backup'
os.makedirs(BACKUP, exist_ok=True)

def parse_ok(fp):
    try:
        with open(fp,'r',encoding='utf-8') as f: ast.parse(f.read(),filename=fp); return True
    except: return False

def get_err(fp):
    try:
        with open(fp,'r',encoding='utf-8') as f: ast.parse(f.read(),filename=fp); return None
    except SyntaxError as e: return e

def fix_crossline_join(content):
    """修复 .split("\n")\n")  → .split("\\n")"""
    lines = content.split('\n')
    changed = False
    i = 0
    while i < len(lines) - 1:
        r = lines[i].rstrip()
        n = lines[i+1].strip()
        if r.endswith('("') and n == '")':
            lines[i] = r[:-1] + '\\\\n")'
            del lines[i+1]; changed = True; continue
        if r.endswith("('") and n == "')":
            lines[i] = r[:-1] + "\\\\n')"
            del lines[i+1]; changed = True; continue
        if r.endswith('("') and n.startswith('")'):
            lines[i] = r[:-1] + '\\\\n' + n[1:]
            del lines[i+1]; changed = True; continue
        if r.endswith("('") and n.startswith("')"):
            lines[i] = r[:-1] + "\\\\n" + n[1:]
            del lines[i+1]; changed = True; continue
        i += 1
    return '\n'.join(lines) if changed else content

def fix_extra_paren(content):
    """修复多余的 ) 或 ] 另起一行"""
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        n = lines[i+1].strip()
        if n in (')', '])', '})', ')]', ')}'):
            cur = lines[i].rstrip()
            op = cur.count('(') + cur.count('[') + cur.count('{')
            cl = cur.count(')') + cur.count(']') + cur.count('}')
            if op <= cl and op > 0:
                del lines[i+1]; continue
        i += 1
    return '\n'.join(lines)

def fix_crossline_str(content):
    """修复跨行字符串：行尾未闭合引号+下行闭合"""
    lines = content.split('\n')
    merged = False
    i = 0
    while i < len(lines) - 1:
        r = lines[i].rstrip()
        n = lines[i+1].strip()
        
        # 判断行尾是否未闭合字符串
        for q in ('"', "'"):
            if r.endswith(q) and not r.endswith(q*3) and not r.endswith('\\'+q):
                cnt = r.count(q) - r.count('\\'+q)
                if cnt % 2 == 1:  # 未闭合
                    # 下行以同引号开头
                    if n.startswith(q):
                        rest = n[len(q):]
                        lines[i] = r.rstrip(q) + '\\\\n' + q + rest
                        del lines[i+1]; merged = True; break
                    # 下行以同引号结尾（纯内容）
                    if n.endswith(q) and len(n) > 1:
                        lines[i] = r + '\\\\n' + n
                        del lines[i+1]; merged = True; break
        if merged:
            merged = False
            continue
        i += 1
    return '\n'.join(lines)

def fix_regex_crossline(content):
    """修复跨行正则：r"..."\n"]"""
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        r = lines[i].rstrip()
        n = lines[i+1].strip()
        # 匹配 r" 没有闭合
        for m in re.finditer(r'r"', r):
            after = r[m.end():]
            dq = after.count('"') - after.count('\\"')
            if dq == 0:  # r" 后的引号未闭合
                if n.startswith('"') or n == '"]' or n.startswith('"]'):
                    lines[i] = r + n
                    del lines[i+1]
                    break
        i += 1
    return '\n'.join(lines)

def fix_file(fp):
    err = get_err(fp)
    if err is None: return True
    
    shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp)+'.bak'))
    
    with open(fp,'r',encoding='utf-8') as f: content = f.read()
    
    for _ in range(15):
        old = content
        content = fix_crossline_join(content)
        content = fix_extra_paren(content)
        content = fix_crossline_str(content)
        content = fix_regex_crossline(content)
        if content == old: break
    
    with open(fp,'w',encoding='utf-8') as f: f.write(content)
    
    if get_err(fp) is None: return True
    # 回滚
    shutil.copy2(os.path.join(BACKUP, os.path.basename(fp)+'.bak'), fp)
    return False

# Main
broken = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not parse_ok(os.path.join(BASE, f))]
print(f'待修复: {len(broken)}')

fixed = 0
for f in broken:
    fp = os.path.join(BASE, f)
    if fix_file(fp):
        fixed += 1
        print(f'  ✅ {f}')
    else:
        err = get_err(fp)
        print(f'  ❌ {f:<45} L{err.lineno:<5} {str(err.msg)[:50]}')

rem = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not parse_ok(os.path.join(BASE, f))]
print(f'\n修复: {fixed}, 剩余: {len(rem)}')
for f in rem[:20]:
    err = get_err(os.path.join(BASE, f))
    print(f'  {f:<45} L{err.lineno:<5} {str(err.msg)[:50]}')
if len(rem) > 20: print(f'  ... 还有 {len(rem)-20} 个')
