"""
修复v9合并行损伤：处理所有 `code:            code    def ` 模式
"""
import re, os, ast

BASE = 'D:/AUTO-EVO-AI-V0.1/modules'

def fix_v9_merge_damage(text):
    """修复v9造成的行合并损伤"""
    lines = text.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        rline = line.rstrip()
        stripped = rline.lstrip()
        
        # 检测是否为合并行（含多个代码块）
        # 模式1: ): 后跟10+空格和代码 → 应该是换行
        # 模式2: ]: 后跟10+空格和代码
        # 模式3: } 后跟8+空格和代码
        
        # 只在行太长时尝试拆分（>150字符）
        if len(rline) > 150:
            # 拆分1: 模式 ":            for" → ":\n            for"
            rline = re.sub(r'(:\s{10,}(?:if|for|while|with|try|except|elif|return))',
                           lambda m: ':\n' + ' ' * (len(m.group(0)) - len(m.group(0).lstrip()) - 4), rline)
            
            # 拆分2: 模式 "])    def " → "])\n    def "
            rline = re.sub(r'(\)\]|\]\))\s{4,}def\s', lambda m: m.group(1) + '\n    def ', rline)
            
            # 拆分3: 模式 "        self." 在行中间
            rline = re.sub(r'(\))\s{12,}(self\.)', lambda m: m.group(1) + '\n' + ' ' * 16 + m.group(2), rline)
            
            # 拆分4: 模式 "}\s{8}for" → "}\n        for"
            rline = re.sub(r'(})\s{8,}(for|if|while)', lambda m: m.group(1) + '\n        ' + m.group(2), rline)
            
            # 更多拆分...
        
        new_lines.append(rline)
    
    return '\n'.join(new_lines)

def fix_all_files():
    fixed = 0
    for f in sorted(os.listdir(BASE)):
        if not f.endswith('.py'):
            continue
        fp = os.path.join(BASE, f)
        try:
            ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
            continue  # already OK
        except:
            pass
        
        with open(fp, 'r', encoding='utf-8') as fh:
            text = fh.read()
        
        new_text = fix_v9_merge_damage(text)
        if new_text != text:
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.write(new_text)
            try:
                ast.parse(open(fp, 'r', encoding='utf-8').read(), filename=fp)
                fixed += 1
            except:
                pass
    
    return fixed

print('修复v9合并行损伤...')
fixed = fix_all_files()
print(f'修复: {fixed}')

total = len([f for f in os.listdir(BASE) if f.endswith('.py')])
errs = [f for f in sorted(os.listdir(BASE)) if f.endswith('.py') and not (lambda fp: ast.parse(open(fp,'r',encoding='utf-8').read(),filename=fp) if True else 1)(os.path.join(BASE,f)) if True else 1]
print(f'总{total}, 剩余{len(errs)}')
