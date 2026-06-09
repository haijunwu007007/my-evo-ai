"""统一修复api/目录下except:pass -> except Exception: (保留注释/日志)"""
import os, re

api_dir = r'D:\AUTO-EVO-AI-V0.1\api'
total = 0
files_changed = set()

for root, dirs, fnames in os.walk(api_dir):
    for f in fnames:
        if not f.endswith('.py'): continue
        fp = os.path.join(root, f)
        content = open(fp, 'r', encoding='utf-8').read()
        old = content
        
        # Replace bare "except: pass" with "except Exception:\n            pass"
        content = re.sub(r'except:\s*pass', 'except Exception:\n            pass', content)
        
        if content != old:
            open(fp, 'w', encoding='utf-8').write(content)
            files_changed.add(os.path.relpath(fp, api_dir))
            total += 1
            print(f'  FIXED: {os.path.relpath(fp, api_dir)}')

print(f'\nTotal files fixed: {total}')
for f in sorted(files_changed):
    print(f'  - {f}')
