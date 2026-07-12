import ast, re
fp = 'modules/atom_code.py'

for rnd in range(100):
    d = open(fp, 'rb').read()
    o = d
    
    # Match .split("X\r\nX") where X is a single char
    # Pattern: .split( followed by any quote char, then any char, CRLF, same char, same quote, )
    # .split("  '  \r\n  '  ")
    # .split("  \r\n  ")
    d = re.sub(rb'(\.split\()(["\'])(.)\r\n\3(\2\))', rb'\1\2\\n\4', d)
    d = re.sub(rb'(\.join\()(["\'])(.)\r\n\3(\2\))', rb'\1\2\\n\4', d)
    d = re.sub(rb'(\.count\()(["\'])(.)\r\n\3(\2\))', rb'\1\2\\n\4', d)
    # Also handle empty: .split("\r\n")
    d = re.sub(rb'(\.split\()(["\'])\r\n\2(\))', rb'\1\2\\n\3', d)
    d = re.sub(rb'(\.join\()(["\'])\r\n\2(\))', rb'\1\2\\n\3', d)
    d = re.sub(rb'(\.count\()(["\'])\r\n\2(\))', rb'\1\2\\n\3', d)
    
    if d == o:
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read())
            print(f'FIXED after {rnd} rounds!')
            break
        except SyntaxError as e:
            print(f'Round {rnd}: L{e.lineno} {str(e.msg)[:50]}')
            break
    
    open(fp, 'wb').write(d)
