#!/usr/bin/env python3
"""修复v12：只修最确定的模式"""
import ast, os, re

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

def fix_simple(text):
    o = text
    # 1: .split / .join / .count 跨行
    text = re.sub(r'\.split\("\s*\n\s*"\)', r'.split("\\n")', text)
    text = re.sub(r"\.split\('\s*\n\s*'\)", r".split('\\n')", text)
    text = re.sub(r'\.join\("\s*\n\s*"\)', r'.join("\\n")', text)
    text = re.sub(r"\.join\('\s*\n\s*'\)", r".join('\\n')", text)
    text = re.sub(r'\.count\("\s*\n\s*"\)', r'.count("\\n")', text)
    
    # 2: r"中文"跨行
    text = re.sub(r'(re\.split\("?r"\[[\u4e00-\u9fff？。！，]+)\s*\n\s*([^"]*"\))', r'\1\2', text)
    
    # 3: 去掉多余)行
    lines = text.split('\n')
    nl = []
    skip = set()
    for i, line in enumerate(lines):
        if i in skip: continue
        s = line.strip()
        if s in (')', '])', '})', ']}') and i > 0:
            pr = lines[i-1].rstrip()
            if pr.count('(')+pr.count('[')+pr.count('{') <= pr.count(')')+pr.count(']')+pr.count('}'):
                continue
        nl.append(line)
    text = '\n'.join(nl)
    
    # 4: timezone
    text = text.replace('timezone, timezone.utc', 'timezone')
    
    # 5: logger.info typo
    text = text.replace('logger.info(y_footprint"', '"memory_footprint"')
    
    return text

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

err_before = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'修复前: {len(err_before)}')

for rnd in range(10):
    fc = 0
    for f in sorted(os.listdir(BASE)):
        if not f.endswith('.py'): continue
        fp = os.path.join(BASE, f)
        if verify(fp): continue
        with open(fp, 'r', encoding='utf-8') as fh:
            t = fh.read()
        nt = fix_simple(t)
        if nt != t:
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.write(nt)
            fc += 1
    if fc == 0: break
    print(f'第{rnd+1}轮: {fc}')

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
err = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'总{total}, 正确{total-len(err)}, 剩余{len(err)}')
for f in err[:20]:
    fp = os.path.join(BASE, f)
    try: ast.parse(open(fp,'r',encoding='utf-8').read())
    except SyntaxError as e:
        print(f'  L{e.lineno:<5} {str(e.msg)[:55]}  {f}')
