import os, ast
base = 'D:/AUTO-EVO-AI-V0.1/modules'

bs = b'\x5c' + b'n'  # \\n = backslash(0x5c) + n(0x6e)

fixed = 0
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'): continue
    fp = base + '/' + f
    with open(fp, 'rb') as fh:
        d = fh.read()
    o = d
    
    # Replace patterns of repeated \n
    d = d.replace(bs + bs + bs, b'')
    d = d.replace(bs + bs, b'')
    d = d.replace(bs, b'')
    
    if d != o:
        with open(fp, 'wb') as fh:
            fh.write(d)
        fixed += 1

errs = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'): continue
    fp = base + '/' + f
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
    except SyntaxError:
        errs.append(f)

total = len([f for f in os.listdir(base) if f.endswith('.py')])
print(f'fixed {fixed}, total {total}, errors {len(errs)}')
for f in errs[:5]:
    fp = base + '/' + f
    try: ast.parse(open(fp, 'r', encoding='utf-8').read())
    except SyntaxError as e:
        print(f'  L{e.lineno:<5} {str(e.msg)[:50]}  {f}')
