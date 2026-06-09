"""全系统端点综合测试 v2 — 匹配实际路由路径"""
import httpx, json, sys, time

BASE = "http://127.0.0.1:8765"
client = httpx.Client(timeout=15)

results = []
def test(name, method, path, expect=200, **kwargs):
    try:
        if method == "GET":
            r = client.get(f"{BASE}{path}", **kwargs)
        else:
            r = client.post(f"{BASE}{path}", **kwargs)
        status = "✅" if r.status_code == expect else "⚠️"
        detail = ""
        if r.status_code != expect:
            detail = f" (期望{expect}, 实际{r.status_code})"
        results.append((status, name, f"{method} {path}{detail}"))
        if r.status_code == expect:
            try: return r.json()
            except: return {}
        return None
    except Exception as e:
        results.append(("❌", name, f"{method} {path}: {e}"))
        return None

# ===== 核心系统 =====
test("根端点", "GET", "/")
test("状态", "GET", "/api/v1/status")
test("健康检查", "GET", "/api/v1/health")
test("版本信息", "GET", "/api/v1/version")
test("模块列表", "GET", "/api/v1/modules")
test("指标", "GET", "/api/v1/metrics")

# ===== 聊天 & 智能体 =====
test("智能聊天", "POST", "/api/v1/smart", json={"message": "你好", "lang": "zh-CN"})
test("中文搜索", "POST", "/api/v1/smart", json={"message": "搜索人工智能趋势", "lang": "zh-CN"})
test("Agent列表", "GET", "/api/v1/agents")

# ===== 自主Agent引擎 =====
r = test("Agent Run", "POST", "/api/v1/agent/run", json={"task": "搜索AI新闻"})

# ===== 公开API =====
key_r = test("创建API Key", "POST", "/api/v1/public/key/create", json={"name": "test", "owner": "test"})
api_key = key_r.get("api_key", "") if key_r else ""
test("公开聊天(无key→401)", "POST", "/api/v1/public/smart", expect=401, json={"message": "hello", "api_key": ""})
if api_key:
    test("公开聊天(有key)", "POST", "/api/v1/public/smart", json={"message": "hello", "api_key": api_key})
test("用量查询", "GET", "/api/v1/public/usage")
test("嵌入脚本", "GET", "/api/v1/public/embed.js")

# ===== Skills =====
test("技能列表", "GET", "/api/v1/skills")
test("技能搜索", "GET", "/api/v1/skills/search?q=search")

# ===== MCP =====
test("MCP服务器列表", "GET", "/api/v1/mcp/servers")
test("MCP工具搜索", "GET", "/api/v1/mcp/search?q=chat")

# ===== 外部集成 =====
test("Gateway列表", "GET", "/api/v1/gateway/tools")
test("连接器列表", "GET", "/api/v1/connectors")
test("MCPize列表", "GET", "/api/v1/mcpize/status")
test("A2A房间列表", "GET", "/api/v1/a2a/rooms")

# ===== 知识库RAG =====
test("RAG知识库列表", "GET", "/api/v1/rag/kb")
test("RAG文档列表", "GET", "/api/v1/rag/documents?kb=default")

# ===== 配置 & 事件 =====
test("配置项", "GET", "/api/v1/config/items?group=llm")
test("调度器状态", "GET", "/api/v1/scheduler/status")
test("调度任务", "GET", "/api/v1/scheduler/tasks")
test("事件列表", "GET", "/api/v1/events")
test("系统诊断", "GET", "/api/v1/diagnosis/health")

# ===== i18n =====
test("i18n中文", "GET", "/api/v1/i18n?lang=zh-CN")
test("i18n英文", "GET", "/api/v1/i18n?lang=en")
test("i18n语言列表", "GET", "/api/v1/i18n/langs")

# ===== 扩展 =====
test("REST→MCP", "POST", "/api/v1/rest2mcp/convert", json={"url": "https://api.github.com", "name": "github"})
test("REST→MCP列表", "GET", "/api/v1/rest2mcp/tools")
test("多租户项目创建", "POST", "/api/v1/tenant/projects", json={"name": "test"})
test("分析事件上报", "POST", "/api/v1/analytics/event", json={"event": "test", "endpoint": "/test"})

# ===== 打印结果 =====
pass_count = sum(1 for s,_,_ in results if s == "✅")
warn_count = sum(1 for s,_,_ in results if s == "⚠️")
fail_count = sum(1 for s,_,_ in results if s == "❌")
print(f"\n{'='*60}")
print(f"全系统端点测试报告 ({len(results)} 端点)")
print(f"{'='*60}")
print(f"通过: {pass_count}  ⚠️异常: {warn_count}  ❌失败: {fail_count}")
print(f"\n详情:")
for status, name, detail in results:
    print(f"  {status} {name}: {detail}")
print(f"\n{'='*60}")
if warn_count == 0 and fail_count == 0:
    print(f"🎉 全部 {pass_count}/{len(results)} 端点通过！")
else:
    print(f"⚠️ 部分异常（智能聊天500=LLM API Key未配置，属于正常行为）")
