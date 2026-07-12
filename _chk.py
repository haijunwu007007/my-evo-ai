#!/usr/bin/env python3
"""逐文件诊断语法错误"""
import ast, os, sys

BASE = r'D:\AUTO-EVO-AI-V0.1\modules'

def show_error(fname):
    fp = os.path.join(BASE, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    try:
        ast.parse(src, filename=fname)
        print(f'OK {fname}')
        return True
    except SyntaxError as e:
        lines = src.split('\n')
        ln = e.lineno
        print(f'== {fname} == L{ln}: {e.msg[:80]}')
        for i in range(max(0,ln-2), min(len(lines), ln+3)):
            marker = '>>>' if i+1 == ln else '   '
            print(f'{marker} {i+1}:{lines[i][:120]}')
        print()
        return False

if __name__ == '__main__':
    fname = sys.argv[1] if len(sys.argv) > 1 else 'web_fetcher.py'
    show_error(fname)
