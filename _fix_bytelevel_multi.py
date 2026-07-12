#!/usr/bin/env python3
"""字节级修复：多轮迭代，直到全部修复"""
import os, ast

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

CRLF = b'\r\n'

# 字节级替换模式（全部位置精确）
PATTERNS = [
    (b'.split("' + CRLF + b'")' + CRLF, b'.split("\\n")' + CRLF),
    (b".split('" + CRLF + b"')" + CRLF, b".split('\\n')" + CRLF),
    (b'.join("' + CRLF + b'")' + CRLF, b'.join("\\n")' + CRLF),
    (b".join('" + CRLF + b"')" + CRLF, b".join('\\n')" + CRLF),
    (b'.count("' + CRLF + b'")' + CRLF, b'.count("\\n")' + CRLF),
    (b".count('" + CRLF + b"')" + CRLF, b".count('\\n')" + CRLF),
    # timezone重复
    (b'timezone, timezone.utc', b'timezone'),
    # logger.info typo
    (b'logger.info(y_footprint"', b'"memory_footprint"'),
]

def verify(fp):
    try:
        ast.parse(open(fp,'r',encoding='utf-8').read(), filename=fp)
        return True
    except: return False

def fix_crossline_rstring(raw):
    """修复 r"跨行" 和 f"跨行" 模式"""
    text = raw.decode('utf-8')
    lines = text.split('\n')
    changed = False
    
    # 收集要合并的信息
    merges = []
    for i, line in enumerate(lines):
        if i >= len(lines) - 1:
            break
        rline = line.rstrip()
        if rline.lstrip().startswith('#'):
            continue
        
        for prefix in ('r"', "r'", 'f"', "f'"):
            if prefix not in rline:
                continue
            # 找到最后一个prefix
            last_idx = rline.rfind(prefix)
            if last_idx < 0:
                continue
            after = rline[last_idx + len(prefix):]
            # 检查引号是否未闭合
            q = prefix[-1]  # " or '
            if after.count(q) == 0:  # 没闭合
                # 向后找闭合引号
                for j in range(i+1, len(lines)):
                    lj = lines[j]
                    qi = lj.find(q)
                    if qi >= 0:
                        merges.append((i, j, last_idx, qi, prefix))
                        break
    
    if not merges:
        return raw
    
    # 从后往前合并（避免索引错乱）
    for i, j, last_idx, qi, prefix in reversed(merges):
        q = prefix[-1]
        before = lines[i][:last_idx]
        content_parts = [lines[i][last_idx:]] + [lines[k].rstrip() for k in range(i+1, j)] + [lines[j][:qi]]
        
        # 合并内容中间加 \n
        merged = before + '\\n'.join(content_parts)
        rest = lines[j][qi:]
        if rest:
            lines[j] = rest
        lines[i] = merged
        for k in range(i+1, j):
            lines[k] = None
        changed = True
    
    if changed:
        text = '\n'.join(l for l in lines if l is not None)
        return text.encode('utf-8')
    return raw

# 主流程
err_before = len([f for f in os.listdir(BASE) if f.endswith('.py') and not verify(os.path.join(BASE, f))])
print(f'修复前: {err_before}')

for rnd in range(50):
    fixed_any = False
    for f in sorted(os.listdir(BASE)):
        if not f.endswith('.py'): continue
        fp = os.path.join(BASE, f)
        if verify(fp): continue
        
        with open(fp, 'rb') as fh:
            raw = fh.read()
        
        # 模式替换
        for old, new in PATTERNS:
            if old in raw:
                raw = raw.replace(old, new)
        
        # r-string/f-string跨行修复
        raw = fix_crossline_rstring(raw)
        
        if raw != open(fp, 'rb').read():
            with open(fp, 'wb') as fh:
                fh.write(raw)
            fixed_any = True
    
    if not fixed_any: break
    
    remaining = len([f for f in os.listdir(BASE) if f.endswith('.py') and not verify(os.path.join(BASE, f))])
    print(f'第{rnd+1}轮: 剩余{remaining}')
    if remaining == 0: break

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
final = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not verify(os.path.join(BASE, f))]
print(f'\n总{total}, 正确{total-len(final)}, 剩余{len(final)}')
if final:
    for f in final[:20]:
        fp = os.path.join(BASE, f)
        try: ast.parse(open(fp,'r',encoding='utf-8').read())
        except SyntaxError as e:
            print(f'  L{e.lineno:<5} {str(e.msg)[:55]}  {f}')
