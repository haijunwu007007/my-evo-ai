#!/usr/bin/env python3
"""审计 modules/ 目录中 < 2KB 的桩模块"""
import os, json
from pathlib import Path

mods = sorted(Path('modules').glob('*.py'))
stubs = [m for m in mods if m.stat().st_size < 2048 and not m.name.startswith('_')]

print(f'Total modules: {len(mods)}')
print(f'Stub modules (< 2KB): {len(stubs)}')
print()

# Categorize stubs
categories = {}
for s in stubs:
    prefix = s.stem.split('_')[0] if '_' in s.stem else s.stem
    categories.setdefault(prefix, []).append(s.stem)

print('=== Categories ===')
for cat, names in sorted(categories.items(), key=lambda x: -len(x[1])):
    shown = ' '.join(names[:5])
    print(f'  {cat}_ ({len(names)}): {shown}{"..." if len(names) > 5 else ""}')

print()
print('=== Full stub list ===')
result = []
for s in stubs:
    with open(s, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    has_module_class = 'module_class' in content
    has_execute = 'def execute' in content
    has_class = 'class ' in content
    has_enterprise = 'EnterpriseModule' in content
    real_score = 0
    if has_module_class: real_score += 2
    if has_execute: real_score += 2
    if has_enterprise: real_score += 2
    if len(content.strip()) > 500: real_score += 1
    if has_class: real_score += 1
    result.append({
        'name': s.stem, 'bytes': s.stat().st_size, 'lines': len(content.strip().split('\n')),
        'has_module_class': has_module_class, 'has_execute': has_execute,
        'has_enterprise': has_enterprise, 'real_score': real_score,
    })
    print(f'  {s.stem:35s} {s.stat().st_size:5d}B  mcl={int(has_module_class)} ex={int(has_execute)} ent={int(has_enterprise)} score={real_score}')

print()
bins_text = {4: 'Grade A(4/5)', 3: 'Grade B(3/5)', 2: 'Grade C(2/5)', 1: 'Grade D(1/5)', 0: 'Grade F(0/5)'}
for r in range(5):
    cnt = sum(1 for x in result if x['real_score'] == r)
    if cnt:
        print(f'  {bins_text[r]}: {cnt} stubs')

with open('modules/stubs_audit.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print()
print('Audit saved to modules/stubs_audit.json')
