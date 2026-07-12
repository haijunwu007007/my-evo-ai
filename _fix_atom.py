import sys
lines = open('modules/atom_code.py', 'r', encoding='utf-8').readlines()
# L292: '        lines = code.split("\\n)\n'
# 原始文件v9修复后变成了 split("\\n) 缺少闭合引号
# 修复: split("\n")
lines[291] = '        lines = code.split("\\n")\n'
open('modules/atom_code.py', 'w', encoding='utf-8').writelines(lines)
print('fixed L292')

import ast
try:
    ast.parse(open('modules/atom_code.py', 'r', encoding='utf-8').read())
    print('OK')
except SyntaxError as e:
    print(f'Still error: L{e.lineno} {e.msg[:60]}')
