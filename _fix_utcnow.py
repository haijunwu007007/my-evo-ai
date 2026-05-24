"""批量修复 datetime.now(timezone.utc) 告警 """
import os, re, sys

root = r'D:\AUTO-EVO-AI-V0.1'
fixed = 0

for dirpath, _, filenames in os.walk(root):
    if 'venv' in dirpath or '__pycache__' in dirpath or '.git' in dirpath:
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(dirpath, fn)
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue

        if 'utcnow()' not in content and 'utcfromtimestamp' not in content:
            continue

        original = content

        # 替换 utcnow()
        content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(timezone.utc)', content)
        content = re.sub(r'datetime\.utcfromtimestamp\(([^)]+)\)', r'datetime.fromtimestamp(\1, tz=timezone.utc)', content)

        # 补 timezone import
        if 'timezone.utc' in content:
            # 检查是否有 from datetime import ... timezone
            imp = re.search(r'^from datetime import(.*)$', content, re.MULTILINE)
            if imp and 'timezone' not in imp.group(1):
                content = content.replace(imp.group(0), imp.group(0).rstrip() + ', timezone')
            elif not imp:
                # 换成 import datetime
                if 'import datetime' in content:
                    pass  # datetime.now(timezone.utc) 不依赖import风格
                else:
                    content = 'from datetime import timezone\n' + content

        if content != original:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed += 1
            print('OK', os.path.relpath(fp, root)[:70])

print('Done:', fixed)
