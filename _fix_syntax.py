"""修复所有agent_*.py中的{{}}语法错误为{}"""
import os

agents_dir = r'D:\AUTO-EVO-AI-V0.1\api\agents'
fixed = 0
files_fixed = set()

for f in os.listdir(agents_dir):
    if not f.endswith('.py'):
        continue
    fp = os.path.join(agents_dir, f)
    content = open(fp, 'r', encoding='utf-8').read()
    old = content
    # Fix {{ "ok": True, "data": ... }} -> {"ok": True, "data": ...}
    content = content.replace('{{ "ok": True, "data": f"{t} - 请配置API后使用" }}', '{"ok": True, "data": f"{t} - 请配置API后使用"}')
    content = content.replace('{{ "ok": False, "data": f"{t}失败: {e}" }}', '{"ok": False, "data": f"{t}失败: {e}"}')
    if content != old:
        open(fp, 'w', encoding='utf-8').write(content)
        fixed += 1
        files_fixed.add(f)
        print(f'  FIXED: {f}')

print(f'\nTotal: {fixed} files fixed')
print(f'Files: {sorted(files_fixed)}')
