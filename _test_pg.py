"""测试 core/database.py 的 PG 连接和数据迁移"""
import sys, os
sys.path.insert(0, r"D:\AUTO-EVO-AI-V0.1")
os.environ["EVO_PG_HOST"] = "122.51.144.227"
os.environ["EVO_PG_DB"] = "evodb"
os.environ["EVO_PG_USER"] = "evo"
os.environ["EVO_PG_PASSWORD"] = "Evo@2026!PG"

# 清除 PG 连接缓存，重新导入
for mod in list(sys.modules.keys()):
    if 'database' in mod and 'core' in mod:
        del sys.modules[mod]

from core.database import get_connection, health_check, _use_pg, initialize
print(f"PG 模式: {_use_pg}")
conn = get_connection()
print(f"连接类型: {type(conn).__name__}")
if _use_pg:
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"PG 表数: {len(tables)}")
    for t in tables[:5]:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        print(f"  {t}: {cur.fetchone()[0]} 行")
hc = health_check()
print(f"健康检查: {hc.get('driver')}, tables={hc.get('tables')}")
print("全部通过 ✅")
