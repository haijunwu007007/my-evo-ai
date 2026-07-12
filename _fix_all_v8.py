#!/usr/bin/env python3
"""v8: 精准修复剩余53个文件的特定错误模式"""
import ast, os, re

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_split_extra_paren(content):
    """
    修复 split("\\n") 后多了一个 )
    模式: split("\\n")\n) → split("\\n")
    """
    # 通用: 行尾以 " 结尾，下一行只有 )
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        next_stripped = lines[i+1].strip()
        
        # 下一行只有 ) 或 ] 或 } 
        if next_stripped in (')', ']', '}', ')]', '})', ')}'):
            # 检查当前行是否括号已平衡
            opens = rline.count('(') + rline.count('[') + rline.count('{')
            closes = rline.count(')') + rline.count(']') + rline.count('}')
            if opens == closes:
                # 当前行括号已平衡，下一行的括号是多余的
                del lines[i+1]
                continue
        i += 1
    return '\n'.join(lines)

def fix_fstring_crossline_v2(content):
    """
    修复跨行 f-string:
    f"...{var}'
    换行
    more text"
    → f"...{var}\\nmore text"
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        if rline.lstrip().startswith('#') or rline.endswith('\\'):
            i += 1
            continue
        
        # 检测 f-string 未闭合
        # 查找行中的 f" 或 f'
        has_fstring = bool(re.search(r'(?:^|[^f])f["\']', rline)) or rline.lstrip().startswith('f"') or rline.lstrip().startswith("f'")
        
        dq = rline.count('"') - rline.count('\\"')
        sq = rline.count("'") - rline.count("\\'")
        
        # f-string 未闭合：引号不平衡
        if (rline.endswith('"') and dq % 2 == 1) or (rline.endswith("'") and sq % 2 == 1):
            # 检查这是否是一个未闭合的 f-string 或普通字符串
            # 合并后续行直到引号闭合
            merged = rline
            j = i + 1
            merged_lines = []
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    j += 1
                    continue
                # 检查下一行是否是代码行（以代码关键字开头）
                code_starts = ('if ', 'for ', 'def ', 'return ', 'import ', 'class ', 'else', 'elif', 'try:', 'except', 'finally:', 'with ', 'while ', 'break', 'continue', 'pass', 'raise', 'yield', 'assert', 'del ', 'global', 'nonlocal', 'from ', '@', '#')
                if any(next_stripped.startswith(s) for s in code_starts):
                    break
                # 下一行以 " 或 ' 开头 → 可能是闭合
                if next_stripped.startswith('"') or next_stripped.startswith("'"):
                    merged += '\\n' + next_stripped
                    merged_lines.append(j)
                    # 检查是否闭合
                    new_dq = merged.count('"') - merged.count('\\"')
                    new_sq = merged.count("'") - merged.count("\\'")
                    if (rline.endswith('"') and new_dq % 2 == 0) or (rline.endswith("'") and new_sq % 2 == 0):
                        break
                    j += 1
                    continue
                # 非代码非引号开头 → 字符串内容
                merged += '\\n' + next_stripped
                merged_lines.append(j)
                new_dq = merged.count('"') - merged.count('\\"')
                new_sq = merged.count("'") - merged.count("\\'")
                if (rline.endswith('"') and new_dq % 2 == 0) or (rline.endswith("'") and new_sq % 2 == 0):
                    break
                j += 1
            
            if merged_lines:
                lines[i] = merged
                for k in sorted(merged_lines, reverse=True):
                    del lines[k]
                continue
        
        i += 1
    return '\n'.join(lines)

def fix_crossline_regex_v2(content):
    """
    修复跨行正则:
    re.split(r"[。！？)]'   换行   ;]+"
    → re.split(r"[。！？);]+"
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        # 检测 r" 未闭合
        # 查找 r" 后面没有闭合的 "
        rquote_pos = rline.rfind('r"')
        if rquote_pos >= 0:
            after_r = rline[rquote_pos + 2:]
            dq_after = after_r.count('"')
            if dq_after == 0:  # r" 后面没有闭合引号
                # 下一行可能是闭合
                for j in range(i+1, min(i+3, len(lines))):
                    next_stripped = lines[j].strip()
                    if next_stripped.startswith('"'):
                        merged = rline + next_stripped
                        lines[i] = merged
                        del lines[j]
                        break
                    elif next_stripped.startswith(']') or next_stripped.startswith("'"):
                        merged = rline + next_stripped
                        lines[i] = merged
                        del lines[j]
                        break
        i += 1
    return '\n'.join(lines)

def fix_logger_info_broken(content):
    """
    修复 logger.info(y_footprint": self.get_memory_footprint(),)
    → "memory_footprint": self.get_memory_footprint(),
    """
    content = content.replace(
        'logger.info(y_footprint": self.get_memory_footprint(),)',
        '"memory_footprint": self.get_memory_footprint(),'
    )
    return content

def fix_dict_brace_in_call(content):
    """修复 .send({) → .send({"""
    content = content.replace('.send({)', '.send({')
    content = content.replace('.append({)', '.append({')
    return content

def fix_sentiment_strip(content):
    """修复 word.strip(\".,!?;:\"\\'()[]{}\") 引号问题"""
    # 这个实际上语法是对的，问题可能在其他地方
    return content

def fix_timezone_double(content):
    """修复 from datetime import ..., timezone, timezone.utc"""
    content = re.sub(r',\s*timezone\.utc', '', content)
    content = re.sub(r'timezone\.utc,\s*timezone', 'timezone', content)
    return content

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    content = fix_split_extra_paren(content)
    content = fix_fstring_crossline_v2(content)
    content = fix_crossline_regex_v2(content)
    content = fix_logger_info_broken(content)
    content = fix_dict_brace_in_call(content)
    content = fix_timezone_double(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return try_parse(filepath)

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
