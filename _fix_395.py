fp = 'modules/atom_code.py'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# 这4行跨行 re.sub
old = (
    '        new_code = re.sub(r"else:\\\\s*\n'
    '\\\\s*return True\n'
    'else:\\\\s*\n'
    '\\\\s*return False", "", new_code)'
)

new = (
    '        new_code = re.sub(r"else:\\\\s*\\\\n'
    '\\\\s*return True\\\\n'
    'else:\\\\s*\\\\n'
    '\\\\s*return False", "", new_code)'
)

if old in content:
    content = content.replace(old, new)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('REPLACED')
else:
    print('NOT FOUND')
    idx = content.find('new_code = re.sub')
    while idx >= 0:
        print(repr(content[idx:idx+120]))
        idx = content.find('new_code = re.sub', idx+1)

import ast
ast.parse(content)
print('OK')
