#!/usr/bin/env python3
import ast, sys
files = ['api/routes/routes_hub.py','api/hub/models.py','api/hub/discover.py','api/hub/integrate.py','api/routes/hub_static.py']
ok = 0
for f in files:
    try:
        with open(f) as fh: content = fh.read()
        ast.parse(content)
        print(f'✓ {f}')
        ok += 1
    except SyntaxError as e:
        print(f'✗ {f}: {e}')
print(f'\n{ok}/{len(files)} 语法通过')
