#!/usr/bin/env python3
"""
修复所有跨行字符串模式，不破坏文档字符串。
"""
import ast, os

# 这些文件已手动修复，跳过
SKIP = {'web_fetcher.py', 'sql_generator.py', 'token_budget.py'}

def fix_file(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.split('\n')
    i = 0
    changes = 0
    
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        if '"""' in rline or "'''" in rline:
            i += 1
            continue
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        if rline.endswith('\\'):
            i += 1
            continue
        
        next_line = lines[i+1]
        ns = next_line.strip()
        
        dq = rline.count('"') - rline.count('\\"')
        sq = rline.count("'") - rline.count("\\'")
        
        if rline.endswith('"') and dq % 2 == 1 and ns.startswith('"') and not rline.endswith('"""'):
            lines[i] = rline + '\\n' + ns[1:]
            del lines[i+1]
            changes += 1
            continue
        
        if rline.endswith("'") and sq % 2 == 1 and ns.startswith("'") and not rline.endswith("'''"):
            lines[i] = rline + "\\n" + ns[1:]
            del lines[i+1]
            changes += 1
            continue
        
        i += 1
    
    if changes == 0:
        return 0
    
    new_text = '\n'.join(lines)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(new_text)
    return changes


base = 'modules'
err_files = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py') or f in SKIP:
        continue
    fp = os.path.join(base, f)
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError:
        err_files.append(f)

print(f'待修复: {len(err_files)}')

for iteration in range(10):
    still_broken = []
    fixed_any = False
    for f in err_files:
        fp = os.path.join(base, f)
        c = fix_file(fp)
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=f)
            if c > 0:
                print(f'  ✓ {f}')
            fixed_any = True
        except SyntaxError:
            still_broken.append(f)
    
    if not still_broken:
        print(f'第{iteration+1}轮: 全部修复!')
        break
    
    if not fixed_any:
        break
    
    err_files = still_broken
    print(f'第{iteration+1}轮: 剩余{len(err_files)}')

print(f'\n最终剩余: {len(err_files)}')
for f in err_files[:20]:
    try:
        ast.parse(open(os.path.join(base, f), 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError as e:
        print(f'  {f}: L{e.lineno} {str(e.msg)[:60]}')
if len(err_files) > 20:
    print(f'  ... 还有 {len(err_files)-20} 个')
