import ast
fp = 'modules/atom_code.py'
for rnd in range(100):
    d = open(fp, 'rb').read()
    o = d
    
    old_bytes = [b'.split("\r\n")\r\n', b'.join("\r\n")\r\n', b'.count("\r\n")\r\n']
    new_bytes = [b'.split("\\n")\r\n', b'.join("\\n")\r\n', b'.count("\\n")\r\n']
    
    for old, new in zip(old_bytes, new_bytes):
        d = d.replace(old, new)
    
    if d == o:
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read())
            print(f'FIXED after {rnd} rounds!')
            break
        except SyntaxError as e:
            print(f'Round {rnd}: remaining L{e.lineno} {str(e.msg)[:50]}')
            break
    
    open(fp, 'wb').write(d)
