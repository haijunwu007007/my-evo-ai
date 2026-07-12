#!/usr/bin/env python3
"""
v10: 更智能的跨行字符串修复。
遍历所有有语法错误的文件，找到所有未闭合字符串并修复。
"""
import ast, os, re

def find_crosslines(lines):
    """找到所有跨行字符串位置"""
    results = []
    i = 0
    while i < len(lines) - 1:
        l = lines[i]
        rl = l.rstrip()
        # 跳过三引号、注释、反斜杠续行
        if '"""' in l or "'''" in l:
            i += 1
            continue
        if rl.lstrip().startswith('#'):
            i += 1
            continue
        if rl.endswith('\\'):
            i += 1
            continue
        
        ns = lines[i+1].strip()
        
        # 检查行尾引号未闭合
        dq = rl.count('"') - rl.count('\\"')
        sq = rl.count("'") - rl.count("\\'")
        
        if rl.endswith('"') and not rl.endswith('"""') and dq % 2 == 1:
            # 行尾 " 未闭合，下一行以 " 开头
            if ns.startswith('"'):
                results.append((i, rl, ns, '"'))
        elif rl.endswith("'") and not rl.endswith("'''") and sq % 2 == 1:
            if ns.startswith("'"):
                results.append((i, rl, ns, "'"))
        
        i += 1
    return results

def fix_file_v2(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.split('\n')
    cross = find_crosslines(lines)
    
    if not cross:
        return 0
    
    # 从后往前修复，避免行号变动
    for idx, rl, ns, quote in reversed(cross):
        # 判断这应该是 \n 还是其他内容
        # 如果下一行只有引号+闭合括号，如 " + ... ) 或 ".join(...)
        stripped_ns = ns.strip(quote)
        stripped_rl = rl.rstrip(quote)
        
        # 检查内容：如果是 .join / .split 等，用 \n
        # 如果是纯文本内容，也用 \n
        if stripped_ns.startswith('.') or stripped_ns.startswith(')') or stripped_ns.startswith(']'):
            # split("\n") 或 join("\n")
            pass
        
        # 构建新行
        new_line = stripped_rl + '\\n' + stripped_ns
        lines[idx] = new_line
        del lines[idx + 1]
    
    if cross:
        new_text = '\n'.join(lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_text)
    
    return len(cross)

# 只处理有语法错误的文件
base = 'modules'
files_with_errors = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    try:
        ast.parse(open(os.path.join(base, f), 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError:
        files_with_errors.append(f)

print(f'语法错误文件: {len(files_with_errors)}')

total_fixed = 0
for f in files_with_errors:
    fp = os.path.join(base, f)
    c = fix_file_v2(fp)
    if c > 0:
        print(f'  {f}: {c}处修复')
        total_fixed += 1

print(f'\n修复了 {total_fixed} 个文件')

# 最终验证
remaining = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    try:
        ast.parse(open(os.path.join(base, f), 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError:
        remaining.append(f)

print(f'剩余语法错误: {len(remaining)}')
for f in remaining:
    try:
        ast.parse(open(os.path.join(base, f), 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError as e:
        print(f'  {f}: L{e.lineno} {e.msg[:60]}')
