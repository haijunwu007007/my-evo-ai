"""在 routes_static.py 中插入 /agents 路由"""
f = r"D:\AUTO-EVO-AI-V0.1\api\routes\routes_static.py"
with open(f, "r", encoding="utf-8") as fh:
    c = fh.read()

insert = '''@router.get("/agents")
async def agents_page():
    p = BASE_DIR / "frontend" / "agents.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

'''

if '@router.get("/agents")' in c:
    print("already exists")
else:
    c = c.replace('@router.get("/claw")', insert + '@router.get("/claw")')
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(c)
    print("inserted OK")
