"""最终验证：except:pass, print(), body硬编码"""
import re, pathlib

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")

# except:pass
exc = 0
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f) or ".git" in str(f):
        continue
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    # 匹配各种缩进的 except: pass
    exc += len(re.findall(r'^( +)except[^:]*:[^\n]*\n\1+pass', c, re.MULTILINE))
print(f"except:pass = {exc}")

# print() — 排除注释、import、def、class、docstring、logger
pr = 0
pr_files = []
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f) or ".git" in str(f) or f.name.startswith("_"):
        continue
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    for line in c.split("\n"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("from ") or s.startswith("import ") or s.startswith("def ") or s.startswith("class "):
            continue
        if "print(" in s and "logger" not in s:
            pr += 1
            pr_files.append(f.relative_to(ROOT))
if pr_files:
    print(f"print() = {pr} (文件数: {len(set(pr_files))})")
    for f in sorted(set(pr_files))[:20]:
        print(f"  {f}")
else:
    print(f"print() = 0 ✅")

# body硬编码 — 只匹配body{里的background硬编码，排除fallback
body = 0
body_pages = []
for f in sorted(ROOT.glob("frontend/*.html")):
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    # 找到body{}块，检查里面有没有background:#xxx (不是var(--bg,#xxx))
    for m in re.finditer(r'body\s*\{[^}]*\}', c):
        block = m.group()
        if re.search(r'background(?:-color)?\s*:\s*#[0-9a-fA-F]{6}\b', block) and "var(--bg)" not in block:
            body += 1
            body_pages.append(f.name)
            print(f"  body硬编码: {f.name} -> {block[:100]}")
if body_pages:
    print(f"body硬编码页 = {body}")
else:
    print(f"body硬编码页 = 0 ✅")
