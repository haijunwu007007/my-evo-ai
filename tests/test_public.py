"""快速公网测试"""
import urllib.request, ssl

ctx = ssl.create_default_context()
results = []

urls = [
    ("/", "首页"),
    ("/chat.html", "聊天"),
    ("/enterprise.html", "模块总览"),
    ("/admin", "管理中心"),
    ("/billion-os.html", "集团OS"),
    ("/audit", "审计日志"),
    ("/webhooks", "Webhook管理"),
    ("/backup", "备份恢复"),
    ("/install-wizard", "安装向导"),
    ("/marketplace", "插件市场"),
    ("/bi", "BI仪表盘"),
    ("/realtime", "实时协作"),
    ("/deploy", "一键部署"),
    ("/docs", "API文档"),
    ("/install/install.sh", "安装脚本"),
    ("/install/docker-compose.yml", "Docker部署"),
    ("/api/v1/version", "API版本"),
]

all_ok = True
for path, name in urls:
    try:
        r = urllib.request.urlopen(f"https://autoevoai.com{path}", timeout=10, context=ctx)
        size = len(r.read())
        status = f"✅ {r.status} {size}B"
    except Exception as e:
        status = f"❌ {e}"
        all_ok = False
    print(f"  {status}  {name}")
    results.append((name, status))

print(f"\n{'='*40}")
print(f"总页面: {len(results)}")
print(f"结果: {'全部通过 ✅' if all_ok else '有失败 ❌'}")
