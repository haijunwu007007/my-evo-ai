import os, glob, re

modules_dir = 'modules'
all_files = sorted(glob.glob(os.path.join(modules_dir, '*.py')))
small = []
medium = []
large = []

for f in all_files:
    name = os.path.basename(f)
    if name.startswith('__'): continue
    sz = os.path.getsize(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        content = fh.read()
    lines = len(content.splitlines())
    ext_imports = [i for i in ['requests', 'httpx', 'aiohttp', 'bs4', 'selenium',
        'openai', 'zhipu', 'redis', 'pymongo', 'sqlalchemy', 'docker', 'boto3',
        'kafka', 'pika', 'elasticsearch', 'mysql', 'psycopg2', 'cryptography',
        'PIL', 'numpy', 'pandas', 'matplotlib'] if i in content]
    grade_a = "'grade': 'A'" in content or '"grade": "A"' in content
    
    if sz < 3000 and lines < 40:
        small.append((sz, name, lines, ext_imports, grade_a))
    elif sz < 8000:
        medium.append((sz, name, lines, ext_imports, grade_a))

print(f"总计模块: {len(all_files)}")
print(f"\n=== <3KB/40行小型模块: {len(small)} ===")
for sz, name, lines, imports, grade_a in sorted(small):
    imp = ', '.join(imports) if imports else '无'
    flag = ' ★虚标Grade A' if grade_a and not imports else ''
    print(f"  [{sz//1024}.{sz%1024:03d}KB/{lines}行] {name} | 导入: {imp}{flag}")

print(f"\n=== 3-8KB中等模块: {len(medium)} ===")
for sz, name, lines, imports, grade_a in sorted(medium):
    imp = ', '.join(imports) if imports else '无'
    flag = ' ★虚标Grade A' if grade_a and not imports else ''
    print(f"  [{sz//1024}.{sz%1024:03d}KB/{lines}行] {name} | 导入: {imp}{flag}")
