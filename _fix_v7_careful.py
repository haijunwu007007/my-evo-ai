#!/usr/bin/env python3
""" 
保守修复脚本v7：只修复100%确定的跨行字符串模式，每步验证
"""
import ast, os, shutil, re

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'
BACKUP = 'D:/AUTO-EVO-AI-V0.1/.fix_bak_v7'

def verify(fp):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=fp)
        return True
    except:
        return False

def fix_one_file(fp):
    """尝试修复一个文件，成功返回True，失败保持原样返回False"""
    if verify(fp):
        return True
    
    # 备份
    os.makedirs(BACKUP, exist_ok=True)
    shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp)))
    
    with open(fp, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8')
    original = text
    
    for _round in range(50):
        old = text
        
        # === 修复模式1: .split("\n")\n") → .split("\\n") ===
        # 匹配: .split("
        #        ")
        text = re.sub(r'\.split\("\s*\n\s*"\s*\)', r'.split("\\n")', text)
        text = re.sub(r"\.split\('\s*\n\s*'\s*\)", r".split('\\n')", text)
        
        # === 修复模式2: .join("\n")\n") → .join("\\n") ===
        text = re.sub(r'\.join\("\s*\n\s*"\s*\)', r'.join("\\n")', text)
        text = re.sub(r"\.join\('\s*\n\s*'\s*\)", r".join('\\n')", text)
        
        # === 修复模式3: .count("\n")\n") → .count("\\n") ===
        text = re.sub(r'\.count\("\s*\n\s*"\s*\)', r'.count("\\n")', text)
        
        # === 修复模式4: 行尾未闭合" + 下一行"开头 ===
        # 如: "abc\ndef" → "abc\\ndef"
        # 关键：仅当合并后括号平衡
        text = re.sub(r'(?<=[^\\])"\s*\n\s*"', r'"\\n"', text)
        
        # === 修复模式5: r"跨行 → 合并内容 ===
        text = re.sub(r'(r"[\u4e00-\u9fff？。！，]+)\s*\n\s*([^"]*?)"', r'\1\2"', text)
        
        # === 修复模式6: ) 单独一行且上一行括号已平衡 ===
        lines = text.split('\n')
        new_lines = []
        skip = False
        for i, line in enumerate(lines):
            if skip:
                skip = False
                continue
            stripped = line.strip()
            if stripped in (')', '])', '})', ')]', '}', ']') and i > 0:
                prev = lines[i-1].rstrip()
                opens = prev.count('(') + prev.count('[') + prev.count('{')
                closes = prev.count(')') + prev.count(']') + prev.count('}')
                if opens <= closes:
                    skip = True
                    continue
            new_lines.append(line)
        text = '\n'.join(new_lines)
        
        if text == old:
            break
    
    # 写回文件
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    
    if verify(fp):
        # 清理备份
        bak = os.path.join(BACKUP, os.path.basename(fp))
        if os.path.exists(bak):
            os.remove(bak)
        return True
    
    # 回滚
    shutil.copy2(os.path.join(BACKUP, os.path.basename(fp)), fp)
    return False

# 主流程
print('Round 1: 逐文件修复...')
errs = [(f, os.path.join(BASE, f)) for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'初始: {len(errs)}')

for fname, fp in errs:
    if fix_one_file(fp):
        print(f'  OK {fname}')
    else:
        print(f'  XX {fname}')

final = [(f, os.path.join(BASE, f)) for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
print(f'\n总{total}, 正确{total-len(final)}, 剩余{len(final)}')
for f, fp in final[:20]:
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
    except SyntaxError as e:
        lines = open(fp,'r',encoding='utf-8').readlines()
        ln = e.lineno
        print(f'  {f:<45} L{ln:<5} {str(e.msg)[:50]}')
        # 显示上下文
        for i in range(max(0,ln-1), min(len(lines),ln+2)):
            print(f'    {i+1}: {lines[i].rstrip()}')
if len(final) > 20:
    print(f'  ... 还有{len(final)-20}个')
