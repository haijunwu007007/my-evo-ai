"""Verify restructure: check all files syntax OK"""
import os, ast, sys

API = r'D:\AUTO-EVO-AI-V0.1\api'
errors = []
ok_count = 0

def check_dir(dirpath, label):
    global ok_count
    for f in os.listdir(dirpath):
        if not f.endswith('.py'):
            continue
        fp = os.path.join(dirpath, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read())
            ok_count += 1
        except SyntaxError as e:
            errors.append(f'{label}/{f}: line {e.lineno}: {e.msg}')

check_dir(API, 'api')
check_dir(os.path.join(API, 'routes'), 'api/routes')
check_dir(os.path.join(API, 'agents'), 'api/agents')

print(f'Syntax check: {ok_count} OK')
if errors:
    print(f'ERRORS: {len(errors)}')
    for e in errors:
        print(f'  {e}')
    sys.exit(1)
else:
    print('ALL PASS')

# Now try import check on key files
print('\n--- Import check (api/infra.py) ---')
try:
    os.chdir(r'D:\AUTO-EVO-AI-V0.1')
    sys.path.insert(0, r'D:\AUTO-EVO-AI-V0.1')
    # Set dummy env to avoid import errors
    import api.infra
    print('  api.infra: OK')
except Exception as e:
    print(f'  api.infra: {type(e).__name__}: {str(e)[:120]}')
