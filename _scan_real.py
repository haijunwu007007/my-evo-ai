"""Scan modules with real external dependencies"""
import os

mods = [f for f in os.listdir("modules") if f.endswith(".py") and not f.startswith("_")]
real = []
for f in sorted(mods):
    fp = os.path.join("modules", f)
    sz = os.path.getsize(fp)
    if sz < 12288:
        continue
    with open(fp, encoding="utf-8", errors="ignore") as fh:
        c = fh.read()
    has_http = "requests." in c or "urllib." in c or "httpx." in c or "http.client" in c
    has_db = "sqlite" in c or "psycopg" in c or "redis" in c
    has_data = "pandas" in c or "numpy" in c or "BeautifulSoup" in c or "psutil" in c
    delegate = "self.delegate" in c or "self._delegate" in c
    tags = []
    if has_http: tags.append("HTTP")
    if has_db: tags.append("DB")
    if has_data: tags.append("DATA")
    if delegate: tags.append("DEL")
    if tags:
        szk = sz // 1024
        print(f"  {f:<35s} {szk:>4}KB {' '.join(tags)}")
        real.append((f, sz, tags))

print(f"\n总计: {len(real)} 个有真实外部依赖的模块")
print(f"有 delegate 的: {sum(1 for _,_,t in real if 'DEL' in t)}")
