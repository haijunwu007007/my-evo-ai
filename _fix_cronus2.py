import re
lines = open('modules/agent_cronus.py', 'r', encoding='utf-8').readlines()

# L198: }        for token in value.split(\n",")
# Fix: split after } and merge .split(\n",")
old198 = lines[197]
# }        for → }\n        for
new198 = re.sub(r'}\s{8}for', r'}\n        for', old198)
# .split(\n",") → .split(",") [merge cross-line]
new198 = new198.replace('.split(\n",")', '.split(",")')
lines[197] = new198

# Also fix the next line if .split was there
if ',",")' in lines[198]:
    # delete line 199 (now 198 after fix, which has leftover ")
    pass

open('modules/agent_cronus.py', 'w', encoding='utf-8').writelines(lines)

import ast
try:
    ast.parse(''.join(lines))
    print('FIXED!')
except SyntaxError as e:
    print(f'Still: L{e.lineno} {str(e.msg)[:50]}')
    for i in range(max(0,e.lineno-2), min(len(lines),e.lineno+2)):
        print(f'  {i+1}: {lines[i].rstrip()}')
