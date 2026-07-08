"""迁移 SQLite → PG，然后重启 API 服务"""
import sys
sys.path.insert(0, "/home/ubuntu/my-evo-ai")
import json, sqlite3, psycopg2
from pathlib import Path

BASE = Path("/home/ubuntu/my-evo-ai")
DB_PATH = str(BASE / "data" / "evo.db")

# PG 连接
PG = psycopg2.connect(host="localhost", dbname="evodb", user="evo", password="Evo@2026!PG")
PG.autocommit = True

# SQLite 连接
SL = sqlite3.connect(DB_PATH)
SL.row_factory = sqlite3.Row

# 获取所有 SQLite 表
tables = [r[0] for r in SL.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'doc_chunks_fts'").fetchall()]

print(f"SQLite 表数: {len(tables)}")
total_rows = 0

for table in tables:
    rows = SL.execute(f'SELECT * FROM "{table}"').fetchall()
    if not rows:
        continue
    col_names = [d[0] for d in SL.execute(f'PRAGMA table_info("{table}")').fetchall()]
    placeholders = ','.join(['%s'] * len(col_names))
    cols_str = ','.join([f'"{c}"' for c in col_names])
    
    # PG 去重插入
    PG_cur = PG.cursor()
    ok = 0
    for row in rows:
        values = tuple(row[c] for c in col_names)
        try:
            PG_cur.execute(f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING', values)
            ok += 1
        except Exception as e:
            print(f"  {table}: row fail: {str(e)[:60]}")
            PG.rollback()
            break
    PG.commit()
    total_rows += ok
    print(f"  {table}: {ok}/{len(rows)}")

print(f"\n总计迁移: {total_rows} 行")
SL.close()
PG.close()
