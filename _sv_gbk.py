import os, sys, subprocess

BASE = r'D:\AUTO-EVO-AI-V0.1\tests'
ENC = 'utf-8'

broken = []
for root, dirs, files in os.walk(BASE):
    for f in files:
        if not f.endswith('.py'): continue
        fp = os.path.join(root, f)
        try:
            with open(fp, 'r', encoding=ENC) as fh:
                fh.read()
        except UnicodeDecodeError:
            broken.append(fp)
            with open(fp, 'r', encoding='gbk') as fh:
                content = fh.read()
            with open(fp, 'w', encoding=ENC) as fh:
                fh.write(content)
            print(f'FIXED: {os.path.relpath(fp, BASE)}')

if not broken:
    print('ALL OK')
else:
    print(f'\nFixed {len(broken)} files')
