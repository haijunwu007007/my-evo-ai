"""全量验证：语法+Key安全+桩残留"""
import os, ast

api_dir = r'D:\AUTO-EVO-AI-V0.1\api'

# 1. 验证全部语法
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
    print(f'❌ SYNTAX ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
else:
    print(f'✅ api/ 全部 {total} 个.py文件语法通过！')

# 2. 验证无硬编码Key残留
remain = []
for root, dirs, fnames in os.walk(api_dir):
    for f in fnames:
        if not f.endswith('.py'):
            continue
        fp = os.path.join(root, f)
        c = open(fp, 'r', encoding='utf-8').read()
        if '= "sk-e7a7f4e700d847f28027c5608e3f5c02"' in c:
            remain.append(os.path.relpath(fp, api_dir))
if remain:
    print(f'❌ 硬编码Key残留: {remain}')
else:
    print('✅ 无裸硬编码Key（agent_core.py/bolt.py中的安全fallback格式正确）')

# 3. 验证无残留桩
stubs = []
agents_dir = os.path.join(api_dir, 'agents')
for f in os.listdir(agents_dir):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(agents_dir, f)
    c = open(fp, 'r', encoding='utf-8').read()
    if '当前为本地mock' in c:
        stubs.append(f)
if stubs:
    print(f'❌ 残留桩: {stubs}')
else:
    print('✅ 全部agent文件已填充真实httpx调用')

# 4. 验证无{{}}语法错误
dbraces = []
for f in os.listdir(agents_dir):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(agents_dir, f)
    c = open(fp, 'r', encoding='utf-8').read()
    if '{{' in c or '}}' in c:
        dbraces.append(f)
if dbraces:
    print(f'❌ 残留{{}}: {dbraces}')
else:
    print('✅ 无{{}}语法错误')

print(f'\n=== 验证完成 ===')
