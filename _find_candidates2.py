"""Find modules that need real API integration"""
import os, ast, re

mods = [f for f in os.listdir("modules") if f.endswith(".py") and not f.startswith("_")]
candidates = []

for fname in mods:
    path = os.path.join("modules", fname)
    with open(path, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    
    sz = len(src)
    lines = len(src.split("\n"))
    
    # Check real deps
    has_http = bool(re.search(r"requests\.|urllib\.|httpx\.|aiohttp\.|http\.client|websocket", src))
    has_db = bool(re.search(r"sqlite|psycopg|sqlalchemy|redis|pymongo", src, re.I))
    has_data = bool(re.search(r"pandas|numpy|sklearn|beautifulsoup|lxml", src, re.I))
    has_net = "socket." in src or "smtplib" in src or "ftplib" in src
    
    # Check for execute method
    has_execute = "def execute" in src
    
    # Count non-blank non-comment lines
    code_lines = sum(1 for l in src.split("\n") 
                     if l.strip() and not l.strip().startswith(("#", '"""', "'''")))
    
    deps = has_http or has_db or has_data or has_net
    
    if not deps and has_execute and sz > 5000:
        candidates.append((fname, sz//1024, lines, code_lines))

candidates.sort(key=lambda x: x[1], reverse=True)
print(f"{'Module':<30} {'KB':>4} {'Lines':>5} {'Code':>5}")
print("-" * 50)
for name, sz, lines, code in candidates[:20]:
    print(f"{name:<30} {sz:>4} {lines:>5} {code:>5}")
print(f"\nTotal candidates: {len(candidates)}")
