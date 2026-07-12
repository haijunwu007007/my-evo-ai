#!/usr/bin/env python3
"""快速诊断所有文件错误行和上下文"""
import ast, os, sys

BASE = r'D:\AUTO-EVO-AI-V0.1\modules'

def analyze(fp):
    name = os.path.basename(fp)
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    try:
        ast.parse(src, filename=name)
        return None
    except SyntaxError as e:
        lines = src.split('\n')
        return (name, e.lineno, e.msg[:80], lines)

errs = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith('.py'): continue
    fp = os.path.join(BASE, f)
    r = analyze(fp)
    if r:
        errs.append(r)

print(f'共 {len(errs)} 个语法错误\n')
for name, ln, msg, lines in errs:
    print(f'== {name} == L{ln}: {msg}')
    for i in range(max(0,ln-2), min(len(lines), ln+3)):
        marker = '>>>' if i+1 == ln else '   '
        print(f'{marker} {i+1}:{lines[i][:120]}')
    print()
