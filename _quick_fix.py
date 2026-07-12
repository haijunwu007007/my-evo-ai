import os, ast
base = 'D:/AUTO-EVO-AI-V0.1/modules'
crlf = b'\r\n'

# Only do the most reliable byte patterns
pat = [
    (b'.split("' + crlf + b'")' + crlf, b'.split("\\n")' + crlf),
    (b".split('" + crlf + b"')" + crlf, b".split('\\n')" + crlf),
    (b'.join("' + crlf + b'")' + crlf, b'.join("\\n")' + crlf),
    (b".join('" + crlf + b"')" + crlf, b".join('\\n')" + crlf),
    (b'timezone, timezone.utc', b'timezone'),
]

for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    fp = base + '/' + f
    with open(fp, 'rb') as fh:
        d = fh.read()
    o = d
    for old, new in pat:
        if old in d:
            d = d.replace(old, new)
    if d != o:
        with open(fp, 'wb') as fh:
            fh.write(d)

total = len([f for f in os.listdir(base) if f.endswith('.py')])
errs = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    fp = base + '/' + f
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
    except SyntaxError:
        errs.append(f)

print(f'总{total}, 剩余{len(errs)}')
for f in errs[:10]:
    fp = base + '/' + f
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
    except SyntaxError as e:
        print(f'  {f:<40} L{e.lineno:<5} {str(e.msg)[:50]}')
if len(errs) > 10:
    print(f'  ... 还有{len(errs)-10}个')
