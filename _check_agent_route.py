"""检查routes_static.py中的agent路由"""
import re

f = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"
with open(f, "r", encoding="utf-8") as fh:
    c = fh.read()

print('Has /agent:', '@router.get("/agent")' in c)
print('Has /agents:', '@router.get("/agents")' in c)
print('Has /claw:', '@router.get("/claw")' in c)

routes = re.findall(r'@router\.get\("[^"]+"\)', c)
print('All routes:', routes)
