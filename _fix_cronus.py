lines = open('modules/agent_cronus.py', 'r', encoding='utf-8').readlines()
# Fix L189 (0-indexed 188): add 8 spaces indent for docstring
lines[188] = '        """验证字段格式"""\n'
open('modules/agent_cronus.py', 'w', encoding='utf-8').writelines(lines)

import ast
try:
    ast.parse(''.join(lines))
    print('FIXED!')
except SyntaxError as e:
    print(f'Still: L{e.lineno} {str(e.msg)[:50]}')
