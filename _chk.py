"""Syntax check all files"""
import os, ast

API = r'D:\AUTO-EVO-AI-V0.1\api'
errors = []
ok = 0

def check(fp, label):
    global ok
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read())
        ok += 1
    except SyntaxError as e:
        errors.append(f'{label}: line {e.lineno}: {e.msg}')

for f in os.listdir(API):
    if f.endswith('.py'):
        check(os.path.join(API, f), f'api/{f}')

for d in ['routes', 'agents']:
    dd = os.path.join(API, d)
    for f in os.listdir(dd):
        if f.endswith('.py'):
            check(os.path.join(dd, f), f'api/{d}/{f}')

if errors:
    print(f'SYNTAX ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
else:
    print(f'ALL {ok} FILES SYNTAX OK')
