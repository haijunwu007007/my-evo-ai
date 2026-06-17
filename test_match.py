import sys
sys.path.insert(0,"api")
from tools.tool_router import route_and_execute

tests = ["审查代码", "生成图表 1,2,3", "你好", "搜索AI", "爬取example.com", "部署nginx", "帮我做个小程序"]
for t in tests:
    r = route_and_execute(t)
    print(t, "→", r["type"], "tool=", r.get("tool",""))
