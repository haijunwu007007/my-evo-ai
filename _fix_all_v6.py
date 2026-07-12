#!/usr/bin/env python3
"""
v6: 正确修复跨行引号
核心策略：行尾的孤立 " 和下一行开头的 " → 合并为 "\\n"
但不移动任何代码行，只替换引号字符
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

def fix_crossline_string_pairs(content):
    """
    核心修复：行尾 " + 空行 + " → 行尾 "\\n" (同一行)
    
    例如：
    L40: text.split('
    L41: ') → text.split('\\n')
    
    L84: return "
    L85: 
    L86: ".join(lines) → return "\\n
    L85: (空行删除)
    L86: ".join(lines) → "\\n".join(lines)
    
    策略：找到行尾的孤立引号，如果下一非空行以相同引号开头，
    把它们合并为 \\n 引号（在同一行），不删除其他行
    """
    lines = content.split('\n')
    changes = []
    
    for i in range(len(lines) - 1):
        line = lines[i]
        rline = line.rstrip()
        
        # 跳过注释/三引号/续行
        if rline.lstrip().startswith('#') or rline.endswith('\\') or rline.endswith('"""') or rline.endswith("'''"):
            continue
        
        # 检测双引号不平衡
        dq = rline.count('"') - rline.count('\\"')
        sq = rline.count("'") - rline.count("\\'")
        
        # 双引号未闭合
        if rline.endswith('"') and dq % 2 == 1:
            # 找下一非空行
            for j in range(i+1, min(i+5, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if next_stripped.startswith('"'):
                    # 替换当前行尾 " 为 \\n"
                    lines[i] = rline[:-1] + '\\n"'
                    # 替换下一非空行开头的 " 为空
                    lines[j] = lines[j].lstrip()
                    if lines[j].startswith('"'):
                        lines[j] = lines[j][1:]
                    # 保留缩进
                    lines[j] = lines[j]  # 已经去掉缩进了，保持
                    changes.append(f'L{i+1}+L{j+1} dq merge')
                    break
                else:
                    break  # 下一行不是引号开头，不是这种模式
        
        # 单引号未闭合
        if rline.endswith("'") and sq % 2 == 1:
            for j in range(i+1, min(i+5, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if next_stripped.startswith("'"):
                    lines[i] = rline[:-1] + "\\n'"
                    lines[j] = lines[j].lstrip()
                    if lines[j].startswith("'"):
                        lines[j] = lines[j][1:]
                    changes.append(f'L{i+1}+L{j+1} sq merge')
                    break
                else:
                    break
    
    return '\n'.join(lines)

def fix_crossline_fstring(content):
    """
    修复跨行 f-string:
    f"...{var}
    more text")
    → f"...{var}\\nmore text")
    
    策略：f-string 引号未闭合时，把后续行合并进来
    """
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        if rline.lstrip().startswith('#') or rline.endswith('\\'):
            i += 1
            continue
        
        # 检测 f-string
        has_f = bool(re.search(r'f["\']', rline))
        dq = rline.count('"') - rline.count('\\"')
        sq = rline.count("'") - rline.count("\\'")
        
        if has_f and ((rline.endswith('"') and dq % 2 == 1) or (rline.endswith("'") and sq % 2 == 1)):
            # f-string 未闭合
            # 合并后续行直到找到闭合引号
            merged = rline
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    j += 1
                    continue
                merged += '\\n' + next_stripped
                # 检查是否闭合了
                new_dq = merged.count('"') - merged.count('\\"')
                new_sq = merged.count("'") - merged.count("\\'")
                if (rline.endswith('"') and new_dq % 2 == 0) or (rline.endswith("'") and new_sq % 2 == 0):
                    break
                j += 1
            
            if j > i:
                lines[i] = merged
                # 删除合并的行
                for k in range(i+1, j+1):
                    if k < len(lines):
                        lines[k] = None  # 标记删除
                lines = [l for l in lines if l is not None]
                # 不跳过，重新检查当前行
                continue
        i += 1
    
    return '\n'.join(lines)

def fix_backslash_replace(content):
    """修复 replace("\\", "/") 被截断"""
    # 行内有 replace("\", "/") 
    content = content.replace('replace("\\", "/")', 'replace("\\\\", "/")')
    content = content.replace("replace('\\','/')", "replace('\\\\','/')")
    return content

def fix_extra_close_paren(content):
    """修复 logger.info("xxx")) 多余括号"""
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

def fix_missing_close_paren(content):
    """修复缺少右括号"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.endswith('\\') or stripped.endswith(','):
            continue
        opens = line.count('(')
        closes = line.count(')')
        if opens > closes and not stripped.endswith('(') and not stripped.endswith('+'):
            lines[i] = line + ')' * (opens - closes)
        bo = line.count('[')
        bc = line.count(']')
        if bo > bc and not stripped.endswith('[') and not stripped.endswith('+'):
            lines[i] = lines[i] + ']' * (bo - bc)
    return '\n'.join(lines)

def fix_enc_paren(content):
    content = content.replace('"ENC(")', '"ENC("')
    return content

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    content = fix_crossline_string_pairs(content)
    content = fix_crossline_fstring(content)
    content = fix_backslash_replace(content)
    content = fix_extra_close_paren(content)
    content = fix_missing_close_paren(content)
    content = fix_enc_paren(content)
    
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
