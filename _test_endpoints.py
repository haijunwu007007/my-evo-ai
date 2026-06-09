import urllib.request, time

BASE = "http://127.0.0.1:8765"
tests = [
    ("/", "首页聊天"),
    ("/dashboard", "仪表盘"),
    ("/app/login", "管理后台"),
    ("/scalar", "API文档"),
    ("/workflow", "工作流画布"),
    ("/api/v1/status", "系统状态"),
    ("/api/v1/version", "版本信息"),
    ("/api/v1/modules", "模块列表"),
    ("/api/v1/skills", "技能列表"),
    ("/api/v1/i18n?lang=zh-CN", "i18n中文"),
    ("/api/v1/i18n/langs", "i18n语言列表"),
    ("/api/v1/mcp/servers", "MCP服务器"),
    ("/api/v1/gateway/tools", "Gateway工具"),
    ("/api/v1/connectors", "连接器"),
    ("/api/v1/a2a/agents", "A2A Agent"),
    ("/api/v1/mcpize/status", "MCPize状态"),
    ("/api/v1/scheduler/status", "调度器状态"),
    ("/api/v1/insights/evolution", "进化洞察"),
    ("/api/v1/config/items?group=system", "系统配置"),
    ("/api/v1/public/usage", "公开API用量"),
    ("/metrics", "Prometheus指标"),
    ("/api/v1/tools/health", "工具健康检查"),
    ("/api/v1/events/stats", "事件统计"),
    ("/api/v1/rag/kb", "RAG知识库"),
    ("/api/v1/gateway/enabled", "Gateway启用列表"),
    ("/api/v1/scheduler/tasks", "调度任务"),
    ("/api/v1/rag/documents", "RAG文档"),
    ("/api/v1/pipeline/status", "管道状态"),
    ("/api/v1/queue/stats", "队列统计"),
    ("/api/v1/events/rules", "事件规则"),
    ("/api/v1/pipelines/stats", "管道统计"),
    ("/api/v1/gateway/audit", "Gateway审计"),
    ("/api/v1/a2a/rooms", "A2A房间"),
    ("/api/v1/templates", "模板列表"),
]
ok = fail = 0; failed = []
for path, desc in tests:
    time.sleep(0.3)
    try:
        r = urllib.request.urlopen(BASE + path, timeout=10)
        if r.status == 200:
            ok += 1; print("  [+] " + desc)
        else:
            fail += 1; print("  [!] " + desc + " " + str(r.status))
            failed.append(path)
    except urllib.error.HTTPError as e:
        fail += 1; print("  [X] " + desc + " " + str(e.code))
        failed.append(path)
    except Exception as e:
        fail += 1; print("  [X] " + desc + " " + type(e).__name__)
        failed.append(path)
print()
print("=== 总计: " + str(len(tests)) + " 端点 === " + str(ok) + " 通过, " + str(fail) + " 失败 ===")
if fail > 0:
    print("失败: " + ", ".join(failed))
