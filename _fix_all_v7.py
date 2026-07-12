#!/usr/bin/env python3
"""
v7: 修复被之前脚本改坏的 \\n" 模式
原始代码是跨行的: payload = "   换行   ".join(lines)
被v9改成了: payload = \\n"  换行  .join(lines)
需要改回: payload = "\\n".join(lines)

同时修复: 
- code.split(\\n")  →  code.split("\\n")
- \\n" 后跟换行+代码 → "\\n" + 代码留在同一行
"""
import ast, os, re

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_broken_newline_quotes(content):
    """
    修复 \\n" 模式（被v9脚本改坏的跨行字符串）
    
    模式1: payload = \\n"   换行   .join(lines)
           → payload = "\\n".join(lines)
    
    模式2: code.split(\\n")  换行  )
           → code.split("\\n")
    
    模式3: text.split(\\n')  换行  )
           → text.split('\\n')
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检测 \\n" 或 \\n' 在行尾或行中
        # 模式: xxx = \\n"  或  xxx.split(\\n")  或  xxx.split(\\n')
        
        # 1. 行尾 = \\n" → 把下一行的内容合并到当前行
        if line.rstrip().endswith('\\n"'):
            if i + 1 < len(lines):
                next_content = lines[i+1].strip()
                # 合并: = \\n" + .join(lines) → = "\\n".join(lines)
                merged = line.rstrip()[:-3] + '"\\n"' + next_content
                lines[i] = merged
                del lines[i+1]
                continue
        
        if line.rstrip().endswith("\\n'"):
            if i + 1 < len(lines):
                next_content = lines[i+1].strip()
                merged = line.rstrip()[:-3] + "'\\n'" + next_content
                lines[i] = merged
                del lines[i+1]
                continue
        
        # 2. split(\\n") → split("\\n")
        if 'split(\\n")' in line:
            line = line.replace('split(\\n")', 'split("\\n")')
            lines[i] = line
        if "split(\\n')" in line:
            line = line.replace("split(\\n')", "split('\\n')")
            lines[i] = line
        
        # 3. replace(\\n", → replace("\\n",
        if 'replace(\\n"' in line:
            line = line.replace('replace(\\n"', 'replace("\\n"')
            lines[i] = line
        
        # 4. 行尾有 \\n" 且下一行不是 .join → 可能是 + \\n" 模式
        # payload = "\\n".join(lines) + \\n"
        # → payload = "\\n".join(lines) + "\\n"
        if line.rstrip().endswith('+ \\n"') or line.rstrip().endswith('+\\n"'):
            if i + 1 < len(lines) and not lines[i+1].strip().startswith('.'):
                # 直接修复为 + "\\n"
                lines[i] = line.rstrip().replace('+ \\n"', '+ "\\n"').replace('+\\n"', '+"\\n"')
                # 如果下一行是空行或 .join 之类的，删除空行
                if lines[i+1].strip() == '' and i+2 < len(lines) and not lines[i+2].strip().startswith('.'):
                    del lines[i+1]
                    continue
        
        # 5. join(\\n" → join("\\n"  (不太可能但以防万一)
        if 'join(\\n"' in line:
            line = line.replace('join(\\n"', 'join("\\n"')
            lines[i] = line
            
        i += 1
    
    return '\n'.join(lines)

def fix_crossline_strings_original(content):
    """
    修复原始的跨行字符串（未被v9改过的）
    行尾 " + 换行 + " → "\\n" (合并引号对，不合并代码行)
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        if rline.lstrip().startswith('#') or rline.endswith('\\') or rline.endswith('"""') or rline.endswith("'''"):
            i += 1
            continue
        
        next_line = lines[i+1]
        next_stripped = next_line.strip()
        if not next_stripped:
            i += 1
            continue
        
        # 双引号不平衡且行尾是 "
        dq = rline.count('"') - rline.count('\\"')
        if rline.endswith('"') and dq % 2 == 1:
            # 下一行以 " 开头
            if next_stripped.startswith('"') and not next_stripped.startswith('"""'):
                lines[i] = rline[:-1] + '\\n"'
                lines[i+1] = next_line.lstrip()[1:]
                continue
            # 下一行不以 " 开头但是字符串内容（如 ## 概述, 00:00:00 等）
            # 判断：下一行不以代码关键字开头
            code_starts = ('if ', 'for ', 'def ', 'return ', 'import ', 'class ', 'else', 'elif', 'try:', 'except', 'finally:', 'with ', 'while ', 'break', 'continue', 'pass', 'raise', 'yield', 'assert', 'del ', 'global', 'nonlocal', 'from ', '@', '#')
            if not any(next_stripped.startswith(s) for s in code_starts):
                # 合并为 f-string 或字符串的延续
                lines[i] = rline + '\\n' + next_stripped
                del lines[i+1]
                continue
        
        # 单引号
        sq = rline.count("'") - rline.count("\\'")
        if rline.endswith("'") and sq % 2 == 1:
            if next_stripped.startswith("'") and not next_stripped.startswith("'''"):
                lines[i] = rline[:-1] + "\\n'"
                lines[i+1] = next_line.lstrip()[1:]
                continue
        
        i += 1
    return '\n'.join(lines)

def fix_backslash_replace(content):
    content = content.replace('replace("\\", "/")', 'replace("\\\\", "/")')
    content = content.replace("replace('\\','/')", "replace('\\\\','/')")
    return content

def fix_enc_paren(content):
    content = content.replace('"ENC(")', '"ENC("')
    return content

def fix_send_dict(content):
    # .send({) → .send({
    content = content.replace('.send({)', '.send({')
    return content

def fix_extra_close_paren(content):
    lines = content.split('\n')
    for i, line in enumerate(lines):
        rstripped = line.rstrip()
        for func in ['logger.info', 'logger.warning', 'logger.error', 'logger.debug']:
            if func + '(' in rstripped:
                opens = rstripped.count('(')
                closes = rstripped.count(')')
                if closes > opens:
                    lines[i] = rstripped[:-(closes - opens)]
    return '\n'.join(lines)

def fix_timezone_utc(content):
    """修复 from datetime import ..., timezone, timezone.utc"""
    content = content.replace(', timezone, timezone.utc', ', timezone')
    content = content.replace(', timezone.utc, timezone', ', timezone')
    return content

def fix_repo_lines_append(content):
    """修复 repo_lines.append({) → repo_lines.append({"""
    content = content.replace('.append({)', '.append({')
    return content

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    content = fix_broken_newline_quotes(content)
    content = fix_crossline_strings_original(content)
    content = fix_backslash_replace(content)
    content = fix_enc_paren(content)
    content = fix_send_dict(content)
    content = fix_extra_close_paren(content)
    content = fix_timezone_utc(content)
    content = fix_repo_lines_append(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return try_parse(filepath)

# 收集错误文件
files = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    err = try_parse(base + '/' + f)
    if err:
        files.append(f)

print(f'待修复: {len(files)} 个')

for round_num in range(20):
    fixed_this = 0
    still_broken = []
    for f in files:
        fp = base + '/' + f
        err = fix_file(fp)
        if err is None:
            fixed_this += 1
        else:
            still_broken.append(f)
    files = still_broken
    if fixed_this > 0:
        print(f'  第{round_num+1}轮: 修复{fixed_this}, 剩余{len(files)}')
    if fixed_this == 0:
        break

print(f'\n总计剩余: {len(files)}')
for f in files:
    err = try_parse(base + '/' + f)
    if err:
        lines = open(base+'/'+f,'r',encoding='utf-8').readlines()
        ln = err.lineno
        print(f'  {f:<45} L{ln:<5} {str(err.msg)[:50]}')
        for i in range(max(0,ln-2), min(len(lines),ln+3)):
            print(f'    {i+1}: {repr(lines[i].rstrip())}')
        print()
