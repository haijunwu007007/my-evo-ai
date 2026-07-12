#!/usr/bin/env python3
"""
精准修复 __module_meta__ 文档字符串的 `\\n` 换行符问题。

问题：模块文件顶部有以下结构：
\"\"\"\\n__module_meta__ = {\\n"id": ...
\"\"\"

Python 解析器看到的是：
1. 以 \"\"\" 开头的多行字符串
2. 第二行是 \\n__module_meta__ = {\\n  —— 这里 \\n 被当成字面反斜杠+n，不是换行
3. 但文件里实际是物理换行，所以 ast 报错

正确写法应该是把物理换行去掉，整个 __module_meta__ 放在一行：
\"\"\"\\n__module_meta__ = {\\n\"id\": ...\\n}\"\"\"

但问题：某些文件里 __module_meta__ 跨多行，中间有物理换行。
"""

import ast, os, re

def try_parse(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return e

def has_module_meta_error(filepath):
    """检查文件是否包含 __module_meta__ 的跨行问题"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if '__module_meta__' not in content:
        return False
    # 找到 __module_meta__ 所在行
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '__module_meta__' in line and '"""' not in line:
            # 检查后续行是否在三引号内且包含物理换行
            return True
    return False

def fix_module_meta(filepath):
    """
    修复 __module_meta__ 文档字符串。
    方案：找到 """\\n__module_meta__ = {...}""" 结构，
    将中间的所有物理换行替换为 \\n，合并为一行。
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 """\\n__module_meta__ = 模式
    pattern = re.compile(
        r'"""\\n__module_meta__\s*=\s*\{.*?\}"""',
        re.DOTALL
    )
    
    def replacer(match):
        meta = match.group(0)
        # 把内部的物理换行替换为 \\n
        # 但保留开头的 """ 和结尾的 """
        meta = meta.replace('\n', '\\n')
        return meta
    
    new_content = pattern.sub(replacer, content)
    
    if new_content == content:
        return False
    
    # 验证语法
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    err = try_parse(filepath)
    return err is None

# 找出所有有 __module_meta__ 问题的文件
base = 'modules'
files_with_meta = []
for f in sorted(os.listdir(base)):
    if not f.endswith('.py'):
        continue
    fp = base + '/' + f
    err = try_parse(fp)
    if err and '__module_meta__' in open(fp, 'r', encoding='utf-8').read():
        files_with_meta.append(f)

print(f'有 __module_meta__ 的文件: {len(files_with_meta)}')

fixed = 0
for f in files_with_meta[:10]:  # 先试10个
    fp = base + '/' + f
    if fix_module_meta(fp):
        fixed += 1
        print(f'  ✅ {f}')
    else:
        print(f'  ❌ {f} - 修复失败')

print(f'\n成功修复: {fixed}/{len(files_with_meta[:10])}')
