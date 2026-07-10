"""简易CI检查"""
import pathlib, re, sys

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")
ok = 0; err = 0

def log(s, m):
    global ok, err
    if s == "OK": ok += 1; print(f"  OK {m}")
    else: err += 1; print(f"  ERR {m}")

log("OK", "1. except:pass")
n = 0
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".git" in str(f) or f.name.startswith("_"):
        continue
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    m = re.findall(r"^( +)except[^:]*:[^\n]*\n\1+pass", c, re.MULTILINE)
    if m:
        log("ERR", f"{f.name}: {len(m)}处")
        n += len(m)
log("OK" if n == 0 else "ERR", f"  except:pass={n}")

log("OK", "2. print()")
n = 0
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".git" in str(f) or f.name.startswith("_"):
        continue
    if "tests" in str(f) or "benchmarks" in str(f) or "scripts" in str(f):
        continue
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    for i, line in enumerate(c.split("\n"), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("from ") or s.startswith("import ") or s.startswith("def "):
            continue
        if "print(" in s and "logger" not in s and "fingerprint" not in s.lower():
            n += 1
            log("ERR", f"{f.name}:{i}: {s[:60]}")
log("OK" if n == 0 else "ERR", f"  print()={n}")

log("OK", "3. body硬编码")
n = 0
for f in sorted(ROOT.glob("frontend/*.html")):
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    for m in re.finditer(r"body\s*\{[^}]*\}", c):
        block = m.group()
        if re.search(r"background(?:-color)?\s*:\s*#[0-9a-fA-F]{6}\b", block) and "var(--bg)" not in block:
            n += 1
            log("ERR", f"{f.name}: body背景硬编码")
log("OK" if n == 0 else "ERR", f"  body硬编码={n}")

log("OK", "4. pyc残留")
n = 0
for f in ROOT.rglob("*.pyc"):
    log("ERR", str(f.relative_to(ROOT)))
    n += 1
log("OK" if n == 0 else "ERR", f"  pyc={n}")

print(f"\nCI: {ok} OK, {err} ERR")
sys.exit(0 if err == 0 else 1)
