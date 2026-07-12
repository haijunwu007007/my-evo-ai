import sys, ast
with open('modules/sql_generator.py', 'rb') as f:
    d = f.read()
# Find replace pattern and fix it
idx = d.find(b'replace(\"')
if idx >= 0:
    # The bytes are: replace("\r\n", " ")
    # Need to find the exact length of this pattern
    # look for the closing )
    end_idx = d.find(b')', idx)
    old_seg = d[idx:end_idx+1]
    print('Old seg:', repr(old_seg))
    # New: replace("\\n", " ")
    new_seg = b'replace("\\n", " ")'
    d = d[:idx] + new_seg + d[end_idx+1:]
    with open('modules/sql_generator.py', 'wb') as f:
        f.write(d)
    print('Written!')
try:
    ast.parse(d.decode('utf-8'))
    print('AST OK!')
except SyntaxError as e:
    print(f'L{e.lineno}: {e.msg[:60]}')
