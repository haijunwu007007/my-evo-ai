import re, ast, os

def fix_check(fp):
    content = open(fp, 'r', encoding='utf-8').read()
    original = content
    
    text = content
    text = re.sub(r'\.split\("\s*\n\s*"\s*\)', r'.split("\\n")', text)
    text = re.sub(r"\.split\('\s*\n\s*'\s*\)", r".split('\\n')", text)
    text = re.sub(r'\.join\("\s*\n\s*"\s*\)', r'.join("\\n")', text)
    text = re.sub(r"\.join\('\s*\n\s*'\s*\)", r".join('\\n')", text)
    text = re.sub(r'\.count\("\s*\n\s*"\s*\)', r'.count("\\n")', text)
    text = re.sub(r'(?<=[^\\])"\s*\n\s*"', r'"\\n"', text)
    text = re.sub(r'(r"[\u4e00-\u9fff？。！，]+)\s*\n\s*([^"]*?)"', r'\1\2"', text)
    
    changed = text != original
    if changed:
        open(fp, 'w', encoding='utf-8').write(text)
    
    try:
        ast.parse(text, filename=fp)
        if changed:
            print(f'  FIXED {os.path.basename(fp)}')
        else:
            print(f'  ALREADY-OK {os.path.basename(fp)}')
        return True
    except SyntaxError as e:
        if changed:
            print(f'  PARTIAL {os.path.basename(fp)}: L{e.lineno} {str(e.msg)[:50]}')
            # Show remaining errors
            lines = text.split('\n')
            for i in range(max(0,e.lineno-2), min(len(lines), e.lineno+3)):
                print(f'    {i+1}: {lines[i]}')
        else:
            print(f'  STILL {os.path.basename(fp)}: L{e.lineno} {str(e.msg)[:50]}')
        return False

# Test on 4 files
base = 'D:/AUTO-EVO-AI-V0.1/modules'
for f in ['atom_code.py', 'auto_summary.py', 'awesome_design_md.py', 'big_key_detection.py', 'cloud_connector.py']:
    fp = os.path.join(base, f)
    fix_check(fp)
