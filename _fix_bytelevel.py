#!/usr/bin/env python3
"""字节级精确修复：匹配 .split("\r\n 然后下一行 ")\r\n"""
import os, ast

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

# 实际字节模式：.split("\r\n")\r\n  → .split("\\n")\r\n
# 也就是：.split(" + CRLF + ") + CRLF → .split("\\n") + CRLF
REPLACEMENTS = [
    (b'.split("\r\n")\r\n', b'.split("\\n")\r\n'),
    (b".split('\r\n')\r\n", b".split('\\n')\r\n"),
    (b'.join("\r\n")\r\n', b'.join("\\n")\r\n'),
    (b".join('\r\n')\r\n", b".join('\\n')\r\n"),
    (b'.count("\r\n")\r\n', b'.count("\\n")\r\n'),
    (b".count('\r\n')\r\n", b".count('\\n')\r\n"),
]

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

fixed_files = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith('.py'): continue
    fp = os.path.join(BASE, f)
    
    with open(fp, 'rb') as fh:
        raw = fh.read()
    
    changed = False
    for old, new in REPLACEMENTS:
        if old in raw:
            raw = raw.replace(old, new)
            changed = True
    
    if changed:
        with open(fp, 'wb') as fh:
            fh.write(raw)
        if verify(fp):
            fixed_files.append(f)
            print(f'  OK {f}')
        else:
            # Try to see what's still wrong
            try:
                ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
            except SyntaxError as e:
                print(f'  PARTIAL {f}: L{e.lineno} {str(e.msg)[:40]}')

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
errs = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'\n总{total}, 完全修复{len(fixed_files)}, 剩余{len(errs)}')
