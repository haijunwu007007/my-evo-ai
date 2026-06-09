"""Fix remaining route-to-route imports in api/routes/"""
import os

ROUTES = r"D:\AUTO-EVO-AI-V0.1\api\routes"
API = r"D:\AUTO-EVO-AI-V0.1\api"
total = 0

# Fix route-to-route imports in routes/ files
for f in os.listdir(ROUTES):
    if not f.endswith('.py') or f == '__init__.py':
        continue
    fp = os.path.join(ROUTES, f)
    with open(fp, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content
    
    mod = f.replace('.py', '')
    # Replace from api.routes_XXX → from api.routes.routes_XXX
    # Need to be careful not to replace the current file's own import
    for f2 in os.listdir(ROUTES):
        if f2 == f or f2 == '__init__.py':
            continue
        mod2 = f2.replace('.py', '')
        old = f"from api.{mod2}"
        new = f"from api.routes.{mod2}"
        if old in content:
            content = content.replace(old, new)
    
    # Also fix route imports in api_server.py (might have been partially updated)
    if content != original:
        with open(fp, 'w', encoding='utf-8') as fh:
            fh.write(content)
        total += 1
        print(f"  Fixed: {f}")

# Also re-check api_server.py
as_path = r"D:\AUTO-EVO-AI-V0.1\api_server.py"
with open(as_path, 'r', encoding='utf-8') as fh:
    content = fh.read()
original = content
for f2 in os.listdir(ROUTES):
    if f2 == '__init__.py':
        continue
    mod2 = f2.replace('.py', '')
    old = f"from api.{mod2}"
    new = f"from api.routes.{mod2}"
    if old in content:
        content = content.replace(old, new)
if content != original:
    with open(as_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    total += 1
    print(f"  Fixed: api_server.py")

# Fix routes_xxx → routes.routes_xxx in api/agents/ (some agents might import routes)
for f in os.listdir(os.path.join(API, 'agents')):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(API, 'agents', f)
    with open(fp, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content
    for f2 in os.listdir(ROUTES):
        if f2 == '__init__.py':
            continue
        mod2 = f2.replace('.py', '')
        old = f"from api.{mod2}"
        new = f"from api.routes.{mod2}"
        if old in content:
            content = content.replace(old, new)
    if content != original:
        with open(fp, 'w', encoding='utf-8') as fh:
            fh.write(content)
        total += 1
        print(f"  Fixed: agents/{f}")

print(f"\nTotal files updated: {total}")
print("=== DONE ===")
