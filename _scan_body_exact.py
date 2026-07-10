"""精确扫描body背景硬编码"""
import re, pathlib
ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1/frontend")

for f in sorted(ROOT.glob("*.html")):
    c = f.read_text("utf-8", errors="ignore")
    # true body background hex
    m = re.search(r'body\s*\{[^}]*?background\s*:\s*#[0-9a-fA-F]{6,8}', c)
    if m:
        logger.info(f"  {f.name}: {m.group()[:60]}"))
