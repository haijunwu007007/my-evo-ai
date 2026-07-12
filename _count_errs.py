import ast, os
base = 'D:/AUTO-EVO-AI-V0.1/modules'
errs = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'): continue
    fp = os.path.join(base, f)
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
    except SyntaxError as e:
        errs.append((f, e.lineno, str(e.msg)[:60]))
total = len([x for x in os.listdir(base) if x.endswith('.py')])
print(f'总: {total}, 剩余: {len(errs)}')
for f, ln, msg in errs:
    print(f'  {ln:<6} {msg:<55} {f}')
