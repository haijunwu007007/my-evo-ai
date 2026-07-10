"""扫描Grade标签虚高模块"""
import os, glob, re, json
from collections import Counter

modules = glob.glob('modules/*.py')
results = []
suspects = []
for fp in sorted(modules):
    fname = os.path.basename(fp)
    with open(fp, encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.count('\n')
    size = len(content)
    # 查找 grade 字段: "grade": "A"
    grade = '?'
    for line in content.split('\n'):
        line = line.strip()
        if '"grade"' in line:
            m = re.search(r'"[ABCD]"', line)
            if m:
                grade = m.group(0)[1]
                break
    has_execute = 'def execute' in content or 'async def execute' in content
    has_class = 'class ' in content
    results.append((grade, size, lines, fname, has_execute, has_class))
    if grade in ('A','B') and (size < 1024 or lines < 30):
        suspects.append((grade, size, lines, fname))

logger.info(f"{'Grade':>5} {'Size':>6} {'Lines':>5} {'File':>40} {'exec':>5} {'cls':>5}"))
logger.info('-' * 75))
for g, s, l, f in suspects:
    row = next(r for r in results if r[3] == f)
    he, hc = row[4], row[5]
    logger.info(f'{g:>5} {s:>6} {l:>5} {f:>40} {str(he):>5} {str(hc):>5}'))

logger.info(f'\n总模块: {len(results)}'))
logger.info(f'Grade A/B 但 <1KB/30行的可疑模块: {len(suspects)}'))
logger.info('\nGrade 分布:'))
for g, c in sorted(Counter(r[0] for r in results).items()):
    logger.info(f'  Grade {g}: {c} 模块'))
