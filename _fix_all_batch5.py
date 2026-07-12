#!/usr/bin/env python3
"""
修复61个语法错误文件的全部已知模式。
策略：直接对每个文件的已知错误行应用replace逻辑，不猜测。
"""
import ast, os, sys, re

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

def fix_file(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    original = text
    
    # === 模式1: re.split(r"[。！？   跨行 → 合并 ===
    text = re.sub(r're\.split\(r"\[\。\！\？\n\s*([^"]*?)"\)', r're.split(r"[。！？\1")', text)
    text = re.sub(r're\.split\(r"\[\。\！\？\n([^"]*?)"\)', r're.split(r"[。！？\1")', text)
    
    # === 模式2: split("跨行") → split("\\n") ===
    text = re.sub(r'\.split\("\n\s*"\s*\)', r'.split("\\n")', text)
    text = re.sub(r'\.split\(\'\n\s*\'\)', r".split('\\n')", text)
    text = re.sub(r'\.join\("\n\s*"\s*\)', r'.join("\\n")', text)
    
    # === 模式3: "内容跨行" 合并 ===
    text = re.sub(r'"\n([^"]*?)"', r'"\1"', text)
    
    # === 模式4: .count("跨行") → .count("\\n") ===  
    text = re.sub(r'\.count\("\n\s*"\s*\)', r'.count("\\n")', text)
    
    # === 模式5: r"内容" 跨行 → r"内容" 合并 ===
    text = re.sub(r'r"([^"]*?)\n\s*([^"]*?)"', r'r"\1\2"', text)
    
    # === 模式6: 去掉logger.info(y_footprint → "memory_footprint ===
    text = text.replace('logger.info(y_footprint": self.get_memory_footprint(),)',
                         '"memory_footprint": self.get_memory_footprint(),')
    
    # === 模式7: 去掉多余的 ) 在行首 ===
    lines = text.split('\n')
    changed = True
    while changed:
        changed = False
        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            stripped = line.strip()
            if stripped in (')', '])', '})') and i > 0:
                prev = lines[i-1].rstrip()
                # 检查上一行括号是否已经平衡
                opens = prev.count('(') + prev.count('[') + prev.count('{')
                closes = prev.count(')') + prev.count(']') + prev.count('}')
                if opens <= closes and opens > 0:
                    skip_next = True
                    changed = True
                    continue
            new_lines.append(line)
        lines = new_lines
    
    text = '\n'.join(lines)
    
    if text != original:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    return False

# 主流程
err_files = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith('.py'): continue
    fp = os.path.join(BASE, f)
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read(), filename=fp)
    except SyntaxError:
        err_files.append(f)

print(f'待修复: {len(err_files)}')

fixed = 0
for f in err_files:
    fp = os.path.join(BASE, f)
    orig_err = None
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read(), filename=fp)
    except SyntaxError as e:
        orig_err = e
    
    if fix_file(fp):
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read(), filename=fp)
            fixed += 1
            print(f'  ✅ {f}')
        except SyntaxError as e:
            print(f'  🔄 {f:<40} L{orig_err.lineno:<5} → L{e.lineno:<5} {str(e.msg)[:40]}')
    else:
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read(), filename=fp)
            # unchanged but now OK? unlikely
        except SyntaxError as e:
            print(f'  ❌ {f:<40} L{e.lineno:<5} {str(e.msg)[:40]}')

# 最终统计
final_errors = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not (lambda fp: (lambda: ast.parse(open(fp,'r',encoding='utf-8').read(),filename=fp))() if True else True)(os.path.join(BASE,f)) ]
# simpler:
final_errs = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith('.py'): continue
    fp = os.path.join(BASE, f)
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read(), filename=fp)
    except SyntaxError:
        final_errs.append(f)

print(f'\n修复: {fixed}, 剩余: {len(final_errs)}')
for f in final_errs[:20]:
    fp = os.path.join(BASE, f)
    with open(fp, 'r', encoding='utf-8') as fh:
        try:
            ast.parse(fh.read(), filename=fp)
        except SyntaxError as e:
            print(f'  {f:<45} L{e.lineno:<5} {str(e.msg)[:50]}')
if len(final_errs) > 20: print(f'  ... 还有 {len(final_errs)-20} 个')
