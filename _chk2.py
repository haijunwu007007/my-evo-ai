#!/usr/bin/env python3
"""诊断文件语法错误"""
import ast, sys

fp = sys.argv[1]
with open(fp, 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src, filename=fp)
    print('OK')
except SyntaxError as e:
    lines = src.split('\n')
    ln = e.lineno
    print(f'L{ln}: {e.msg[:80]}')
    for i in range(max(0,ln-2), min(len(lines), ln+3)):
        marker = '>>>' if i+1 == ln else '   '
        print(f'{marker} {i+1}:{lines[i][:120]}')
