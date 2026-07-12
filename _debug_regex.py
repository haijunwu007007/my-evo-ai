import re, ast
content = open('D:/AUTO-EVO-AI-V0.1/modules/atom_code.py','r',encoding='utf-8').read()
print('has split line:', '.split("' in content)

# Check for \r\n
crlf_count = content.count('\r\n')
print(f'CRLF count: {crlf_count}')

# Test cross-line .split pattern
new = re.sub(r'\.split\("\s*\n\s*"\s*\)', r'.split("\\n")', content)
if new != content:
    print('Pattern 1 matched (.split)!')
else:
    print('Pattern 1 NO MATCH')
    # Try with \r
    new2 = re.sub(r'\.split\("\r\n\s*"\s*\)', r'.split("\\n")', content)
    if new2 != content:
        print('Pattern with \\r\\n matched!')

# Test .join pattern
new3 = re.sub(r'\.join\("\s*\n\s*"\s*\)', r'.join("\\n")', content)
if new3 != content:
    print('Pattern 2 matched (.join)!')
else:
    print('Pattern 2 NO MATCH')

# Try binary direct find
raw = open('D:/AUTO-EVO-AI-V0.1/modules/atom_code.py','rb').read()
idx = raw.find(b'.split("')
if idx >= 0:
    print(f'Found .split(" at byte {idx}')
    print(f'  Raw: {raw[idx:idx+40]}')
    hex_str = ' '.join(f'{b:02x}' for b in raw[idx:idx+40])
    print(f'  Hex: {hex_str}')
else:
    print('NO .split(" in raw bytes!')
