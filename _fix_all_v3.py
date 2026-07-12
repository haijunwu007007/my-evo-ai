#!/usr/bin/env python3
"""v3: 逐文件精准修复 - 针对每种错误模式"""
import ast, os, re

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_crossline_strings(content):
    """修复跨行字符串: 行尾 " 换行 " → \\n"""
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        if rline.lstrip().startswith('#') or rline.endswith('\\') or rline.endswith('"""') or rline.endswith("'''"):
            i += 1
            continue
        
        next_stripped = lines[i+1].strip()
        if not next_stripped:
            i += 1
            continue
            
        # 检测行尾 " 且下一行以 " 开头（非注释）
        if rline.endswith('"') and next_stripped.startswith('"') and not next_stripped.startswith('"""'):
            # 检查是否在字符串内（粗略检查引号数）
            quote_count = rline.count('"') - rline.count('\\"')
            if quote_count % 2 == 1:  # 奇数引号 = 字符串未闭合
                merged = rline[:-1] + '\\n"' + next_stripped[1:]
                lines[i] = merged
                del lines[i+1]
                continue
        
        if rline.endswith("'") and next_stripped.startswith("'") and not next_stripped.startswith("'''"):
            sq_count = rline.count("'") - rline.count("\\'")
            if sq_count % 2 == 1:
                merged = rline[:-1] + "\\n'" + next_stripped[1:]
                lines[i] = merged
                del lines[i+1]
                continue
        i += 1
    return '\n'.join(lines)

def fix_missing_paren(content):
    """修复缺少右括号"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # 统计圆括号
        opens = line.count('(')
        closes = line.count(')')
        # 统计方括号
        bopens = line.count('[')
        bcloses = line.count(']')
        
        # 如果 ( 比 ) 多且行尾不是 ( 或 ,
        if opens > closes and not stripped.endswith('(') and not stripped.endswith(',') and not stripped.endswith('\\'):
            diff = opens - closes
            lines[i] = line + ')' * diff
        # 如果 [ 比 ] 多
        if bopens > bcloses and not stripped.endswith('[') and not stripped.endswith(',') and not stripped.endswith('\\'):
            diff = bopens - bcloses
            lines[i] = line + ']' * diff
    return '\n'.join(lines)

def fix_double_paren(content):
    """修复多余右括号 logger.info("xxx")) """
    lines = content.split('\n')
    for i, line in enumerate(lines):
        rstripped = line.rstrip()
        if ('logger.info(' in line or 'logger.warning(' in line or 'logger.error(' in line or 'logger.debug(' in line):
            opens = line.count('(')
            closes = line.count(')')
            if closes > opens:
                lines[i] = rstripped[:-(closes - opens)] 
    return '\n'.join(lines)

def fix_backslash_replace(content):
    """修复 replace("\\", "/") 被截断"""
    # 模式: replace("\", "/") → replace("\\", "/")
    content = content.replace('replace("\\", "/")', 'replace("\\\\", "/")')
    content = content.replace('replace("\\",\'/\')', 'replace("\\\\",\'/\')')
    content = content.replace("replace('\\','/')", "replace('\\\\','/')")
    return content

def fix_missing_comma_in_list(content):
    """修复列表/字典中缺少逗号"""
    lines = content.split('\n')
    for i in range(len(lines) - 1):
        line = lines[i].rstrip()
        next_line = lines[i+1].strip()
        # 行以 } 或 ) 结尾，下一行以 { 或 " 开头 → 可能缺逗号
        if (line.endswith('}') or line.endswith(')')) and (next_line.startswith('{') or next_line.startswith('"') or next_line.startswith("'")):
            # 检查是否已经在函数调用参数中
            if not line.endswith(','):
                lines[i] = line + ','
    return '\n'.join(lines)

def fix_file(filepath):
    """尝试多种修复策略"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    
    # 策略1: 跨行字符串
    content = fix_crossline_strings(content)
    
    # 策略2: 反斜杠替换
    content = fix_backslash_replace(content)
    
    # 策略3: 多余括号
    content = fix_double_paren(content)
    
    # 策略4: 缺少括号
    content = fix_missing_paren(content)
    
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
for round_num in range(5):
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
    print(f'  第{round_num+1}轮: 修复{fixed_this_round}, 剩余{len(files)}')
    if fixed_this_round == 0:
        break

print(f'\n总计剩余: {len(files)}')
for f in files:
    err = try_parse(base + '/' + f)
    if err:
        print(f'  {f:<45} L{err.lineno:<5} {str(err.msg)[:50]}')
