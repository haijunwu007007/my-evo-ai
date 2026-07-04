"""验证/agents路由函数体"""
with open(r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py", "r", encoding="utf-8") as fh:
    c = fh.read()
i = c.find('@router.get("/agents")')
print(c[i:i+300])
