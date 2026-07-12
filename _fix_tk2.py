lines = open('modules/token_budget.py', 'r', encoding='utf-8').readlines()
# L737: '    logger.info("Token Budget Module 测试完成!"))'
# 删除多余行
del lines[736]  # 删除重复行
del lines[736]  # L738变成L737，删除
open('modules/token_budget.py', 'w', encoding='utf-8').writelines(lines)

import ast
try:
    ast.parse(open('modules/token_budget.py', 'r', encoding='utf-8').read())
    print('OK')
except SyntaxError as e:
    print(f'L{e.lineno}: {e.msg}')
    lines2 = open('modules/token_budget.py', 'r', encoding='utf-8').readlines()
    for i in range(max(0, e.lineno-2), min(len(lines2), e.lineno+3)):
        print(f'  {i+1}: {repr(lines2[i].rstrip()[:100])}')
