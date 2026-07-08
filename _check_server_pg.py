"""服务器本地验证PG连接"""
import sys, json
sys.path.insert(0, "/home/ubuntu/my-evo-ai")
from core.database import _use_pg, _try_pg, health_check
print("before:", _use_pg)
_try_pg()
print("after:", _use_pg)
print(json.dumps(health_check(), ensure_ascii=False))
