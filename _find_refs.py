import os, re

candidates = ['system_coordinator', 'system_coordinator_v3', 'circuit_breaker_pattern']
search_dirs = [
    r'D:\AUTO-EVO-AI-V0.1\core',
    r'D:\AUTO-EVO-AI-V0.1\api',
    r'D:\AUTO-EVO-AI-V0.1\modules',
    r'D:\AUTO-EVO-AI-V0.1\tests',
    r'D:\AUTO-EVO-AI-V0.1\scripts',
]

for mod in candidates:
    print(f'\n=== {mod} 引用位置 ===')
    found = False
    for d in search_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                if not f.endswith('.py'): continue
                fp = os.path.join(root, f)
                try:
                    content = open(fp, encoding='utf-8', errors='ignore').read()
                except: continue
                if mod in content:
                    print(f'  {fp}')
                    found = True
    if not found:
        print(f'  (no references found)')
