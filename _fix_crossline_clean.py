#!/usr/bin/env python3
"""修复文件中所有跨行字符串模式"""
import ast, sys, os

def fix_crossline_strings(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    changed = False
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        rline = line.rstrip()
        nxt = lines[i+1]
        nstripped = nxt.strip()
        
        if not rline or not nstripped:
            i += 1
            continue
        
        # 跳过注释行
        if rline.lstrip().startswith('#'):
            i += 1
            continue
        
        # 检测是否以未闭合的单引号结尾
        for q in ('"', "'"):
            if rline.endswith(q) and not rline.endswith('\\' + q) and not rline.endswith(q * 3):
                cnt = rline.count(q) - rline.count('\\' + q)
                # 检查这个引号下的 count
                if cnt % 2 == 1:  # 未闭合
                    # 下一行以同引号开头或结尾
                    if nstripped.startswith(q):
                        # 合并：行尾内容 + 引号 + 换行符 + 引号 + 下行引号后内容
                        lq = rline.rstrip(q)
                        rest = nstripped[len(q):]
                        lines[i] = lq + q + '\\n' + q + rest
                        del lines[i+1]
                        changed = True
                        break
                    elif nstripped.endswith(q):
                        # 下一行是纯字符串内容
                        lines[i] = rline + '\\n' + nstripped
                        del lines[i+1]
                        changed = True
                        break
        if changed:
            changed = False
            continue
        i += 1
    
    new_content = '\n'.join(lines)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

if __name__ == '__main__':
    base = 'D:/AUTO-EVO-AI-V0.1/modules'
    targets = sys.argv[1:] if len(sys.argv) > 1 else [f for f in sorted(os.listdir(base)) if f.endswith('.py')]
    
    for t in targets:
        fp = os.path.join(base, t) if not os.path.isabs(t) else t
        if not os.path.exists(fp):
            print(f'  SKIP {t}: not found')
            continue
        
        old_err = None
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                ast.parse(f.read(), filename=fp)
        except SyntaxError as e:
            old_err = e
        
        if old_err is None:
            continue
        
        for rnd in range(30):
            # backup
            bak = fp + '.fix_bak'
            import shutil
            shutil.copy2(fp, bak)
            
            if not fix_crossline_strings(fp):
                break  # no more changes
            
            # verify
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    ast.parse(f.read(), filename=fp)
                os.remove(bak)
                print(f'  ✅ {t} (fixed after {rnd+1} rounds)')
                break
            except SyntaxError as e:
                # restore and try more
                shutil.copy2(bak, fp)
                os.remove(bak)
                if rnd == 29:
                    print(f'  ❌ {t} L{e.lineno}: {str(e.msg)[:50]}')
