#!/usr/bin/env python3
"""
修复61个语法错误文件 - 多轮迭代版
"""
import ast, os, sys, re

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

def fix_file(fp):
    with open(fp, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-8')
    except:
        text = raw.decode('gbk', errors='replace')
    original = text
    
    for _round in range(30):
        old = text
        
        # 模式1: re.split(r"[跨行 → 合并
        text = re.sub(r'(re\.split\(r"\[[\u4e00-\u9fff]+\?)\s*\n\s*([^"]*?)"\)', r'\1\2")', text)
        
        # 模式2: .split("\n跨行 → .split("\\n")
        text = re.sub(r'\.split\("\s*\n\s*"\s*\)', r'.split("\\n")', text)
        text = re.sub(r"\.split\('\s*\n\s*'\s*\)", r".split('\\n')", text)
        
        # 模式3: .join("\n跨行 → .join("\\n")
        text = re.sub(r'\.join\("\s*\n\s*"\s*\)', r'.join("\\n")', text)
        text = re.sub(r"\.join\('\s*\n\s*'\s*\)", r".join('\\n')", text)
        
        # 模式4: 行尾未闭合引号+下行引号开头 → 合并
        text = re.sub(r'([^\\])"\s*\n\s*"([^)])', r'\1"\\n"\2', text)
        text = re.sub(r"([^\\])'\s*\n\s*'([^)])", r"\1'\\n'\2", text)
        
        # 模式5: .count("跨行 → .count("\\n")
        text = re.sub(r'\.count\("\s*\n\s*"\s*\)', r'.count("\\n")', text)
        
        # 模式6: 去掉多余的 ) 独立行
        lines = text.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped in (')', '])', '})', ')}', ']]') and i > 0:
                prev = lines[i-1].rstrip()
                opens = prev.count('(') + prev.count('[') + prev.count('{')
                closes = prev.count(')') + prev.count(']') + prev.count('}')
                if opens <= closes:
                    i += 1
                    continue
            new_lines.append(lines[i])
            i += 1
        text = '\n'.join(new_lines)
        
        # 模式7: "xxx" "xxx" 之间多余的换行
        text = re.sub(r'([\'"])\s*\n\s*\1', r'\1', text)
        
        # 模式8: logger.info(y_footprint"
        text = text.replace('logger.info(y_footprint": self.get_memory_footprint(),)',
                             '"memory_footprint": self.get_memory_footprint(),')
        
        if text == old:
            break
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    return text != original

# 主流程
for round_num in range(20):
    err_files = []
    for f in sorted(os.listdir(BASE)):
        if not f.endswith('.py'): continue
        fp = os.path.join(BASE, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read(), filename=fp)
        except SyntaxError:
            err_files.append(f)
    
    if not err_files:
        print(f'第{round_num+1}轮: 全部通过!')
        break
    
    fixed = 0
    for f in err_files:
        fp = os.path.join(BASE, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read(), filename=fp)
        except SyntaxError:
            if fix_file(fp):
                fixed += 1
    
    print(f'第{round_num+1}轮: 修复{fixed}, 剩余{len(err_files)-fixed}')
    if fixed == 0:
        break

# 最终统计
final_errs = []
for f in sorted(os.listdir(BASE)):
    if not f.endswith('.py'): continue
    fp = os.path.join(BASE, f)
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read(), filename=fp)
    except SyntaxError:
        final_errs.append(f)

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
print(f'\n=== 最终: 总{total}, 正确{total - len(final_errs)}, 剩余{len(final_errs)} ===')
for f in final_errs:
    fp = os.path.join(BASE, f)
    with open(fp, 'r', encoding='utf-8') as fh:
        try:
            ast.parse(fh.read(), filename=fp)
        except SyntaxError as e:
            print(f'  {f:<45} L{e.lineno:<5} {str(e.msg)[:60]}')
