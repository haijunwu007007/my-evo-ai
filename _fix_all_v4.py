#!/usr/bin/env python3
"""v4: 终极修复 - 精准匹配所有跨行模式"""
import ast, os, re

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_crossline_fstring(content):
    """修复跨行 f-string: f"...{xxx} 换行 ...}" → f"...{xxx}\\n...}" """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        if rline.lstrip().startswith('#') or rline.endswith('\\'):
            i += 1
            continue
        
        # 检测 f-string 跨行: 行中有 f" 但没有闭合
        # f" 后面有 {xxx} 但 " 没闭合，下一行以 " 或内容开头
        stripped = rline.lstrip()
        
        # 检查引号是否平衡
        dq_count = rline.count('"') - rline.count('\\"')
        sq_count = rline.count("'") - rline.count("\\'")
        
        if dq_count % 2 == 1:  # 双引号不平衡
            # 下一行如果以 " 开头，合并
            next_line = lines[i+1]
            next_stripped = next_line.strip()
            if next_stripped.startswith('"'):
                merged = rline + '\\n' + next_stripped
                lines[i] = merged
                del lines[i+1]
                continue
            # 下一行不以 " 开头但以 ' 开头
            if next_stripped.startswith("'"):
                merged = rline + '\\n' + next_stripped
                lines[i] = merged
                del lines[i+1]
                continue
            # 下一行不以引号开头但内容是字符串的延续（如 00:00:00,000）
            # 如果下一行不以代码关键字开头（如 if/for/def/return/import/class）
            if next_stripped and not next_stripped.startswith(('#', 'if ', 'for ', 'def ', 'return ', 'import ', 'class ', 'from ', 'else', 'elif', 'try', 'except', 'finally', 'with ', 'while ', 'break', 'continue', 'pass', 'raise', 'yield', 'assert', 'del ', 'global', 'nonlocal')):
                merged = rline + '\\n' + next_stripped
                lines[i] = merged
                del lines[i+1]
                continue
                
        if sq_count % 2 == 1:
            next_line = lines[i+1]
            next_stripped = next_line.strip()
            if next_stripped.startswith("'"):
                merged = rline + '\\n' + next_stripped
                lines[i] = merged
                del lines[i+1]
                continue
        
        i += 1
    return '\n'.join(lines)

def fix_backslash_n(content):
    """修复 \\n" → "\n" 被截断的模式"""
    # code.split(\\n") → code.split("\n")
    content = content.replace('split(\\\\n")', 'split("\\n")')
    content = content.replace('.split(\\\\n\'', '.split(\'\\n\'')
    # code.split(\n") → code.split("\n")
    # 更通用的修复: 行中出现的 \n" 但前面没有引号
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 模式: .split(\n") → .split("\n")
        if '\\n"' in line and '"\\n"' not in line:
            line = line.replace('\\n"', '"\\n"')
            lines[i] = line
        if "\\\\n'" in line and "'\\\\n'" not in line:
            line = line.replace("\\\\n'", "'\\\\n'")
            lines[i] = line
    return '\n'.join(lines)

def fix_enc_paren(content):
    """修复 "ENC(") → "ENC(" """
    content = content.replace('"ENC(")', '"ENC("')
    return content

def fix_missing_comma_in_call(content):
    """修复多行函数调用中缺少逗号"""
    lines = content.split('\n')
    for i in range(len(lines) - 1):
        line = lines[i].rstrip()
        next_stripped = lines[i+1].strip()
        # 行以值结尾，下一行也是值，中间缺逗号
        if (line.endswith('"') or line.endswith("'") or line.endswith(')') or line.endswith(']') or line.endswith('}')) and not line.endswith(','):
            if next_stripped and not next_stripped.startswith(('#', ')', ']', '}', 'if ', 'for ', 'def ', 'return ', 'import ', 'class ', 'else', 'elif', 'try', 'except', 'finally', 'with ', 'while ', 'break', 'continue', 'pass', 'raise', 'yield', 'assert', 'del ', 'global', 'nonlocal', 'from ')):
                # 只有在函数调用/列表/字典的上下文中才加逗号
                # 粗略判断：前面有 ( 或 [ 或 {
                # 检查缩进是否一致
                if lines[i].rstrip() and next_stripped and len(line) - len(line.lstrip()) == len(lines[i+1]) - len(lines[i+1].lstrip()):
                    lines[i] = line + ','
    return '\n'.join(lines)

def fix_crossline_regex(content):
    """修复跨行正则: r"[。；]) 换行 ]" → r"[。；]" """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        # 检测 r" 结尾且引号未闭合
        if 'r"' in rline:
            # 统计 r" 后面的 " 数量
            last_rquote = rline.rfind('r"')
            after_r = rline[last_rquote+2:]
            dq_after = after_r.count('"')
            if dq_after == 0:  # r" 后面没有闭合引号
                next_line = lines[i+1].strip()
                if next_line.startswith(']'):
                    # 合并: r"[。；])\n]" → r"[。；]"
                    merged = rline + next_line
                    lines[i] = merged
                    del lines[i+1]
                    continue
                elif next_line.startswith('"'):
                    merged = rline + next_line
                    lines[i] = merged
                    del lines[i+1]
                    continue
        i += 1
    return '\n'.join(lines)

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    content = fix_crossline_fstring(content)
    content = fix_backslash_n(content)
    content = fix_enc_paren(content)
    content = fix_crossline_regex(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return try_parse(filepath)

# 收集所有错误文件
files = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    err = try_parse(base + '/' + f)
    if err:
        files.append(f)

print(f'待修复: {len(files)} 个')

# 多轮修复
for round_num in range(10):
    fixed_this_round = 0
    still_broken = []
    for f in files:
        fp = base + '/' + f
        err = fix_file(fp)
        if err is None:
            fixed_this_round += 1
        else:
            still_broken.append(f)
    files = still_broken
    if fixed_this_round > 0:
        print(f'  第{round_num+1}轮: 修复{fixed_this_round}, 剩余{len(files)}')
    if fixed_this_round == 0:
        break

print(f'\n总计剩余: {len(files)}')
for f in files:
    err = try_parse(base + '/' + f)
    if err:
        print(f'  {f:<45} L{err.lineno:<5} {str(err.msg)[:50]}')
