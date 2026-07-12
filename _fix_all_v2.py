#!/usr/bin/env python3
"""v2: 精准修复69个语法错误文件"""
import ast, os, re, sys

base = 'modules'

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def fix_file(filepath):
    """尝试修复单个文件，返回 (fixed, remaining_error)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    changed = False
    
    # 策略1: 跨行字符串合并
    # 模式: 行尾以 ' 或 " 结尾(不是三引号)，下一行以相同引号开头
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        next_stripped = lines[i+1].strip()
        
        # 跳过注释行
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        # 跳过三引号
        if rline.endswith('"""') or rline.endswith("'''"):
            i += 1
            continue
        # 跳过行尾反斜杠续行
        if rline.endswith('\\'):
            i += 1
            continue
            
        # 检测: 行尾 " 且下一行以 " 开头
        if rline.endswith('"') and next_stripped.startswith('"'):
            # 合并: 去掉行尾的"，加上 \n"，去掉下行开头的"
            merged = rline[:-1] + '\\n"' + next_stripped[1:]
            lines[i] = merged
            del lines[i+1]
            changed = True
            continue
            
        # 检测: 行尾 ' 且下一行以 ' 开头  
        if rline.endswith("'") and next_stripped.startswith("'"):
            merged = rline[:-1] + "\\n'" + next_stripped[1:]
            lines[i] = merged
            del lines[i+1]
            changed = True
            continue
        
        i += 1
    
    # 策略2: 修复 replace("\\", "/") 被截断为 replace("\", "/")
    # 模式: replace("\", "/") 应该是 replace("\\", "/")
    new_content = '\n'.join(lines)
    
    # 修复单反斜杠: replace("\", "/") → replace("\\", "/")
    pattern_bs = r'replace\("\\?",\s*"/"\)'
    if re.search(pattern_bs, new_content):
        new_content = re.sub(r'replace\("\",\s*"/"\)', 'replace("\\\\", "/")', new_content)
        changed = True
    
    # 策略3: 修复少右括号 list(xxx.iter_rows(values_only=True) → list(xxx.iter_rows(values_only=True))
    # 检测: = list( 结尾且同行没有匹配 )
    lines2 = new_content.split('\n')
    for j, line in enumerate(lines2):
        stripped = line.strip()
        if '= list(' in line:
            # 统计括号
            opens = line.count('(')
            closes = line.count(')')
            if opens > closes and not stripped.endswith(')'):
                lines2[j] = line + ')'
                changed = True
    new_content = '\n'.join(lines2)
    
    # 策略4: 修复 )) 多余右括号 logger.info("xxx"))
    lines3 = new_content.split('\n')
    for j, line in enumerate(lines3):
        if 'logger.info(' in line or 'logger.warning(' in line or 'logger.error(' in line:
            # 如果行以 )) 结尾（不是三重），去掉一个
            if line.rstrip().endswith('))') and not line.rstrip().endswith(')))'):
                lines3[j] = line.rstrip()[:-1]
                changed = True
    new_content = '\n'.join(lines3)
    
    # 策略5: 跨行 f-string 合并
    # 模式: f"...{xxx} 换行 ..." 
    lines4 = new_content.split('\n')
    i = 0
    while i < len(lines4) - 1:
        line = lines4[i]
        rline = line.rstrip()
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        # f-string 跨行: 行中有 f" 但没有闭合，下一行有 "
        if 'f"' in rline and rline.count('"') % 2 == 1:
            next_s = lines4[i+1].strip()
            if next_s.startswith('"') or next_s.startswith("'"):
                merged = rline + '\\n' + next_s
                lines4[i] = merged
                del lines4[i+1]
                changed = True
                continue
        i += 1
    new_content = '\n'.join(lines4)
    
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    err = try_parse(filepath)
    return changed, err

# 处理所有文件
files = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    err = try_parse(base + '/' + f)
    if err:
        files.append(f)

print(f'待修复: {len(files)} 个文件')

fixed = 0
still_broken = []

for f in files:
    fp = base + '/' + f
    changed, err = fix_file(fp)
    if err is None:
        fixed += 1
        print(f'  [OK] {f}')
    else:
        still_broken.append((f, err.lineno, str(err.msg)[:50]))
        if changed:
            print(f'  [PARTIAL] {f} -> {err.msg[:40]}')
        else:
            print(f'  [SKIP] {f} -> {err.msg[:40]}')

print(f'\n修复: {fixed}/{len(files)}')
print(f'剩余: {len(still_broken)}')
for f, ln, msg in still_broken[:10]:
    print(f'  {f:<45} L{ln:<5} {msg}')
