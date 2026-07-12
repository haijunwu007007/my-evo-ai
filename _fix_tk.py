import sys
lines = open('modules/token_budget.py', 'r', encoding='utf-8').readlines()
# L733-L739 修复
lines[732] = '    logger.info("\\n📄 Markdown报告:")\n'
lines[733] = '    logger.info(manager.to_markdown())\n'
# 删掉多余的行
del lines[734]
lines[734] = '    logger.info("\\n" + "=" * 60)\n'
del lines[735]
lines[735] = '    logger.info("Token Budget Module 测试完成!")\n'
# 如果还有多余行则删除
while len(lines) > 736 and lines[736].strip() == '':
    del lines[736]
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
