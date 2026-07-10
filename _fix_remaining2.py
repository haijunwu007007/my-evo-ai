"""修复剩余的5处except:pass和14处print()"""
import re, pathlib

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")

# except:pass — 找出具体位置
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f) or ".git" in str(f):
        continue
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    matches = list(re.finditer(r'^( +)except[^:]*:[^\n]*\n\1+pass', c, re.MULTILINE))
    if not matches:
        continue
    print(f"\n=== {f.relative_to(ROOT)} ===")
    lines = c.split("\n")
    for m in matches:
        line_no = c[:m.start()].count("\n") + 1
        print(f"  L{line_no}: {lines[line_no-1].strip()}")
        print(f"  L{line_no+1}: {lines[line_no].strip()}")
