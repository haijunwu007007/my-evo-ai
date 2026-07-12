#!/usr/bin/env python3
"""v5: 正确修复跨行字符串 - 只合并引号对，不合并代码行"""
import ast, os, re

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_crossline_quotes(content):
    """
    修复跨行引号对：
    模式1: code.split("    换行    ')  →  code.split("\\n")
    模式2: return "    换行    ".join  →  return "\\n".join
    模式3: payload = "    换行    "    →  payload = "\\n"
    
    关键：只替换引号对，保持代码行不变
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        # 跳过注释、三引号、续行
        if rline.lstrip().startswith('#') or rline.endswith('\\') or rline.endswith('"""') or rline.endswith("'''"):
            i += 1
            continue
        
        next_line = lines[i+1]
        next_stripped = next_line.strip()
        
        if not next_stripped:
            i += 1
            continue
        
        # 检测：行尾是 " (非三引号)，且引号数不平衡
        dq_count = rline.count('"') - rline.count('\\"')
        
        if rline.endswith('"') and dq_count % 2 == 1:
            # 下一行以 " 开头 → 合并引号对为 \n
            if next_stripped.startswith('"'):
                # 替换: 行尾的 " + 换行 + 下行开头的 " → "\n"
                # 保持行尾的 " 为 "\\n"
                # 保持下行去掉开头的 "
                new_line = rline[:-1] + '\\n"'
                new_next = next_line.lstrip()[1:]
                lines[i] = new_line
                lines[i+1] = new_next
                # 不跳过下一行，因为它可能还有内容需要处理
                continue
            # 下一行以 ' 开头但行尾是 " → 可能是混合引号
            # 例如: text.split("  换行  ') → text.split("\n')
            # 这种情况下应该是 text.split('\n') 而不是 text.split("\n')
            # 但更可能的是引号不匹配，需要具体分析
            
        # 同理处理单引号
        sq_count = rline.count("'") - rline.count("\\'")
        if rline.endswith("'") and sq_count % 2 == 1:
            if next_stripped.startswith("'"):
                new_line = rline[:-1] + "\\n'"
                new_next = next_line.lstrip()[1:]
                lines[i] = new_line
                lines[i+1] = new_next
                continue
        
        i += 1
    
    return '\n'.join(lines)

def fix_fstring_crossline(content):
    """修复跨行 f-string"""
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        if rline.lstrip().startswith('#') or rline.endswith('\\'):
            i += 1
            continue
        
        next_line = lines[i+1]
        next_stripped = next_line.strip()
        
        if not next_stripped:
            i += 1
            continue
        
        # 检测 f-string 跨行
        # f"xxx{var}  换行  more text")
        dq_count = rline.count('"') - rline.count('\\"')
        
        # 检查是否有 f" 且引号不平衡
        has_fstring = 'f"' in rline or "f'" in rline
        if has_fstring and dq_count % 2 == 1:
            # f-string 未闭合，下一行需要合并
            # 如果下一行以 " 开头 → 合并
            if next_stripped.startswith('"'):
                new_line = rline + '\\n' + next_stripped
                lines[i] = new_line
                del lines[i+1]
                continue
            # 如果下一行不以引号开头但也是字符串内容
            elif not next_stripped.startswith(('#', 'if ', 'for ', 'def ', 'return ', 'import ', 'class ', 'else', 'elif', 'try', 'except', 'finally', 'with ', 'while ', 'break', 'continue', 'pass', 'raise', 'yield', 'assert', 'del ', 'global', 'nonlocal', 'from ')):
                new_line = rline + '\\n' + next_stripped
                lines[i] = new_line
                del lines[i+1]
                continue
        
        i += 1
    return '\n'.join(lines)

def fix_backslash_issues(content):
    """修复反斜杠相关问题"""
    # replace("\", "/") → replace("\\", "/")  
    content = content.replace('replace("\\", "/")', 'replace("\\\\", "/")')
    content = content.replace("replace('\\', '/')", "replace('\\\\', '/')")
    
    # split(\\n") → split("\n")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # \n" 但前面没有引号 → 应该是 "\n"
        if '\\n"' in line and '"\\n"' not in line and "'\\n'" not in line:
            # 检查是否是 split(\\n") 或 replace(\\n")
            if 'split(\\n"' in line or 'replace(\\n"' in line:
                line = line.replace('split(\\n"', 'split("\\n"')
                line = line.replace('replace(\\n"', 'replace("\\n"')
                lines[i] = line
    
    return '\n'.join(lines)

def fix_extra_parens(content):
    """修复多余括号"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        rstripped = line.rstrip()
        if 'logger.info(' in rstripped or 'logger.warning(' in rstripped or 'logger.error(' in rstripped or 'logger.debug(' in rstripped:
            opens = rstripped.count('(')
            closes = rstripped.count(')')
            if closes > opens:
                lines[i] = rstripped[:-(closes - opens)]
    return '\n'.join(lines)

def fix_missing_parens(content):
    """修复缺少括号"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        opens = line.count('(')
        closes = line.count(')')
        if opens > closes and not stripped.endswith('(') and not stripped.endswith(',') and not stripped.endswith('\\') and not stripped.endswith('+'):
            diff = opens - closes
            lines[i] = line + ')' * diff
    return '\n'.join(lines)

def fix_enc_paren(content):
    """修复 ENC(") → ENC(\""""
    content = content.replace('"ENC(")', '"ENC("')
    return content

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    content = fix_crossline_quotes(content)
    content = fix_fstring_crossline(content)
    content = fix_backslash_issues(content)
    content = fix_extra_parens(content)
    content = fix_missing_parens(content)
    content = fix_enc_paren(content)
    
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
for round_num in range(15):
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
        lines = open(base+'/'+f,'r',encoding='utf-8').readlines()
        ln = err.lineno
        print(f'  {f:<45} L{ln:<5} {str(err.msg)[:50]}')
        for i in range(max(0,ln-2), min(len(lines),ln+3)):
            print(f'    {i+1}: {repr(lines[i].rstrip())}')
        print()
