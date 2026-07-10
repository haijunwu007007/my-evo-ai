"""强力修复body硬编码：读取每个HTML，直接替换body{中的background硬编码"""
import re, pathlib

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1/frontend")
fixed = 0

for f in sorted(ROOT.glob("*.html")):
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    if "var(--bg)" in c and "#" not in c[:500]:  # 前面已修
        continue
    # 用更简单的匹配：body{...background: #xxx
    new = re.sub(
        r'(body\s*\{[^}]*?)background(?:-color)?\s*:\s*#[0-9a-fA-F]{3,6}\b',
        r'\1background:var(--bg)',
        c
    )
    # 也替换 background-color: #xxx
    new = re.sub(
        r'(body\s*\{[^}]*?)background-color\s*:\s*#[0-9a-fA-F]{3,6}\b',
        r'\1background:var(--bg)',
        new
    )
    if new != c:
        f.write_text(new, "utf-8")
        print(f"  fixed: {f.name}")
        fixed += 1

print(f"\n共计修复: {fixed}页")

# 最终验证
remaining = []
for f in sorted(ROOT.glob("*.html")):
    c = f.read_text("utf-8", errors="ignore")
    # 找到body{...}中还有#xxx的
    m = re.search(r'body\s*\{[^}]*?background[^}]*?#[0-9a-fA-F]{6}', c)
    if m:
        remaining.append(f.name)
if remaining:
    print(f"剩余: {remaining}")
else:
    print("全部清零 ✅")
