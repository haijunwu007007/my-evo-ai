"""Fix compact module syntax errors"""
import ast, re
from pathlib import Path
MDIR = Path(__file__).parent.parent / "modules"
FIXES = 0
def fix(fpath):
    global FIXES
    content = fpath.read_text("utf-8")
    try: ast.parse(content); return
    except: pass
    lines = content.split("\n"); new = []
    for line in lines:
        s = line.lstrip()
        if s.startswith("#"): new.append(line); continue
        m = re.match(r'^(\s+)(if .+?):\s*(.+)', line)
        if m: new.append(f"{m.group(1)}{m.group(2)}:"); new.append(f"{m.group(1)}    {m.group(3)}"); continue
        m = re.match(r'^(\s+)(for .+?):\s*(.+)', line)
        if m: new.append(f"{m.group(1)}{m.group(2)}:"); new.append(f"{m.group(1)}    {m.group(3)}"); continue
        m = re.match(r'^(\s+)(elif .+?|else|try|except .+?|while .+?):\s*(.+)', line)
        if m: new.append(f"{m.group(1)}{m.group(2)}:"); new.append(f"{m.group(1)}    {m.group(3)}"); continue
        m = re.match(r'^module_class=(\w+)', line)
        if m: new.append(f"module_class = {m.group(1)}"); continue
        line = re.sub(r',(\s*[}\]])', r'\1', line)
        new.append(line)
    content = "\n".join(new)
    try:
        ast.parse(content)
        fpath.write_text(content, "utf-8"); FIXES += 1
        print(f"OK {fpath.name}")
    except SyntaxError as e:
        print(f"FAIL {fpath.name}: L{e.lineno} {e.msg}")

for f in sorted(MDIR.iterdir()):
    if f.suffix != ".py" or f.name.startswith("_"): continue
    try: ast.parse(f.read_text("utf-8"))
    except: fix(f)
print(f"\nFixed: {FIXES}")
