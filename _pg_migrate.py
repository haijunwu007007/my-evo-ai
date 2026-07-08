"""PG全量迁移: 扫描所有SQLite .db文件 → 导入PostgreSQL"""
import os, json, sqlite3, psycopg2, sys
from pathlib import Path

PG = psycopg2.connect(host="localhost", dbname="evodb", user="evo", password="Evo@2026!PG")
PG.autocommit = True
BASE = Path("/home/ubuntu/my-evo-ai")

dbs = []
for root, dirs, files in os.walk(str(BASE)):
    root_p = Path(root)
    if any(x in str(root_p) for x in ['__pycache__','.git','venv','node_modules']):
        continue
    for f in files:
        if f.endswith('.db') and os.path.getsize(os.path.join(root, f)) > 1024:
            dbs.append(os.path.join(root, f))

print(f"找到 {len(dbs)} 个SQLite数据库文件:")
total_rows = 0
for db_path in sorted(dbs):
    rel = os.path.relpath(db_path, str(BASE))
    size = os.path.getsize(db_path)
    try:
        sl = sqlite3.connect(db_path)
        sl.row_factory = sqlite3.Row
        tables = [r[0] for r in sl.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' AND name NOT LIKE '%_seg%' AND name NOT LIKE '%_content%' AND name NOT LIKE '%_docsize%' AND name NOT LIKE '%_stat%'").fetchall()]
        db_rows = 0
        for table in tables:
            try:
                rows = sl.execute(f'SELECT * FROM "{table}"').fetchall()
                if not rows: continue
                cols = [d[0] for d in sl.execute(f'PRAGMA table_info("{table}")').fetchall()]
                ph = ','.join(['%s']*len(cols))
                cs = ','.join([f'"{c}"' for c in cols])
                cur = PG.cursor()
                ok = 0
                for row in rows:
                    vals = [row[c] if row[c] is not None else None for c in cols]
                    try:
                        cur.execute(f'INSERT INTO "{table}" ({cs}) VALUES ({ph}) ON CONFLICT DO NOTHING', vals)
                        ok += 1
                    except: break
                PG.commit()
                db_rows += ok
            except: continue
        sl.close()
        total_rows += db_rows
        print(f"  [{size//1024:>4}KB] {rel:50s} {len(tables):>2}表 {db_rows:>4}行")
    except Exception as e:
        print(f"  [FAIL] {rel}: {str(e)[:60]}")

print(f"\n总计: {len(dbs)} 个数据库, {total_rows} 行数据迁移完成")
PG.close()
