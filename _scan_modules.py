"""Scan module directory: classify stubs vs real modules, move stubs to _archive"""
import os, json

modules_dir = 'D:\\AUTO-EVO-AI-V0.1\\modules'
archive_dir = os.path.join(modules_dir, '_archive_stub')
os.makedirs(archive_dir, exist_ok=True)

# Special: keep gitea_issue_sync (has httpx real call)
keep_override = {'gitea_issue_sync.py'}

stubs = []
reals = []
for f in sorted(os.listdir(modules_dir)):
    if not f.endswith('.py'):
        continue
    fpath = os.path.join(modules_dir, f)
    if os.path.isdir(fpath):
        continue
    size = os.path.getsize(fpath)
    with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    
    # Stub criteria: <5KB, no real imports, empty returns
    has_real_import = any(x in content for x in ['httpx.', 'requests.', 'sqlalchemy', 'pandas.', 'redis.', 'boto3', 'minio.', 'fastapi', 'websocket', 'asyncio.', 'paramiko', 'docker.', 'kubernetes', 'openai', 'zhipuai', 'subprocess.', 'numpy.'])
    has_real_logic = any(x in content for x in ['def ', 'class ', 'async def', 'import ']) or has_real_import
    
    if f in keep_override:
        reals.append((f, size, 'KEEP_OVERRIDE'))
        continue
    
    is_stub = False
    if size < 5120 and not has_real_import:
        # Check if it has actual return logic
        code_lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#') and not l.strip().startswith(('"""', "'''", '@'))]
        real_ops = sum(1 for l in code_lines if any(x in l for x in ['return ', 'print(', 'open(', '.write', '.read', 'await ', '.get(', '.post(', '.put(', '.delete(']))
        if real_ops < 3:
            is_stub = True
    
    if is_stub:
        stubs.append((f, size))
    else:
        reals.append((f, size, ''))

# Move stubs
archived = 0
for f, size in stubs:
    src = os.path.join(modules_dir, f)
    dst = os.path.join(archive_dir, f)
    if not os.path.exists(dst):
        os.rename(src, dst)
        archived += 1

print(f'=== MODULE SCAN REPORT ===')
print(f'Total .py files: {len(stubs) + len(reals)}')
print(f'Stubs moved to _archive_stub/: {archived} (of {len(stubs)} identified)')
print(f'Retained: {len(reals)}')
print()
print('Moved stubs:')
for f, size in stubs:
    print(f'  {f:45s} {size:>6}B')
print()
print('Retained:')
for r in reals:
    extra = f' [{r[2]}]' if r[2] else ''
    print(f'  {r[0]:45s} {r[1]:>6}B{extra}')
