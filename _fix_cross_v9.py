#!/usr/bin/env python3
"""v9: 只修复跨行字符串，不改任何其他内容"""
import os, re

def fix_file(filepath):
    """只修复 `"...\n..."` 跨行模式为 `"...\\n..."`"""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    original = text
    lines = text.split('\n')
    i = 0
    changes = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        # 跳过三引号、注释
        if '"""' in line or "'''" in line:
            i += 1
            continue
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        # 跳过行尾反斜杠续行
        if rline.endswith('\\'):
            i += 1
            continue
        
        ns = lines[i+1].strip()
        
        # 模式1: 行尾 " 且下一行以 " 开头（不是三引号）
        if rline.endswith('"') and ns.startswith('"') and not rline.endswith('"""'):
            # 检查行中未闭合引号：行内 " 数量为奇数
            dq = rline.count('"') - rline.count('\\"')
            if dq % 2 == 1:
                # 这是跨行字符串，合并
                lines[i] = rline + '\\n' + ns[1:]
                del lines[i+1]
                changes += 1
                continue
        
        # 模式2: 行尾 ' 且下一行以 ' 开头（不是三引号）
        if rline.endswith("'") and ns.startswith("'") and not rline.endswith("'''"):
            sq = rline.count("'") - rline.count("\\'")
            if sq % 2 == 1:
                lines[i] = rline + "\\n" + ns[1:]
                del lines[i+1]
                changes += 1
                continue
        
        i += 1
    
    if changes > 0:
        text = '\n'.join(lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
    
    return changes

base = 'modules'
fixed = 0
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(base, f)
    c = fix_file(fp)
    if c > 0:
        print(f'{f}: {c}处修复')
        fixed += 1

print(f'\n共修复 {fixed} 个文件')
