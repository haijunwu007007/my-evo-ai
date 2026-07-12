#!/usr/bin/env python3
"""
修复所有跨行字符串模式，不破坏文档字符串。
只处理以下精确模式：
1. `split("` + 换行 + `")` → `split("\n")`
2. `".join` + 换行 + `".join` → `"\\n".join`
3. `f"` 或 `f'` 跨行 → 合并为 `\\n`
"""
import ast, os

def fix_file(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.split('\n')
    i = 0
    changes = 0
    
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        
        # 跳过三引号块
        if '"""' in rline or "'''" in rline:
            i += 1
            continue
        
        # 跳过注释行
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        
        # 跳过反斜杠续行
        if rline.endswith('\\'):
            i += 1
            continue
        
        next_line = lines[i+1]
        ns = next_line.strip()
        
        # 检查行尾引号是否未闭合
        dq = rline.count('"') - rline.count('\\"')
        sq = rline.count("'") - rline.count("\\'")
        
        # 处理 " 未闭合跨行
        if rline.endswith('"') and dq % 2 == 1 and ns.startswith('"') and not rline.endswith('"""'):
            lines[i] = rline + '\\n' + ns[1:]
            del lines[i+1]
            changes += 1
            continue
        
        # 处理 ' 未闭合跨行
        if rline.endswith("'") and sq % 2 == 1 and ns.startswith("'") and not rline.endswith("'''"):
            lines[i] = rline + "\\n" + ns[1:]
            del lines[i+1]
            changes += 1
            continue
        
        # 处理 f" 未闭合跨行
        if rline.endswith('f"') and dq % 2 == 1:
            if ns.startswith('"'):
                lines[i] = rline + '\\n' + ns[1:]
                del lines[i+1]
                changes += 1
                continue
        
        # 处理 f' 未闭合跨行  
        if rline.endswith("f'") and sq % 2 == 1:
            if ns.startswith("'"):
                lines[i] = rline + "\\n" + ns[1:]
                del lines[i+1]
                changes += 1
                continue
        
        i += 1
    
    if changes == 0:
        return 0
    
    new_text = '\n'.join(lines)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(new_text)
    return changes


base = 'modules'
all_files = sorted(os.listdir(base))

# 先找出所有有错误的文件
err_files = []
for f in all_files:
    if not f.endswith('.py'):
        continue
    fp = os.path.join(base, f)
    try:
        ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=f)
    except SyntaxError:
        err_files.append(f)

print(f'语法错误文件: {len(err_files)}')

# 迭代修复（修复可能暴露新错误）
for iteration in range(10):
    fixed = 0
    still_broken = []
    for f in err_files:
        fp = os.path.join(base, f)
        c = fix_file(fp)
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=f)
            if c > 0:
                print(f'  ✓ {f}: {c}处修复')
            fixed += 1
        except SyntaxError:
            still_broken.append(f)
    
    err_files = still_broken
    if not err_files:
        print(f'\n第{iteration+1}轮: 全部修复!')
        break
    print(f'\n第{iteration+1}轮: 修复{fixed - len(err_files)}个文件, 剩余{len(err_files)}')
    
    if iteration >= 2:
        # 检查是否有固定错误（修复过的文件仍然报错）
        print('\n剩余文件:')
        for f in err_files[:15]:
            try:
                ast.parse(open(os.path.join(base, f), 'r', encoding='utf-8').read(), filename=f)
            except SyntaxError as e:
                print(f'  {f}: L{e.lineno} {str(e.msg)[:60]}')
        if len(err_files) > 15:
            print(f'  ... 还有 {len(err_files)-15} 个')
        break

print(f'\n最终: 剩余 {len(err_files)} 个')
