import re, pathlib
ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f): continue
    c = f.read_text("utf-8", errors="ignore")
    matches = re.findall(r'^( +)except[^:]*:[^\n]*\n\1+pass', c, re.MULTILINE)
    if matches:
        logger.info(f"{f.relative_to(ROOT)}: {len(matches)}处"))
