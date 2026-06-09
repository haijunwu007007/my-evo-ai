"""全量语法验证"""
import os, ast

api_dir = r'D:\AUTO-EVO-AI-V0.1\api'
errors = []
total = 0
for root, dirs, fnames in os.walk(api_dir):
    for f in sorted(fnames):
        if not f.endswith('.py'):
            continue
        total += 1
        fp = os.path.join(root, f)
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read())
        except SyntaxError as e:
            errors.append(f'{os.path.relpath(fp, api_dir)}: {e}')

if errors:
    print(f'❌ {len(errors)} SYNTAX ERRORS:')
    for e in errors:
        print(f'  {e}')
else:
    print(f'✅ api/ 全部 {total} 个.py文件语法通过！')

# Check {{}} - only flag if outside f-strings
dbraces = []
for f in os.listdir(os.path.join(api_dir, 'agents')):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(api_dir, 'agents', f)
    c = open(fp, 'r', encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if ('{{' in stripped or '}}' in stripped) and 'f"' not in stripped and "f'" not in stripped:
            dbraces.append(f'{f}:{i+1}')
            break

if dbraces:
    print(f'{{}} found in: {dbraces}')
else:
    print('✅ 无{{}}问题')
